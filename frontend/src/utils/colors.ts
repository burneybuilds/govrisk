import { COLOR_RAMPS, NO_DATA_FILL } from '../constants/map';
import type { RampId } from '../constants/map';
import type { ProjectStatus } from '../types/map';

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

export function hexToRgb(hex: string): Rgb {
  const value = hex.replace('#', '');
  const full =
    value.length === 3
      ? value
          .split('')
          .map((c) => c + c)
          .join('')
      : value;
  const num = Number.parseInt(full, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

export function rgbToHex({ r, g, b }: Rgb): string {
  const to2 = (v: number) => v.toString(16).padStart(2, '0');
  return `#${to2(r)}${to2(g)}${to2(b)}`;
}

/** Linear interpolation between two RGB colors. */
export function lerpRgb(a: Rgb, b: Rgb, t: number): Rgb {
  const k = Math.min(1, Math.max(0, t));
  return {
    r: Math.round(a.r + (b.r - a.r) * k),
    g: Math.round(a.g + (b.g - a.g) * k),
    b: Math.round(a.b + (b.b - a.b) * k),
  };
}

function rampHexes(ramp: RampId, steps: number): string[] {
  const base = COLOR_RAMPS[ramp];
  if (steps <= base.length) {
    return base.slice(0, steps);
  }
  // More steps than ramp entries: interpolate to length `steps`.
  const hexes: string[] = [];
  for (let i = 0; i < steps; i += 1) {
    const t = (i / (steps - 1)) * (base.length - 1);
    const lo = Math.floor(t);
    const hi = Math.min(base.length - 1, lo + 1);
    const a = hexToRgb(base[lo]);
    const b = hexToRgb(base[hi]);
    hexes.push(rgbToHex(lerpRgb(a, b, t - lo)));
  }
  return hexes;
}

/**
 * Map a normalized value (0..1, or null for "missing") to a hex color for the
 * given ramp. `rampSteps` controls the banding granularity (e.g. 5 classes).
 */
export function quantileColor(value: number | null, ramp: RampId, rampSteps = 5): string {
  if (value === null || Number.isNaN(value)) return NO_DATA_FILL;
  const steps = Math.max(2, rampSteps);
  const hexes = rampHexes(ramp, steps);
  const index = Math.min(steps - 1, Math.max(0, Math.floor(value * steps)));
  return hexes[index] ?? NO_DATA_FILL;
}

/** Hex color with alpha for leaflet `fillOpacity` styling. */
export function withAlpha(hex: string, opacity: number): string {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/** Discrete legend buckets for a ramp (label + color pairs). */
export function rampLegend(
  ramp: RampId,
  steps = 5,
  labelMin = 'Low',
  labelMax = 'High',
): { label: string; color: string }[] {
  const hexes = rampHexes(ramp, steps);
  return hexes.map((color, i) => {
    const fraction = i / (steps - 1);
    const label = i === 0 ? labelMin : i === steps - 1 ? labelMax : `${Math.round(fraction * 100)}`;
    return { label, color };
  });
}

/** Status -> marker/legend fill color for the infrastructure projects layer. */
export const PROJECT_STATUS_COLORS: Record<ProjectStatus, string> = {
  ONGOING: '#22d3ee',
  COMPLETED: '#4ade80',
  DELAYED: '#fbbf24',
  STALLED: '#f87171',
  CANCELLED: '#a3a3a3',
};

export function projectStatusColor(status: ProjectStatus): string {
  return PROJECT_STATUS_COLORS[status] ?? '#22d3ee';
}
