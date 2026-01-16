import { useState, useMemo } from 'react';
import { MapPin, X, Loader2, List, Map, Train, Bus } from 'lucide-react';
import { Stop } from '../types';
import { useStops } from '../hooks/useStops';
import { useLocation } from '../hooks/useLocation';
import StopsListView from './StopsListView';
import StopsMapView from './StopsMapView';

type ViewMode = 'list' | 'map';

export default function StopsSelector() {
  const {
    stops,
    selectedStopIds,
    setSelectedStopIds,
    saveSelectedStops,
    loading,
    error,
  } = useStops();
  const {
    effectiveLocation,
    manualLocation,
    isManualOverride,
    setManualLocation,
    clearManualLocation,
    loading: locationLoading,
  } = useLocation();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [showTrains, setShowTrains] = useState(true);
  const [showBuses, setShowBuses] = useState(false);

  // Filter stops by transit type
  const filteredStops = useMemo(() => {
    return stops.filter((stop) => {
      if (stop.type === 'train' && showTrains) return true;
      if (stop.type === 'bus' && showBuses) return true;
      return false;
    });
  }, [stops, showTrains, showBuses]);

  const selectedStops = useMemo(() => {
    return selectedStopIds
      .map((id) => stops.find((s) => s.stop_id === id))
      .filter((s): s is Stop => s !== undefined);
  }, [selectedStopIds, stops]);

  const toggleStop = (stopId: string) => {
    const newSelected = selectedStopIds.includes(stopId)
      ? selectedStopIds.filter((id) => id !== stopId)
      : [...selectedStopIds, stopId];
    setSelectedStopIds(newSelected);
  };

  const handleSave = async () => {
    setSaveStatus('Saving...');
    const success = await saveSelectedStops(selectedStopIds);
    setSaveStatus(success ? 'Saved!' : 'Error saving');
    setTimeout(() => setSaveStatus(null), 2000);
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="animate-spin" size={20} />
          Loading stops...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
      {/* Header with view toggle */}
      <div className="flex justify-between items-center mb-3 sm:mb-4">
        <h2 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2">
          <MapPin size={20} />
          Station Selection
        </h2>
        <div className="flex items-center gap-2">
          {locationLoading && (
            <span className="text-xs text-gray-400">Getting location...</span>
          )}
          {/* View toggle buttons */}
          <div className="flex bg-gray-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              title="List view"
            >
              <List size={18} />
            </button>
            <button
              onClick={() => setViewMode('map')}
              className={`p-1.5 rounded-md transition-colors ${
                viewMode === 'map'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              title="Map view"
            >
              <Map size={18} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-600/20 text-red-400 px-3 sm:px-4 py-2 rounded mb-3 sm:mb-4 text-sm">
          {error}
        </div>
      )}

      {/* View content */}
      {viewMode === 'list' ? (
        <StopsListView
          stops={filteredStops}
          selectedStopIds={selectedStopIds}
          onToggleStop={toggleStop}
          location={effectiveLocation}
        />
      ) : (
        <StopsMapView
          stops={filteredStops}
          selectedStopIds={selectedStopIds}
          onToggleStop={toggleStop}
          location={effectiveLocation}
          manualLocation={manualLocation}
          isManualOverride={isManualOverride}
          onSetManualLocation={setManualLocation}
          onClearManualLocation={clearManualLocation}
        />
      )}

      {/* Transit type filter checkboxes */}
      <div className="flex items-center gap-4 mt-3 sm:mt-4 py-2 border-t border-gray-700">
        <span className="text-sm text-gray-400">Show:</span>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showTrains}
            onChange={(e) => setShowTrains(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-purple-600 focus:ring-purple-500 focus:ring-offset-gray-800"
          />
          <Train size={16} className="text-purple-400" />
          <span className="text-sm text-white">Trains</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showBuses}
            onChange={(e) => setShowBuses(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <Bus size={16} className="text-blue-400" />
          <span className="text-sm text-white">Buses</span>
        </label>
      </div>

      {/* Selected stations */}
      {selectedStops.length > 0 && (
        <div className="space-y-2 mb-3 sm:mb-4 mt-3 sm:mt-4">
          <h3 className="text-sm font-medium text-gray-400">
            Selected Stations ({selectedStops.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {selectedStops.map((stop) => (
              <div
                key={stop.stop_id}
                className="bg-purple-600 text-white px-2 sm:px-3 py-1 rounded-full flex items-center gap-1 sm:gap-2 text-sm"
              >
                <span>{stop.stop_name} ({stop.stop_id.slice(-1)})</span>
                <X
                  size={14}
                  className="cursor-pointer hover:text-red-300"
                  onClick={() => toggleStop(stop.stop_id)}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleSave}
        className="w-full bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 sm:py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
      >
        {saveStatus || 'Save Selection'}
      </button>
    </div>
  );
}
