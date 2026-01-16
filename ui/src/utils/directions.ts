// Direction labels for NYC subway lines
// N = Northbound (generally uptown/Manhattan-bound)
// S = Southbound (generally downtown/outer borough-bound)

/**
 * Get the route letter from a stop ID
 * Stop IDs like "L12N" -> "L", "G14S" -> "G", "101N" -> "1"
 */
export function getRouteFromStopId(stopId: string): string {
  // Remove N/S suffix first
  const base = stopId.replace(/[NS]$/, '');
  // First character is the route (letter or number)
  const first = base[0];
  // For numeric IDs (like 101, 201), the first digit is the route
  if (/^\d/.test(first)) {
    return first;
  }
  // For letter IDs (like L12, G14), the letter is the route
  return first.toUpperCase();
}

// Terminal destinations by line/route
const LINE_TERMINALS: Record<string, { N: string; S: string }> = {
  // IRT Lines (1-7)
  '1': { N: 'Van Cortlandt Park', S: 'South Ferry' },
  '2': { N: '241 St (Wakefield)', S: 'Flatbush Av' },
  '3': { N: 'Harlem-148 St', S: 'New Lots Av' },
  '4': { N: 'Woodlawn', S: 'Crown Hts-Utica Av' },
  '5': { N: 'Eastchester', S: 'Flatbush Av' },
  '6': { N: 'Pelham Bay Park', S: 'Brooklyn Bridge' },
  '7': { N: 'Flushing', S: 'Hudson Yards' },

  // IND Lines (A-G)
  'A': { N: 'Inwood-207 St', S: 'Far Rockaway / Ozone Park' },
  'B': { N: 'Bedford Park Blvd', S: 'Brighton Beach' },
  'C': { N: '168 St', S: 'Euclid Av' },
  'D': { N: 'Norwood-205 St', S: 'Coney Island' },
  'E': { N: 'Jamaica Center', S: 'World Trade Center' },
  'F': { N: 'Jamaica-179 St', S: 'Coney Island' },
  'G': { N: 'Court Sq', S: 'Church Av' },
  'M': { N: 'Forest Hills', S: 'Middle Village' },

  // BMT Lines (J-Z, L, N-W)
  'J': { N: 'Jamaica Center', S: 'Broad St' },
  'Z': { N: 'Jamaica Center', S: 'Broad St' },
  'L': { N: '8 Av (Manhattan)', S: 'Canarsie-Rockaway Pkwy' },
  'N': { N: 'Astoria-Ditmars', S: 'Coney Island' },
  'Q': { N: '96 St (2nd Av)', S: 'Coney Island' },
  'R': { N: 'Forest Hills', S: 'Bay Ridge-95 St' },
  'W': { N: 'Astoria-Ditmars', S: 'Whitehall St' },

  // Shuttles
  'S': { N: 'Times Sq', S: 'Grand Central' },
  'H': { N: 'Broad Channel', S: 'Rockaway Park' },
};

// Default fallback for unknown lines
const DEFAULT_TERMINALS = { N: 'Uptown', S: 'Downtown' };

/**
 * Get the direction label for a stop based on its line and direction
 * @param line - The subway line (e.g., "L", "G", "1")
 * @param direction - "N" or "S"
 * @returns Human-readable direction label (e.g., "8 Av (Manhattan)")
 */
export function getDirectionLabel(line: string, direction: 'N' | 'S'): string {
  const terminals = LINE_TERMINALS[line.toUpperCase()] || DEFAULT_TERMINALS;
  return terminals[direction];
}

/**
 * Get the base station ID from a directional stop ID
 * @param stopId - Stop ID like "L12N" or "L12S"
 * @returns Base station ID like "L12"
 */
export function getBaseStationId(stopId: string): string {
  if (stopId.endsWith('N') || stopId.endsWith('S')) {
    return stopId.slice(0, -1);
  }
  return stopId;
}

/**
 * Get the direction suffix from a stop ID
 * @param stopId - Stop ID like "L12N"
 * @returns "N", "S", or null if no direction
 */
export function getDirectionFromStopId(stopId: string): 'N' | 'S' | null {
  if (stopId.endsWith('N')) return 'N';
  if (stopId.endsWith('S')) return 'S';
  return null;
}
