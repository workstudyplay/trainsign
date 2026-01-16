import { useState, useEffect, useCallback } from 'react';
import { UserLocation } from '../types';
import { useGeolocation } from './useGeolocation';

const MANUAL_LOCATION_KEY = 'trainsign-manual-location';

export function useLocation() {
  const { location: browserLocation, loading: geoLoading, error: geoError } = useGeolocation();
  const [manualLocation, setManualLocationState] = useState<UserLocation | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Load manual location from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(MANUAL_LOCATION_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (typeof parsed.lat === 'number' && typeof parsed.lon === 'number') {
          setManualLocationState(parsed);
        }
      }
    } catch {
      // Ignore localStorage errors
    }
    setInitialized(true);
  }, []);

  const setManualLocation = useCallback((location: UserLocation) => {
    setManualLocationState(location);
    try {
      localStorage.setItem(MANUAL_LOCATION_KEY, JSON.stringify(location));
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  const clearManualLocation = useCallback(() => {
    setManualLocationState(null);
    try {
      localStorage.removeItem(MANUAL_LOCATION_KEY);
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  // Use manual location if set, otherwise use browser location
  const effectiveLocation = manualLocation ?? browserLocation;
  const isManualOverride = manualLocation !== null;

  return {
    effectiveLocation,
    browserLocation,
    manualLocation,
    isManualOverride,
    setManualLocation,
    clearManualLocation,
    loading: !initialized || geoLoading,
    error: geoError,
  };
}
