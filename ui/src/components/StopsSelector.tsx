import { useState, useMemo } from 'react';
import { Search, MapPin, X, Check, Loader2 } from 'lucide-react';
import { Stop } from '../types';
import { useStops } from '../hooks/useStops';
import { useGeolocation } from '../hooks/useGeolocation';
import { sortStopsByDistance, formatDistance } from '../utils/geo';

export default function StopsSelector() {
  const {
    stops,
    selectedStopIds,
    setSelectedStopIds,
    saveSelectedStops,
    loading,
    error,
  } = useStops();
  const { location, loading: geoLoading } = useGeolocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const filteredStops = useMemo(() => {
    const sorted = sortStopsByDistance(stops, location);
    if (!searchQuery.trim()) return sorted;

    const query = searchQuery.toLowerCase();
    return sorted.filter(
      (stop) =>
        stop.stop_name.toLowerCase().includes(query) ||
        stop.stop_id.toLowerCase().includes(query)
    );
  }, [stops, location, searchQuery]);

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
      <div className="flex justify-between items-center mb-3 sm:mb-4">
        <h2 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2">
          <MapPin size={20} />
          Station Selection
        </h2>
        {geoLoading && (
          <span className="text-sm text-gray-400">Getting location...</span>
        )}
        {location && (
          <span className="text-sm text-green-400">Location enabled</span>
        )}
      </div>

      {error && (
        <div className="bg-red-600/20 text-red-400 px-3 sm:px-4 py-2 rounded mb-3 sm:mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="relative mb-3 sm:mb-4">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          size={18}
        />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search stations..."
          className="w-full bg-gray-700 text-white pl-10 pr-4 py-2 sm:py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      {isOpen && (
        <div className="bg-gray-700 rounded-lg max-h-64 overflow-y-auto mb-3 sm:mb-4">
          {filteredStops.slice(0, 50).map((stop) => (
            <div
              key={stop.stop_id}
              onClick={() => toggleStop(stop.stop_id)}
              className={`flex items-center justify-between px-3 sm:px-4 py-2 sm:py-3 cursor-pointer hover:bg-gray-600 border-b border-gray-600 last:border-0 ${
                selectedStopIds.includes(stop.stop_id) ? 'bg-purple-900/30' : ''
              }`}
            >
              <div>
                <div className="text-white text-sm sm:text-base">
                  {stop.stop_name}
                  <span className="ml-2 text-xs text-gray-400">
                    ({stop.stop_id.slice(-1)})
                  </span>
                </div>
                <div className="text-xs sm:text-sm text-gray-400">
                  {stop.line} line · {stop.direction}
                  {stop.distance !== undefined && (
                    <span className="ml-2 text-purple-400">
                      {formatDistance(stop.distance)}
                    </span>
                  )}
                </div>
              </div>
              {selectedStopIds.includes(stop.stop_id) && (
                <Check size={18} className="text-purple-400 flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      )}

      {selectedStops.length > 0 && (
        <div className="space-y-2 mb-3 sm:mb-4">
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
