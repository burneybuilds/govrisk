import type { RiskLevel } from '../types';
import type { StateKey } from '../types/map';

export interface KnownRegion {
  key: StateKey;
  officialName: string;
  aliases: readonly string[];
}

/**
 * Canonical registry of Indian states & union territories.
 *
 * `key` is the stable join key used by every adapter. `aliases` covers
 * legacy/GADM spellings (e.g. "Orissa", "Uttaranchal", "Andaman and Nicobar")
 * as well as ISO-3 style abbreviations, so raw sources can be reliably joined.
 */
export const KNOWN_REGIONS: readonly KnownRegion[] = [
  { key: 'andhra-pradesh', officialName: 'Andhra Pradesh', aliases: ['AP', 'Andhra'] },
  { key: 'arunachal-pradesh', officialName: 'Arunachal Pradesh', aliases: ['AR'] },
  { key: 'assam', officialName: 'Assam', aliases: ['AS'] },
  { key: 'bihar', officialName: 'Bihar', aliases: ['BR'] },
  { key: 'chhattisgarh', officialName: 'Chhattisgarh', aliases: ['CG', 'Chattisgarh'] },
  { key: 'goa', officialName: 'Goa', aliases: ['GA'] },
  { key: 'gujarat', officialName: 'Gujarat', aliases: ['GJ', 'Gujarat'] },
  { key: 'haryana', officialName: 'Haryana', aliases: ['HR'] },
  { key: 'himachal-pradesh', officialName: 'Himachal Pradesh', aliases: ['HP'] },
  { key: 'jharkhand', officialName: 'Jharkhand', aliases: ['JH'] },
  { key: 'karnataka', officialName: 'Karnataka', aliases: ['KA', 'Karnataka'] },
  { key: 'kerala', officialName: 'Kerala', aliases: ['KL', 'Kerala'] },
  { key: 'madhya-pradesh', officialName: 'Madhya Pradesh', aliases: ['MP'] },
  { key: 'maharashtra', officialName: 'Maharashtra', aliases: ['MH', 'Maharashtra'] },
  { key: 'manipur', officialName: 'Manipur', aliases: ['MN'] },
  { key: 'meghalaya', officialName: 'Meghalaya', aliases: ['ML'] },
  { key: 'mizoram', officialName: 'Mizoram', aliases: ['MZ'] },
  { key: 'nagaland', officialName: 'Nagaland', aliases: ['NL'] },
  { key: 'odisha', officialName: 'Odisha', aliases: ['OD', 'Orissa', 'Oddisa'] },
  { key: 'punjab', officialName: 'Punjab', aliases: ['PB'] },
  { key: 'rajasthan', officialName: 'Rajasthan', aliases: ['RJ', 'Rajasthan'] },
  { key: 'sikkim', officialName: 'Sikkim', aliases: ['SK'] },
  { key: 'tamil-nadu', officialName: 'Tamil Nadu', aliases: ['TN', 'Tamil Nadu'] },
  { key: 'telangana', officialName: 'Telangana', aliases: ['TS', 'TG', 'Telangana'] },
  { key: 'tripura', officialName: 'Tripura', aliases: ['TR'] },
  { key: 'uttar-pradesh', officialName: 'Uttar Pradesh', aliases: ['UP'] },
  { key: 'uttarakhand', officialName: 'Uttarakhand', aliases: ['UK', 'Uttaranchal', 'Uttranchal'] },
  { key: 'west-bengal', officialName: 'West Bengal', aliases: ['WB', 'West Bengal'] },
  {
    key: 'andaman-and-nicobar-islands',
    officialName: 'Andaman and Nicobar Islands',
    aliases: ['Andaman and Nicobar', 'AN', 'A&N Islands'],
  },
  { key: 'chandigarh', officialName: 'Chandigarh', aliases: ['CH'] },
  {
    key: 'dadra-and-nagar-haveli-and-daman-and-diu',
    officialName: 'Dadra and Nagar Haveli and Daman and Diu',
    aliases: ['Dadra and Nagar Haveli', 'Daman and Diu', 'DD', 'DNH'],
  },
  {
    key: 'delhi',
    officialName: 'Delhi',
    aliases: ['NCT of Delhi', 'National Capital Territory of Delhi', 'DL', 'New Delhi'],
  },
  {
    key: 'jammu-and-kashmir',
    officialName: 'Jammu and Kashmir',
    aliases: ['J&K', 'JK', 'Jammu & Kashmir'],
  },
  { key: 'ladakh', officialName: 'Ladakh', aliases: ['LA'] },
  { key: 'lakshadweep', officialName: 'Lakshadweep', aliases: ['LD', 'Lakshadweep'] },
  { key: 'puducherry', officialName: 'Puducherry', aliases: ['Pondicherry', 'PY', 'Puduchery'] },
];

/** Build a lookup table once, at module scope (never in render). */
const REGION_INDEX = (() => {
  const byKey = new Map<StateKey, KnownRegion>();
  const byAlias = new Map<string, StateKey>();
  for (const region of KNOWN_REGIONS) {
    byKey.set(region.key, region);
    byAlias.set(normalizeForMatch(region.officialName), region.key);
    for (const alias of region.aliases) {
      byAlias.set(normalizeForMatch(alias), region.key);
    }
  }
  return { byKey, byAlias };
})();

/** Lowercase, strip punctuation/noise words so spellings compare reliably. */
function normalizeForMatch(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\b(islands|island|nct|territory|state|ut|national|months)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Resolve any non-normalized region label (backend state name, GeoJSON
 * NAME_1, CSV cell) to a canonical `StateKey`. Returns null when unknown.
 */
export function resolveStateKey(label: string): StateKey | null {
  const key = REGION_INDEX.byAlias.get(normalizeForMatch(label));
  return key ?? null;
}

export function getKnownRegion(key: StateKey): KnownRegion | undefined {
  return REGION_INDEX.byKey.get(key);
}

const RISK_LEVEL_WEIGHT: Record<RiskLevel, number> = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };

/** Map an average portfolio risk score to a categorical level. */
export function levelForScore(score: number): RiskLevel {
  if (score >= 76) return 'CRITICAL';
  if (score >= 51) return 'HIGH';
  if (score >= 26) return 'MEDIUM';
  return 'LOW';
}

export function levelsEqual(a: RiskLevel, b: RiskLevel): boolean {
  return RISK_LEVEL_WEIGHT[a] === RISK_LEVEL_WEIGHT[b];
}
