export interface Stop {
  stop_id: string;
  stop_name: string;
  lat: number;
  lon: number;
  line: string;
  direction: string;
  distance?: number;
}

export interface UserLocation {
  lat: number;
  lon: number;
}
