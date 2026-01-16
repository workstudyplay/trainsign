import { useMemo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, RotateCcw } from 'lucide-react';
import { Stop, UserLocation } from '../types';
import { formatDistance, calculateDistance } from '../utils/geo';
import { getDirectionLabel, getBaseStationId, getDirectionFromStopId, getRouteFromStopId } from '../utils/directions';
import { getLineColor } from '../utils/lineColors';
import routeShapes from '../data/routeShapes.json';

// Type for route shapes data
interface RouteShape {
  color: string;
  lines: number[][][];
}

const routeShapesData = routeShapes as Record<string, RouteShape>;

// Custom icons
const userIcon = L.divIcon({
  className: 'user-location-marker',
  html: `<div style="
    width: 24px;
    height: 24px;
    background: #3b82f6;
    border: 3px solid white;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  "></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

// Selection states for grouped stations
type SelectionState = 'none' | 'partial' | 'full';

// Colors for different transit types and selection states
const MARKER_COLORS = {
  train: {
    none: { bg: '#6b7280', border: '#9ca3af' },      // Gray
    partial: { bg: '#a855f7', border: '#c084fc' },   // Light purple
    full: { bg: '#9333ea', border: '#c084fc' },      // Purple
  },
  bus: {
    none: { bg: '#6b7280', border: '#9ca3af' },      // Gray
    partial: { bg: '#60a5fa', border: '#93c5fd' },   // Light blue
    full: { bg: '#2563eb', border: '#60a5fa' },      // Blue
  },
};

const createStationIcon = (selectionState: SelectionState, transitType: 'train' | 'bus' = 'train') => {
  const colors = MARKER_COLORS[transitType] || MARKER_COLORS.train;
  const colorSet = colors[selectionState];

  return L.divIcon({
    className: 'station-marker',
    html: `<div style="
      width: 18px;
      height: 18px;
      background: ${colorSet.bg};
      border: 2px solid ${colorSet.border};
      border-radius: 50%;
      box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
};

interface StopsMapViewProps {
  stops: Stop[];
  selectedStopIds: string[];
  onToggleStop: (stopId: string) => void;
  location: UserLocation | null;
  manualLocation: UserLocation | null;
  isManualOverride: boolean;
  onSetManualLocation: (location: UserLocation) => void;
  onClearManualLocation: () => void;
}

// Grouped station with N and S stops
interface StationGroup {
  baseId: string;
  name: string;
  lat: number;
  lon: number;
  route: string;
  type: 'train' | 'bus';
  stops: {
    N?: Stop;
    S?: Stop;
  };
}

// Default center (NYC Grand Central area for MTA)
const DEFAULT_CENTER: [number, number] = [40.7527, -73.9772];
const DEFAULT_ZOOM = 13;

// Component to handle map center updates
function MapController({ center }: { center: [number, number] }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);

  return null;
}

// Draggable user marker component
function DraggableUserMarker({
  position,
  onDragEnd,
}: {
  position: [number, number];
  onDragEnd: (lat: number, lon: number) => void;
}) {
  return (
    <Marker
      position={position}
      icon={userIcon}
      draggable={true}
      eventHandlers={{
        dragend: (e) => {
          const marker = e.target;
          const pos = marker.getLatLng();
          onDragEnd(pos.lat, pos.lng);
        },
      }}
    >
      <Popup>
        <div className="text-center">
          <strong>Your Location</strong>
          <br />
          <span className="text-xs text-gray-500">Drag to adjust</span>
        </div>
      </Popup>
    </Marker>
  );
}

