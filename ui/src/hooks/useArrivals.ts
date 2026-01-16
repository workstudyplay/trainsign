import { useState, useEffect } from 'react';

import { API_BASE } from "../const"

interface Arrival {
  route_id: string;
  time: string;
  status: string;
  text: string;
  color: { r: number; g: number; b: number };
}

interface StopArrivals {
  stop_name: string;
  lines: string[];
  arrivals: Arrival[];
}

export function useArrivals(refreshInterval: number = 10000) {
  const [arrivals, setArrivals] = useState<Record<string, StopArrivals>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchArrivals() {
      try {
        const response = await fetch(`${API_BASE}/api/arrivals`);
        if (!response.ok) throw new Error('Failed to fetch arrivals');
        const data = await response.json();
        setArrivals(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch arrivals');
      } finally {
        setLoading(false);
      }
    }

    fetchArrivals();
    const interval = setInterval(fetchArrivals, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return { arrivals, loading, error };
}
