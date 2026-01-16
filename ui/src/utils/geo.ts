import { Stop, UserLocation } from '../types';

function toRad(deg: number): number {
  return deg * (Math.PI / 180);
}

export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 3959; // Earth's radius in miles
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export function sortStopsByDistance(
  stops: Stop[],
  userLocation: UserLocation | null
): Stop[] {
  if (!userLocation) {
    return [...stops].sort((a, b) => a.stop_name.localeCompare(b.stop_name));
  }

  return stops
    .map((stop) => ({
      ...stop,
      distance: calculateDistance(
        userLocation.lat,
        userLocation.lon,
        stop.lat,
        stop.lon
      ),
    }))
    .sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0));
}

export function formatDistance(miles: number): string {
  if (miles < 0.1) {
    return `${Math.round(miles * 5280)} ft`;
  }
  return `${miles.toFixed(1)} mi`;
}
