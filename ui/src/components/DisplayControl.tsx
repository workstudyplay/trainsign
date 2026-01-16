import { useState, useEffect } from 'react';
import { Monitor, MonitorOff, Loader2 } from 'lucide-react';

import { API_BASE } from "../const"

export default function DisplayControl() {
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch(`${API_BASE}/api/display/status`);
        if (response.ok) {
          const data = await response.json();
          setRunning(data.running);
        }
      } catch (err) {
        console.error('Error fetching display status:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleDisplay = async () => {
    setError(null);
    try {
      const endpoint = running ? '/api/display/stop' : '/api/display/start';
      const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setRunning(data.running);
      } else {
        setError('Failed to toggle display');
      }
    } catch (err) {
      setError('Error connecting to server');
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-xl p-6">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="animate-spin" size={20} />
          Loading display status...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg shadow-xl p-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            {running ? <Monitor size={20} /> : <MonitorOff size={20} />}
            Display
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            {running ? 'Display is rendering arrivals' : 'Display is off'}
          </p>
        </div>
        <button
          onClick={toggleDisplay}
          className={`${
            running
              ? 'bg-red-600 hover:bg-red-700'
              : 'bg-green-600 hover:bg-green-700'
          } text-white px-6 py-3 rounded-lg flex items-center gap-2 transition-colors`}
        >
          {running ? (
            <>
              <MonitorOff size={18} />
              Stop
            </>
          ) : (
            <>
              <Monitor size={18} />
              Start
            </>
          )}
        </button>
      </div>
      {error && (
        <div className="mt-4 bg-red-600/20 text-red-400 px-4 py-2 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
