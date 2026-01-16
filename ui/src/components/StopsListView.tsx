import { useState, useMemo } from 'react';
import { Search, Check } from 'lucide-react';
import { Stop, UserLocation } from '../types';
import { sortStopsByDistance, formatDistance } from '../utils/geo';

interface StopsListViewProps {
  stops: Stop[];
  selectedStopIds: string[];
  onToggleStop: (stopId: string) => void;
  location: UserLocation | null;
}

export default function StopsListView({
  stops,
  selectedStopIds,
  onToggleStop,
  location,
}: StopsListViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);

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

  return (
    <>
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
              onClick={() => onToggleStop(stop.stop_id)}
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
    </>
  );
}