// Station marker with hover-to-open popup
function StationMarker({
  group,
  selectionState,
  distance,
  selectedStopIds,
  onToggleStop,
}: {
  group: StationGroup;
  selectionState: SelectionState;
  distance: number | undefined;
  selectedStopIds: string[];
  onToggleStop: (stopId: string) => void;
}) {
  const markerRef = useRef<L.Marker>(null);

  const routeColor = getLineColor(group.route);

  return (
    <Marker
      ref={markerRef}
      position={[group.lat, group.lon]}
      icon={createStationIcon(selectionState, group.type)}
      eventHandlers={{
        mouseover: () => {
          markerRef.current?.openPopup();
        },
      }}
    >
      <Popup>
        <div className="min-w-[200px] bg-gray-50 -m-[13px] -mt-[13px] p-3 rounded">
          <div className="font-semibold text-gray-900">{group.name}</div>
          {distance !== undefined && (
            <div className="text-xs text-gray-500 mt-0.5">
              {formatDistance(distance)}
            </div>
          )}

          {/* Direction checkboxes for train stations */}
          {group.type === 'train' && (group.stops.N || group.stops.S) && (
            <div className="mt-2 space-y-2">
              {group.stops.N && (
                <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-200 rounded px-1 py-1">
                  <input
                    type="checkbox"
                    checked={selectedStopIds.includes(group.stops.N.stop_id)}
                    onChange={() => onToggleStop(group.stops.N!.stop_id)}
                    className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span
                    className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                    style={{ backgroundColor: routeColor }}
                  >
                    {group.route}
                  </span>
                  <span className="text-sm text-gray-700">
                    {getDirectionLabel(group.route, 'N')}
                  </span>
                </label>
              )}
              {group.stops.S && (
                <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-200 rounded px-1 py-1">
                  <input
                    type="checkbox"
                    checked={selectedStopIds.includes(group.stops.S.stop_id)}
                    onChange={() => onToggleStop(group.stops.S!.stop_id)}
                    className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span
                    className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                    style={{ backgroundColor: routeColor }}
                  >
                    {group.route}
                  </span>
                  <span className="text-sm text-gray-700">
                    {getDirectionLabel(group.route, 'S')}
                  </span>
                </label>
              )}
            </div>
          )}

          {/* Bus stop toggle button */}
          {group.type === 'bus' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleStop(group.baseId);
              }}
              className={`mt-2 w-full px-2 py-1 text-xs rounded ${
                selectionState === 'full'
                  ? 'bg-red-100 text-red-700 hover:bg-red-200'
                  : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
              }`}
            >
              {selectionState === 'full' ? 'Deselect' : 'Select'}
            </button>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

export default function StopsMapView({
  stops,
  selectedStopIds,
  onToggleStop,
  location,
  isManualOverride,
  onSetManualLocation,
  onClearManualLocation,
}: StopsMapViewProps) {
  const mapCenter: [number, number] = useMemo(() => {
    if (location) {
      return [location.lat, location.lon];
    }
    return DEFAULT_CENTER;
  }, [location]);

  const userPosition: [number, number] | null = useMemo(() => {
    if (location) {
      return [location.lat, location.lon];
    }
    return null;
  }, [location]);

  // Group stops by base station ID (combining N and S)
  const stationGroups = useMemo(() => {
    const groups: Record<string, StationGroup> = {};

    for (const stop of stops) {
      // Only group train stops with N/S suffixes
      if (stop.type !== 'train') {
        // Bus stops don't get grouped
        const busGroup: StationGroup = {
          baseId: stop.stop_id,
          name: stop.stop_name,
          lat: stop.lat,
          lon: stop.lon,
          route: 'Bus',
          type: 'bus',
          stops: {},
        };
        groups[stop.stop_id] = busGroup;
        continue;
      }

      const direction = getDirectionFromStopId(stop.stop_id);
      if (!direction) continue; // Skip parent stations without direction

      const baseId = getBaseStationId(stop.stop_id);
      const route = getRouteFromStopId(stop.stop_id);

      if (!groups[baseId]) {
        groups[baseId] = {
          baseId,
          name: stop.stop_name,
          lat: stop.lat,
          lon: stop.lon,
          route,
          type: 'train',
          stops: {},
        };
      }

      groups[baseId].stops[direction] = stop;
    }

    return Object.values(groups);
  }, [stops]);

  const handleMarkerDragEnd = (lat: number, lon: number) => {
    onSetManualLocation({ lat, lon });
  };

  // Get selection state for a station group
  const getSelectionState = (group: StationGroup): SelectionState => {
    if (group.type === 'bus') {
      return selectedStopIds.includes(group.baseId) ? 'full' : 'none';
    }

    const nSelected = group.stops.N && selectedStopIds.includes(group.stops.N.stop_id);
    const sSelected = group.stops.S && selectedStopIds.includes(group.stops.S.stop_id);
    const hasN = !!group.stops.N;
    const hasS = !!group.stops.S;

    if (hasN && hasS && nSelected && sSelected) return 'full';
    if (nSelected || sSelected) return 'partial';
    return 'none';
  };

  return (
    <div className="space-y-3">
      {/* Control bar - matches list view height */}
      <div className="flex items-center justify-between gap-2 min-h-[32px]">
        <div className="flex items-center gap-2">
          {isManualOverride && (
            <button
              onClick={onClearManualLocation}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
            >
              <RotateCcw size={14} />
              Reset to GPS
            </button>
          )}
        </div>
        {isManualOverride && (
          <span className="text-xs text-amber-400">
            Using custom location
          </span>
        )}
        {!isManualOverride && location && (
          <span className="text-xs text-green-400 flex items-center gap-1">
            <Navigation size={12} />
            GPS location
          </span>
        )}
      </div>

      {/* Map container - fixed height to match list view */}
      <div className="h-80 sm:h-96 rounded-lg overflow-hidden border border-gray-600 transition-all duration-300">
        <MapContainer
          center={mapCenter}
          zoom={DEFAULT_ZOOM}
          className="h-full w-full"
          style={{ background: '#1f2937' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <MapController center={mapCenter} />

          {/* Route lines */}
          {Object.entries(routeShapesData).map(([route, data]) =>
            data.lines.map((line, lineIdx) => (
              <Polyline
                key={`${route}-${lineIdx}`}
                positions={line.map((coord) => [coord[0], coord[1]] as [number, number])}
                pathOptions={{
                  color: data.color,
                  weight: 3,
                  opacity: 0.7,
                }}
              />
            ))
          )}

          {/* User location marker */}
          {userPosition && (
            <DraggableUserMarker
              position={userPosition}
              onDragEnd={handleMarkerDragEnd}
            />
          )}

          {/* Station markers (grouped) */}
          {stationGroups.map((group) => {
            const selectionState = getSelectionState(group);
            const distance = location
              ? calculateDistance(location.lat, location.lon, group.lat, group.lon)
              : undefined;

            return (
              <StationMarker
                key={group.baseId}
                group={group}
                selectionState={selectionState}
                distance={distance}
                selectedStopIds={selectedStopIds}
                onToggleStop={onToggleStop}
              />
            );
          })}
        </MapContainer>
      </div>

      {/* Instructions */}
      <p className="text-xs text-gray-400 text-center">
        Drag the blue marker to set a custom location. Hover over stations to select directions.
      </p>
    </div>
  );
}
