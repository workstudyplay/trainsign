import { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, RotateCcw, Maximize2, Minimize2, X } from 'lucide-react';
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
  showRouteLines: boolean;
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

// Station marker with hover/click popup behavior
// - Hover: opens popup, closes when mouse leaves marker AND popup
// - Click: pins popup open until X is clicked
// - Mobile: uses click behavior (no hover)
function StationMarker({
  group,
  selectionState,
  distance,
  selectedStopIds,
  onToggleStop,
  adjustedPosition,
}: {
  group: StationGroup;
  selectionState: SelectionState;
  distance: number | undefined;
  selectedStopIds: string[];
  onToggleStop: (stopId: string) => void;
  adjustedPosition: [number, number];
}) {
  const markerRef = useRef<L.Marker>(null);
  const [isPinned, setIsPinned] = useState(false);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const routeColor = getLineColor(group.route);

  // Clear any pending close timeout
  const clearCloseTimeout = useCallback(() => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
  }, []);

  // Schedule popup close with delay
  const scheduleClose = useCallback(() => {
    clearCloseTimeout();
    closeTimeoutRef.current = setTimeout(() => {
      if (!isPinned) {
        markerRef.current?.closePopup();
      }
    }, 150); // Small delay to allow moving to popup
  }, [isPinned, clearCloseTimeout]);

  // Handle marker hover
  const handleMouseOver = useCallback(() => {
    clearCloseTimeout();
    markerRef.current?.openPopup();
  }, [clearCloseTimeout]);

  const handleMouseOut = useCallback(() => {
    if (!isPinned) {
      scheduleClose();
    }
  }, [isPinned, scheduleClose]);

  // Handle marker click (pin the popup)
  const handleClick = useCallback(() => {
    setIsPinned(true);
    clearCloseTimeout();
    markerRef.current?.openPopup();
  }, [clearCloseTimeout]);

  // Handle popup close button click
  const handleCloseClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsPinned(false);
    markerRef.current?.closePopup();
  }, []);

  // Handle popup mouse events
  const handlePopupMouseEnter = useCallback(() => {
    clearCloseTimeout();
  }, [clearCloseTimeout]);

  const handlePopupMouseLeave = useCallback(() => {
    if (!isPinned) {
      scheduleClose();
    }
  }, [isPinned, scheduleClose]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  return (
    <Marker
      ref={markerRef}
      position={adjustedPosition}
      icon={createStationIcon(selectionState, group.type)}
      eventHandlers={{
        mouseover: handleMouseOver,
        mouseout: handleMouseOut,
        click: handleClick,
      }}
    >
      <Popup
        closeButton={false}
        autoPan={false}
      >
        <div
          className="min-w-[200px] bg-gray-50 -m-[13px] -mt-[13px] p-3 rounded"
          onMouseEnter={handlePopupMouseEnter}
          onMouseLeave={handlePopupMouseLeave}
        >
          {/* Close button - only show when pinned */}
          {isPinned && (
            <button
              onClick={handleCloseClick}
              className="absolute top-1 right-1 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded"
              aria-label="Close"
            >
              <X size={14} />
            </button>
          )}

          <div className="font-semibold text-gray-900 pr-6">{group.name}</div>
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
  showRouteLines,
}: StopsMapViewProps) {
  const [isMaximized, setIsMaximized] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Calculate adjusted positions to prevent overlapping markers
  // At zoom level 13, roughly 0.0003 degrees ≈ 20 pixels (marker size is 18px)
  // We want at least 1px spacing, so minimum separation is ~19px ≈ 0.00029 degrees
  const adjustedPositions = useMemo(() => {
    const MIN_SEPARATION = 0.00025; // Minimum lat/lon separation between markers
    const positions: Record<string, [number, number]> = {};

    // Sort groups to have consistent ordering
    const sortedGroups = [...stationGroups].sort((a, b) =>
      a.baseId.localeCompare(b.baseId)
    );

    for (const group of sortedGroups) {
      let adjustedLat = group.lat;
      let adjustedLon = group.lon;
      let attempts = 0;
      const maxAttempts = 20;

      // Check for collisions and adjust position
      while (attempts < maxAttempts) {
        let hasCollision = false;

        for (const existingId of Object.keys(positions)) {
          const [existingLat, existingLon] = positions[existingId];
          const latDiff = Math.abs(adjustedLat - existingLat);
          const lonDiff = Math.abs(adjustedLon - existingLon);

          // Check if markers would overlap (using euclidean distance approximation)
          if (latDiff < MIN_SEPARATION && lonDiff < MIN_SEPARATION) {
            hasCollision = true;
            // Offset in a spiral pattern
            const angle = (attempts * 137.5 * Math.PI) / 180; // Golden angle for good distribution
            const radius = MIN_SEPARATION * (1 + Math.floor(attempts / 8) * 0.5);
            adjustedLat = group.lat + radius * Math.cos(angle);
            adjustedLon = group.lon + radius * Math.sin(angle);
            break;
          }
        }

        if (!hasCollision) break;
        attempts++;
      }

      positions[group.baseId] = [adjustedLat, adjustedLon];
    }

    return positions;
  }, [stationGroups]);

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

  // Scroll map into view when maximized
  useEffect(() => {
    if (isMaximized && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [isMaximized]);

  return (
    <div ref={containerRef} className="space-y-3">
      {/* Control bar */}
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
        <div className="flex items-center gap-2">
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
          <button
            onClick={() => setIsMaximized(!isMaximized)}
            className="p-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            title={isMaximized ? 'Minimize map' : 'Maximize map'}
          >
            {isMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>

      {/* Map container - 150% taller, or full viewport when maximized */}
      <div
        className={`rounded-lg overflow-hidden border border-gray-600 transition-all duration-300 ${
          isMaximized ? 'h-[calc(100vh-120px)]' : 'h-[480px] sm:h-[576px]'
        }`}
      >
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

          {/* Route lines - only show when trains are visible */}
          {showRouteLines &&
            Object.entries(routeShapesData).map(([route, data]) =>
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
            const adjustedPosition = adjustedPositions[group.baseId] || [group.lat, group.lon];

            return (
              <StationMarker
                key={group.baseId}
                group={group}
                selectionState={selectionState}
                distance={distance}
                selectedStopIds={selectedStopIds}
                onToggleStop={onToggleStop}
                adjustedPosition={adjustedPosition}
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
