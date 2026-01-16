#!/usr/bin/env python3
"""
Generate simplified route shapes JSON for the web UI.
Reads GTFS shapes.txt and outputs a simplified version with fewer points.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
import math

DATA_DIR = Path(__file__).parent.parent / "src" / "transit" / "data" / "gtfs_subway"
OUTPUT_FILE = Path(__file__).parent.parent / "ui" / "src" / "data" / "routeShapes.json"

# Route colors from MTA
ROUTE_COLORS = {
    '1': '#EE352E', '2': '#EE352E', '3': '#EE352E',
    '4': '#00933C', '5': '#00933C', '6': '#00933C',
    '7': '#B933AD',
    'A': '#0039A6', 'C': '#0039A6', 'E': '#0039A6',
    'B': '#FF6319', 'D': '#FF6319', 'F': '#FF6319', 'M': '#FF6319',
    'G': '#6CBE45',
    'J': '#996633', 'Z': '#996633',
    'L': '#A7A9AC',
    'N': '#FCCC0A', 'Q': '#FCCC0A', 'R': '#FCCC0A', 'W': '#FCCC0A',
    'S': '#808183', 'H': '#808183',
}

def simplify_line(points, tolerance=0.0003):
    """Simplify a line using Douglas-Peucker algorithm."""
    if len(points) <= 2:
        return points

    # Find the point with maximum distance from line between first and last
    max_dist = 0
    max_idx = 0

    p1 = points[0]
    p2 = points[-1]

    for i in range(1, len(points) - 1):
        p = points[i]
        dist = point_line_distance(p, p1, p2)
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > tolerance:
        # Recurse
        left = simplify_line(points[:max_idx + 1], tolerance)
        right = simplify_line(points[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]

def point_line_distance(p, p1, p2):
    """Calculate perpendicular distance from point p to line p1-p2."""
    x0, y0 = p
    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)))

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy

    return math.sqrt((x0 - proj_x)**2 + (y0 - proj_y)**2)

def get_route_from_shape_id(shape_id):
    """Extract route letter/number from shape_id like '1..N03R' or 'A..N04R'."""
    parts = shape_id.split('..')
    if parts:
        route = parts[0]
        # Handle express variants
        if route.endswith('X'):
            route = route[:-1]
        return route
    return None

def main():
    shapes_file = DATA_DIR / "shapes.txt"

    # Read all shapes grouped by shape_id
    shapes_by_id = defaultdict(list)

    print(f"Reading {shapes_file}...")
    with open(shapes_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shape_id = row['shape_id']
            seq = int(row['shape_pt_sequence'])
            lat = float(row['shape_pt_lat'])
            lon = float(row['shape_pt_lon'])
            shapes_by_id[shape_id].append((seq, lat, lon))

    print(f"Found {len(shapes_by_id)} unique shape IDs")

    # Group shapes by route
    shapes_by_route = defaultdict(list)

    for shape_id, points in shapes_by_id.items():
        route = get_route_from_shape_id(shape_id)
        if route and route in ROUTE_COLORS:
            # Sort by sequence
            points.sort(key=lambda x: x[0])
            # Extract just lat/lon
            coords = [(p[1], p[2]) for p in points]
            shapes_by_route[route].append(coords)

    print(f"Found shapes for routes: {sorted(shapes_by_route.keys())}")

    # Simplify and deduplicate shapes per route
    route_shapes = {}

    for route, all_shapes in shapes_by_route.items():
        # Take the longest shape as representative (usually the full route)
        # and simplify it
        if not all_shapes:
            continue

        # Combine all shapes and remove near-duplicates
        all_points = set()
        simplified_shapes = []

        for shape in all_shapes:
            simplified = simplify_line(shape, tolerance=0.0005)
            # Only keep if it adds significant coverage
            new_points = 0
            for p in simplified:
                key = (round(p[0], 4), round(p[1], 4))
                if key not in all_points:
                    new_points += 1
                    all_points.add(key)

            if new_points > 5 or len(simplified_shapes) == 0:
                simplified_shapes.append(simplified)

        # Merge into a single list of line segments
        route_shapes[route] = {
            'color': ROUTE_COLORS[route],
            'lines': simplified_shapes[:10]  # Limit to 10 shape variants per route
        }

        total_points = sum(len(s) for s in route_shapes[route]['lines'])
        print(f"  {route}: {len(simplified_shapes[:10])} lines, {total_points} total points")

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    print(f"\nWriting to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(route_shapes, f)

    # Check file size
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"Output file size: {size_kb:.1f} KB")

if __name__ == '__main__':
    main()
