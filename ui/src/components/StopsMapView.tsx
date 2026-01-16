import { useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, RotateCcw } from 'lucide-react';
import { Stop, UserLocation } from '../types';
import { formatDistance, calculateDistance } from '../utils/geo';

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

// Colors for different transit types and selection states
const MARKER_COLORS = {
  train: {
    selected: { bg: '#9333ea', border: '#c084fc' },    // Purple
    unselected: { bg: '#6b7280', border: '#9ca3af' },  // Gray
  },
  bus: {
    selected: { bg: '#2563eb', border: '#60a5fa' },    // Blue
    unselected: { bg: '#6b7280', border: '#9ca3af' },  // Gray
  },
};

const createStationIcon = (isSelected: boolean, transitType: 'train' | 'bus' = 'train') => {
  const colors = MARKER_COLORS[transitType] || MARKER_COLORS.train;
  const colorSet = isSelected ? colors.selected : colors.unselected;

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

  const handleMarkerDragEnd = (lat: number, lon: number) => {
    onSetManualLocation({ lat, lon });
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

          {/* User location marker */}
          {userPosition && (
            <DraggableUserMarker
              position={userPosition}
              onDragEnd={handleMarkerDragEnd}
            />
          )}

          {/* Station markers */}
          {stops.map((stop) => {
            const isSelected = selectedStopIds.includes(stop.stop_id);
            const distance = location
              ? calculateDistance(location.lat, location.lon, stop.lat, stop.lon)
              : undefined;
            const transitType = stop.type || 'train';

            return (
              <Marker
                key={stop.stop_id}
                position={[stop.lat, stop.lon]}
                icon={createStationIcon(isSelected, transitType)}
                eventHandlers={{
                  click: () => onToggleStop(stop.stop_id),
                }}
              >
                <Popup>
                  <div className="min-w-[150px]">
                    <div className="font-semibold">{stop.stop_name}</div>
                    <div className="text-xs text-gray-500">
                      {transitType === 'bus' ? 'Bus stop' : stop.line + ' line'}{stop.direction && ` · ${stop.direction}`}
                    </div>
                    {distance !== undefined && (
                      <div className={`text-xs mt-1 ${transitType === 'bus' ? 'text-blue-600' : 'text-purple-600'}`}>
                        {formatDistance(distance)}
                      </div>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleStop(stop.stop_id);
                      }}
                      className={`mt-2 w-full px-2 py-1 text-xs rounded ${
                        isSelected
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : transitType === 'bus'
                            ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                            : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                      }`}
                    >
                      {isSelected ? 'Deselect' : 'Select'}
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Instructions */}
      <p className="text-xs text-gray-400 text-center">
        Drag the blue marker to set a custom location. Click stations to select.
      </p>
    </div>
  );
}
