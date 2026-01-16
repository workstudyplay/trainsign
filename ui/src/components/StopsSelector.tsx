import { useState, useMemo } from 'react';
import { MapPin, X, Loader2, List, Map } from 'lucide-react';
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
          stops={stops}
          selectedStopIds={selectedStopIds}
          onToggleStop={toggleStop}
          location={effectiveLocation}
        />
      ) : (
        <StopsMapView
          stops={stops}
          selectedStopIds={selectedStopIds}
          onToggleStop={toggleStop}
          location={effectiveLocation}
          manualLocation={manualLocation}
          isManualOverride={isManualOverride}
          onSetManualLocation={setManualLocation}
          onClearManualLocation={clearManualLocation}
        />
      )}

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
