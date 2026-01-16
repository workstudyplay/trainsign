export type TransitType = 'train' | 'bus';

export interface Stop {
  stop_id: string;
  stop_name: string;
  lat: number;
  lon: number;
  line: string;
  direction: string;
  distance?: number;
  type: TransitType;
}

export interface UserLocation {
  lat: number;
  lon: number;
}
