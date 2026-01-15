#!/usr/bin/env python
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base import StopData
from transit.worker import load_stop_data
from transit.ui import draw_stop


# Main function
if __name__ == "__main__":
    stops = load_stop_data(os.path.join(os.path.dirname(__file__), "data/stops.txt"))
    print("Loaded stops.txt data", len(stops))
    my_stops = [
        StopData("G14N", "Roosevelt Ave BDFM", ["G"]), 
        StopData("710N", "74 St-Broadway 7", ["7"]),
        StopData("A15N", "Atlantic Av-Barclays CEN", ["A"]),
    ]
    for stop in my_stops:
        stop.start(api_key="friend", stops=stops)
    
    while True:
        for stop in my_stops:
            print("Drawing stop:", stop.stop_id, stop.name)
            draw_stop(stop)
            time.sleep(5.0)
