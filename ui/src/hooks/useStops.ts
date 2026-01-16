import { useState, useEffect, useCallback } from 'react';
import { Stop } from '../types';

import { API_BASE } from "../const"

export function useStops() {
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedStopIds, setSelectedStopIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStops() {
      try {
        const response = await fetch(`${API_BASE}/api/stops`);
        if (!response.ok) throw new Error('Failed to fetch stops');
        const data = await response.json();
        setStops(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch stops');
      }
    }
    fetchStops();
  }, []);

  useEffect(() => {
    async function fetchSelectedStops() {
      try {
        const response = await fetch(`${API_BASE}/api/selected-stops`);
        if (!response.ok) throw new Error('Failed to fetch selected stops');
        const data = await response.json();
        setSelectedStopIds(data.selected_stops || []);
      } catch (err) {
        console.error('Error fetching selected stops:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchSelectedStops();
  }, []);

  const saveSelectedStops = useCallback(async (stopIds: string[]) => {
    try {
      const response = await fetch(`${API_BASE}/api/selected-stops`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_stops: stopIds }),
      });
      if (!response.ok) throw new Error('Failed to save stops');
      setSelectedStopIds(stopIds);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save stops');
      return false;
    }
  }, []);

  return {
    stops,
    selectedStopIds,
    setSelectedStopIds,
    saveSelectedStops,
    loading,
    error,
  };
}
