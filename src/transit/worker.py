#!/usr/bin/env python3
"""
mta_worker.py

Python port of the Go example:
- Loads stops.txt
- Resolves GTFS-RT feed URL based on stop ID
- Background thread periodically fetches arrivals and populates:
    - lines_buffer (3 strings)
    - data_buffer  (3 TrainStatus objects)
- Serves HTTP endpoints:
    GET /text -> JSON lines_buffer
    GET /data -> JSON data_buffer
"""

from __future__ import annotations

import argparse
import csv
import json
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# pip install gtfs-realtime-bindings
#from google.transit import gtfs_realtime_pb2  # type: ignore
#from gtfs_realtime_bindings import gtfs_realtime_pb2
from . import gtfs_realtime_pb2


MAX_ARRIVALS = 6

FEED_URLS: Dict[str, str] = {
    "MAIN": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "ACE": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "JZ": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "NQRW": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "SI": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}


@dataclass(frozen=True)
class Arrival:
    route_id: str
    when: datetime


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int


@dataclass
class TrainStatus:
    route_id: str = ""
    time: str = ""
    status: str = ""
    text: str = ""
    color: Color = field(default_factory=lambda: Color(50, 50, 50))



@dataclass
class TrainStop:
    stop_id: str
    line: str
    name: str
    lat: str
    lon: str
    location_type: str
    parent_station_id: str


def get_feed_id_from_stop_id(stop_id: str) -> str:
    first = stop_id[:1].upper()
    if first in {"1", "2", "3", "4", "5", "7"}:
        return "MAIN"
    if first in {"A", "C", "E"}:
        return "ACE"
    if first in {"N", "Q", "R", "W"}:
        return "NQRW"
    if first == "L":
        return "L"
    if first == "G":
        return "G"
    if first == "S":
        return "SI"
    if first in {"B", "D", "F", "M"}:
        return "BDFM"
    if first in {"J", "Z"}:
        return "JZ"
    return "MAIN"


def get_line_from_stop_id(stop_id: str) -> str:
    # Mirrors your Go logic (even though it’s a little quirky)
    first = stop_id[:1].upper()
    if first == "7":
        return "MAIN"
    if first == "A":
        return "ACE"
    if first == "G":
        return "BDFM"
    return first


def resolve_feed_url(feed_group: str) -> str:
    key = feed_group.strip().upper()
    if not key:
        raise ValueError("feed group is empty")
    if key not in FEED_URLS:
        raise ValueError(f"unknown feed group {feed_group!r}; valid: {', '.join(sorted(FEED_URLS.keys()))}")
    return FEED_URLS[key]


def load_stop_data(stops_txt_path: str) -> Dict[str, TrainStop]:
    path = Path(stops_txt_path)
    if not path.exists():
        raise FileNotFoundError(f"stops file not found: {stops_txt_path}")

    stops: Dict[str, TrainStop] = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Go code reads everything including header; we’ll skip header if present.
        rows = list(reader)

    for row in rows:
        if not row:
            continue
        # stops.txt format: stop_id, stop_name, stop_lat, stop_lon, location_type, parent_station
        if row[0] == "stop_id":
            continue
        stop_id, name, lat, lon = row[0], row[1], row[2], row[3]
        location_type = row[4] if len(row) > 4 else ""
        parent_station_id = row[5] if len(row) > 5 else ""

        line_id = get_line_from_stop_id(stop_id)

        stops[stop_id] = TrainStop(
            stop_id=stop_id,
            line=line_id,
            name=name,
            lat=lat,
            lon=lon,
            location_type=location_type,
            parent_station_id=parent_station_id,
        )

    return stops


