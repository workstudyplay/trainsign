## TRAINSIGN.nyc

RGB panel for fun and games, showing MTA train and bus times and other messages, games and stuff.

### Components

Raspberry Pi - Runs python application
 * Python Flask API, runs as a daemon
 * [rpi-rgb-led-matrix](https://github.com/hzeller/) is compiled with python bindings
 * Adafruit RGB matrix hat for connecting daisy-chained RGB panels
 * React based web UI for control and configuration

## Installation

### Quick Start

```bash
# Install dependencies
pip install -r src/requirements.txt

# If you encounter build errors with adafruit packages on macOS/Linux, this is normal.
# The emulator works fine without them. Use:
pip install -r src/requirements.txt --no-build-isolation
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions and troubleshooting.

## Dependency Management

This project uses version ranges in `requirements.txt` to allow automatic patch and minor version updates. For reproducible builds, you can use `requirements.in` with `pip-tools`:

```bash
# Install pip-tools
pip install pip-tools

# Generate pinned requirements.txt from requirements.in
cd src
pip-compile requirements.in --upgrade
```

Or use the update script:

```bash
./scripts/update-requirements.sh
```

Dependencies are automatically checked weekly via GitHub Actions and a PR is created if updates are available.

## Features

### Transit Support

The application supports both **MTA Subway trains** and **MTA buses**:

- **Trains**: Real-time arrival data from MTA GTFS-RT feeds for all subway lines (1-7, A-G, J-Z, L, N-W, S)
- **Buses**: Support for NYC bus routes (M, B, Q, BX series)

### Web UI

 * **Station/Stop Selection**: Configure which train stations and bus stops to display
   - Interactive map view with draggable location marker
   - List view with search functionality
   - Filter by transit type (trains/buses)
   - Distance-based sorting from your location
 * **Manual Location Override**: Drag the map marker to set a custom location (persists across sessions)
 * **Send Broadcast messages**: Display custom scrolling text on the RGB panel
 * **Animation Control**: Configure and play animations on the display

### Data Files

Transit stop data is stored in CSV format:
 * `src/transit/data/gtfs_subway/stops.txt` - MTA Subway station data
 * `src/transit/data/gtfs_busco/stops.txt` - MTA Bus stop data

Bus stop IDs follow the format: `{ROUTE}_{STOP}N` or `{ROUTE}_{STOP}S` (e.g., `M15_001N` for M15 bus, northbound, stop 001)

 ![Web UI](assets/screenshots/web_ui.png)