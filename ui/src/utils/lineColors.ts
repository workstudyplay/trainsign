// MTA subway line colors (matching official MTA colors)
export const LINE_COLORS: Record<string, string> = {
  '1': '#EE352E', // Red
  '2': '#EE352E',
  '3': '#EE352E',
  '4': '#00933C', // Green
  '5': '#00933C',
  '6': '#00933C',
  '7': '#B933AD', // Purple
  'A': '#0039A6', // Blue
  'C': '#0039A6',
  'E': '#0039A6',
  'B': '#FF6319', // Orange
  'D': '#FF6319',
  'F': '#FF6319',
  'M': '#FF6319',
  'G': '#6CBE45', // Lime green
  'J': '#996633', // Brown
  'Z': '#996633',
  'L': '#A7A9AC', // Gray
  'N': '#FCCC0A', // Yellow
  'Q': '#FCCC0A',
  'R': '#FCCC0A',
  'W': '#FCCC0A',
  'S': '#808183', // Shuttle gray
  'H': '#808183', // Rockaway shuttle
};

// Tailwind class versions for use in className
export const LINE_COLORS_TW: Record<string, string> = {
  '1': 'bg-red-600',
  '2': 'bg-red-600',
  '3': 'bg-red-600',
  '4': 'bg-green-600',
  '5': 'bg-green-600',
  '6': 'bg-green-600',
  '7': 'bg-purple-600',
  'A': 'bg-blue-600',
  'C': 'bg-blue-600',
  'E': 'bg-blue-600',
  'B': 'bg-orange-500',
  'D': 'bg-orange-500',
  'F': 'bg-orange-500',
  'M': 'bg-orange-500',
  'G': 'bg-lime-500',
  'J': 'bg-amber-700',
  'Z': 'bg-amber-700',
  'L': 'bg-gray-500',
  'N': 'bg-yellow-500',
  'Q': 'bg-yellow-500',
  'R': 'bg-yellow-500',
  'W': 'bg-yellow-500',
  'S': 'bg-gray-500',
  'H': 'bg-gray-500',
};

export function getLineColor(routeId: string): string {
  return LINE_COLORS[routeId.toUpperCase()] || '#6b7280';
}

export function getLineColorTW(routeId: string): string {
  return LINE_COLORS_TW[routeId.toUpperCase()] || 'bg-gray-600';
}