def fetch_arrivals(feed_url: str, stop_id: str, api_key: str, timeout_s: float = 10.0) -> List[Arrival]:
    headers = {"x-api-key": api_key} if api_key else {}
    resp = requests.get(feed_url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()

    msg = gtfs_realtime_pb2.FeedMessage()
    msg.ParseFromString(resp.content)

    now = datetime.now(timezone.utc)
    arrivals: List[Arrival] = []

    for ent in msg.entity:
        if not ent.HasField("trip_update"):
            continue
        tu = ent.trip_update
        route_id = tu.trip.route_id

        for stu in tu.stop_time_update:
            if stu.stop_id != stop_id:
                continue

            epoch = 0
            if stu.HasField("departure") and stu.departure.time:
                epoch = int(stu.departure.time)
            elif stu.HasField("arrival") and stu.arrival.time:
                epoch = int(stu.arrival.time)
            if not epoch:
                continue

            t = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if t < now:
                continue

            arrivals.append(Arrival(route_id=route_id, when=t))

    arrivals.sort(key=lambda a: a.when)
    return arrivals[:MAX_ARRIVALS]


class DataBuffers:
    """
    Thread-safe buffers like your Go globals.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.lines_buffer: List[str] = ["", "", ""]
        self.data_buffer: List[TrainStatus] = [TrainStatus(), TrainStatus(), TrainStatus()]

    def set_from_arrivals(self, arrivals: List[Arrival], dest_text: str = "MANHATTAN") -> None:
        now = datetime.now(timezone.utc)
        new_lines = ["", "", ""]
        new_data = [TrainStatus(), TrainStatus(), TrainStatus()]

        for i, a in enumerate(arrivals[:3]):
            mins = int((a.when - now).total_seconds() // 60)
            if mins < 0:
                mins = 0
            status = f"{mins:3d}m"
            new_lines[i] = status
            new_data[i] = TrainStatus(
                text=dest_text,
                route_id=a.route_id,
                status=status,
                time=a.when.astimezone().strftime("%H:%M"),
                color=Color(50, 50, 50),
            )

        with self._lock:
            self.lines_buffer = new_lines
            self.data_buffer = new_data

    def snapshot(self) -> Tuple[List[str], List[Dict]]:
        with self._lock:
            lb = list(self.lines_buffer)
            db = [asdict(ts) for ts in self.data_buffer]
        return lb, db


class MTAWorker(threading.Thread):
    """
    Background worker thread: fetches arrivals for configured stops and populates buffers.
    """
    def __init__(
        self,
        *,
        stops: Dict[str, TrainStop],
        configured_stop_ids: List[str],
        refresh_s: float,
        api_key: str,
        buffers: DataBuffers,
        name: str,
    ) -> None:
        super().__init__(daemon=True)
        self._stops = stops
        self._configured_stop_ids = configured_stop_ids
        self._refresh_s = refresh_s
        self._api_key = api_key
        self._buffers = buffers
        self._stop_evt = threading.Event()
        self.name = name

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        # Minimal behavior match: original loop uses the first stop (even if multiple were parsed)
        # You can extend to rotate stops if you want.
        
        first_stop_id = self._configured_stop_ids[0]
        print("RUN worker: " + self.name + " " + first_stop_id)
        stop = self._stops.get(first_stop_id)
        if not stop:
            print("NO STOPS!")
            # Can't really "log.Fatal" in a thread; just stop.
            return

        # In your Go code, you resolve feed by stop.line (derived from stop_id)
        feed_group = stop.line
        feed_url = resolve_feed_url(feed_group)
        print(feed_url)
        while not self._stop_evt.is_set():
            try:
                arrivals = fetch_arrivals(feed_url, stop.stop_id, api_key=self._api_key)
                self._buffers.set_from_arrivals(arrivals)

                print("Setting arrivals for " + self.name)
            except Exception:
                # On error, keep prior buffer; could also clear or write an error sentinel.
                pass

            self._stop_evt.wait(self._refresh_s)


# class APIServerHandler(BaseHTTPRequestHandler):
#     buffers: DataBuffers  # set from server setup

#     def _send_json(self, payload) -> None:
#         data = json.dumps(payload).encode("utf-8")
#         self.send_response(200)
#         self.send_header("Content-Type", "application/json")
#         self.send_header("Content-Length", str(len(data)))
#         self.end_headers()
#         self.wfile.write(data)

#     def do_GET(self) -> None:
#         if self.path == "/text":
#             lb, _ = self.buffers.snapshot()
#             self._send_json(lb)
#             return
#         if self.path == "/data":
#             _, db = self.buffers.snapshot()
#             self._send_json(db)
#             return

#         self.send_response(404)
#         self.end_headers()

#     def log_message(self, fmt: str, *args) -> None:
#         # quiet by default
#         return


# def run_server(host: str, port: int, buffers: DataBuffers) -> None:
#     APIServerHandler.buffers = buffers
#     httpd = ThreadingHTTPServer((host, port), APIServerHandler)
#     httpd.serve_forever()


def parse_stop_ids(arg: str) -> List[str]:
    if "," in arg:
        return [s.strip() for s in arg.split(",") if s.strip()]
    return [arg.strip()]


# def main() -> None:

#     print("STARTING WORKER")
#     p = argparse.ArgumentParser()
#     p.add_argument("--stops-file", default="./stops.txt")
#     p.add_argument("--stop-id", default="G14N", help="GTFS stop ID, or comma-separated list")
#     p.add_argument("--refresh", default="10", help="refresh seconds (e.g. 5, 10)")
#     p.add_argument("--api-key", default="hello", help="x-api-key header value (if required)")
#     p.add_argument("--host", default="0.0.0.0")
#     p.add_argument("--port", type=int, default=8080)
#     args = p.parse_args()

#     stops = load_stop_data(args.stops_file)
#     configured_stop_ids = parse_stop_ids(args.stop_id)
#     refresh_s = float(args.refresh)

#     buffers = DataBuffers()

#     worker = MTAWorker(
#         stops=stops,
#         configured_stop_ids=configured_stop_ids,
#         refresh_s=refresh_s,
#         api_key=args.api_key,
#         buffers=buffers,
#     )
#     worker.start()

#     run_server(args.host, args.port, buffers)


# if __name__ == "__main__":
#     main()
