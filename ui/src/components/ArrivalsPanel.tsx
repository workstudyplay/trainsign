import { Train, Loader2 } from 'lucide-react';
import { useArrivals } from '../hooks/useArrivals';

const LINE_COLORS: Record<string, string> = {
  '1': 'bg-red-600',
  '2': 'bg-red-600',
  '3': 'bg-red-600',
  '4': 'bg-green-600',
  '5': 'bg-green-600',
  '6': 'bg-green-600',
  '7': 'bg-purple-600',
  A: 'bg-blue-600',
  C: 'bg-blue-600',
  E: 'bg-blue-600',
  B: 'bg-orange-500',
  D: 'bg-orange-500',
  F: 'bg-orange-500',
  M: 'bg-orange-500',
  G: 'bg-lime-500',
  J: 'bg-amber-700',
  Z: 'bg-amber-700',
  L: 'bg-gray-500',
  N: 'bg-yellow-500',
  Q: 'bg-yellow-500',
  R: 'bg-yellow-500',
  W: 'bg-yellow-500',
  S: 'bg-gray-500',
};

function getLineColor(routeId: string): string {
  return LINE_COLORS[routeId] || 'bg-gray-600';
}

export default function ArrivalsPanel() {
  const { arrivals, loading, error } = useArrivals(15000);

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="animate-spin" size={20} />
          Loading arrivals...
        </div>
      </div>
    );
  }

  const stopIds = Object.keys(arrivals);

  if (stopIds.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2 mb-3 sm:mb-4">
          <Train size={20} />
          Train Arrivals
        </h2>
        <p className="text-gray-400 text-sm sm:text-base">No stops configured. Select stations above to see arrivals.</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-gray-800 rounded-lg shadow-xl p-4 sm:p-6">
      <h2 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2 mb-3 sm:mb-4">
        <Train size={20} />
        Train Arrivals
      </h2>

      {error && (
        <div className="bg-red-600/20 text-red-400 px-3 sm:px-4 py-2 rounded mb-3 sm:mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-3 sm:space-y-4">
        {stopIds.map((stopId) => {
          const stop = arrivals[stopId];
          const hasArrivals = stop.arrivals.some((a) => a.route_id);

          return (
            <div key={stopId} className="bg-gray-700 rounded-lg p-3 sm:p-4">
              <div className="flex justify-between items-center mb-2 sm:mb-3">
                <h3 className="text-white font-medium text-sm sm:text-base">{stop.stop_name}</h3>
                <span className="text-xs text-gray-400">{stopId}</span>
              </div>

              {hasArrivals ? (
                <div className="space-y-2">
                  {stop.arrivals
                    .filter((arrival) => arrival.route_id)
                    .map((arrival, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between bg-gray-800 rounded px-2 sm:px-3 py-2"
                      >
                        <div className="flex items-center gap-2 sm:gap-3">
                          <span
                            className={`${getLineColor(arrival.route_id)} text-white font-bold w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm`}
                          >
                            {arrival.route_id}
                          </span>
                          <span className="text-gray-300 text-xs sm:text-sm">
                            {arrival.text || 'Train'}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-white font-mono text-base sm:text-lg">
                            {arrival.status}
                          </span>
                          <span className="text-gray-400 text-xs ml-1 sm:ml-2">
                            {arrival.time}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">No upcoming arrivals</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
