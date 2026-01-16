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

#TODO: Refactor the FEED_URLS to be less repetitive.
FEED_URLS: Dict[str, str] = {
    "MAIN": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "1": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "2": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "3": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "4": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "5": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "6": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "7": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "8": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "9": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "ACE": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "A": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "C": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "E": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "B": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "D": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "F": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "M": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "JZ": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "J": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "Z": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "NQRW": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "N": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "Q": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "R": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "W": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "SI": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
    "S": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
    "H": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}


@dataclass(frozen=True)
class Arrival:
    route_id: str
    when: datetime
    destination: str = ""


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
    transit_type: str = "train"  # "train" or "bus"


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


def get_line_from_stop_id(stop_id: str, transit_type: str = "train") -> str:
    """Get the line identifier from a stop ID.

    For trains: Uses the first character (e.g., "G14N" -> "G")
    For buses: MTA bus stop IDs are just numbers, so we return "Bus" as a generic line
    """
    if transit_type == "bus":
        # MTA bus stop IDs are numeric (e.g., "100025")
        # We don't have route info in the stop ID, so return generic
        return "Bus"

    # Train logic - mirrors original Go logic
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


def load_stop_data(stops_txt_path: str, transit_type: str = "train") -> Dict[str, TrainStop]:
    path = Path(stops_txt_path)
    if not path.exists():
        raise FileNotFoundError(f"stops file not found: {stops_txt_path}")

    stops: Dict[str, TrainStop] = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row.get("stop_id", "").strip()
            if not stop_id:
                continue

            # Handle different CSV formats
            # Train format: stop_id, stop_name, stop_lat, stop_lon, location_type, parent_station
            # Bus format: stop_id, stop_name, stop_desc, stop_lat, stop_lon
            name = row.get("stop_name", "").strip().strip('"')
            lat = row.get("stop_lat", "").strip()
            lon = row.get("stop_lon", "").strip()
            location_type = row.get("location_type", "").strip()
            parent_station_id = row.get("parent_station", "").strip()

            if not lat or not lon:
                continue

            line_id = get_line_from_stop_id(stop_id, transit_type)

            stops[stop_id] = TrainStop(
                stop_id=stop_id,
                line=line_id,
                name=name,
                lat=lat,
                lon=lon,
                location_type=location_type,
                parent_station_id=parent_station_id,
                transit_type=transit_type,
            )

    return stops


def load_all_stops(data_dir: str) -> Dict[str, TrainStop]:
    """Load both train and bus stops from the data directory"""
    all_stops: Dict[str, TrainStop] = {}

    # Load train stops
    train_file = Path(data_dir) / "gtfs_subway/stops.txt"
    if train_file.exists():
        train_stops = load_stop_data(str(train_file), transit_type="train")
        all_stops.update(train_stops)

    # Load bus stops
    bus_file = Path(data_dir) / "gtfs_busco/stops.txt"
    if bus_file.exists():
        bus_stops = load_stop_data(str(bus_file), transit_type="bus")
        all_stops.update(bus_stops)

    return all_stops


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

        # Extract destination/headsign from GTFS-RT
        destination = ""
        try:
            # Try trip_properties.trip_headsign (GTFS-RT 2.0+)
            if tu.HasField("trip_properties") and tu.trip_properties.trip_headsign:
                destination = tu.trip_properties.trip_headsign
        except Exception:
            pass

        # Fallback: use last stop_id in the trip
        if not destination and tu.stop_time_update:
            destination = tu.stop_time_update[-1].stop_id

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

            arrivals.append(Arrival(route_id=route_id, when=t, destination=destination))

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

    def set_from_arrivals(self, arrivals: List[Arrival], stops: Optional[Dict[str, "TrainStop"]] = None) -> None:
        now = datetime.now(timezone.utc)
        new_lines = ["", "", ""]
        new_data = [TrainStatus(), TrainStatus(), TrainStatus()]

        for i, a in enumerate(arrivals[:3]):
            mins = int((a.when - now).total_seconds() // 60)
            if mins < 0:
                mins = 0
            status = f"{mins:3d}m"
            new_lines[i] = status

            # Get destination text - try to resolve stop_id to station name
            dest_text = a.destination
            if dest_text and stops:
                stop_info = stops.get(dest_text)
                if stop_info:
                    dest_text = stop_info.name
            if not dest_text:
                dest_text = ""

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
            return

        feed_group = stop.line
        feed_url = resolve_feed_url(feed_group)
        print(feed_url)
        while not self._stop_evt.is_set():
            try:
                arrivals = fetch_arrivals(feed_url, stop.stop_id, api_key=self._api_key)
                self._buffers.set_from_arrivals(arrivals, stops=self._stops)

                print("Setting arrivals for " + self.name)
            except Exception:
                # On error, keep prior buffer; could also clear or write an error sentinel.
                pass

            self._stop_evt.wait(self._refresh_s)



def parse_stop_ids(arg: str) -> List[str]:
    if "," in arg:
        return [s.strip() for s in arg.split(",") if s.strip()]
    return [arg.strip()]
