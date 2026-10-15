// The map's projection and views (DESIGN.md §16.57). Equirectangular, by hand: x = longitude ×
// cos(31.5°), y = −latitude, so a degree east and a degree north are the same length around
// Jerusalem's latitude. Map units are those projected degrees.

import type { PlaceKind, PlaceSite } from '../api/types'

const COS = Math.cos((31.5 * Math.PI) / 180)

export interface Bounds {
  lon0: number
  lat0: number
  lon1: number
  lat1: number
}

/** The two standing views: the land (Dan to Beersheba, the Negev, the Jordan's east) and the
 * Near East (Egypt to Persia). */
export const VIEWS = {
  land: { lon0: 33.9, lat0: 29.4, lon1: 36.8, lat1: 33.5 },
  east: { lon0: 25, lat0: 14, lon1: 56, lat1: 41 },
} satisfies Record<string, Bounds>
export type ViewName = keyof typeof VIEWS

export const projectX = (lon: number) => lon * COS
export const projectY = (lat: number) => -lat

/** An SVG path of rings ([[lon, lat], ...]); `closed` for polygons. */
export function ringsPath(rings: number[][][], closed: boolean): string {
  return rings
    .map((ring) => ring.map(([lon, lat], i) => `${i ? 'L' : 'M'}${projectX(lon).toFixed(3)} ${projectY(lat).toFixed(3)}`).join('') + (closed ? 'Z' : ''))
    .join('')
}

/** The view box of bounds widened to the map's aspect (width / height), centred. */
export function viewBox(b: Bounds, aspect: number): { x: number; y: number; w: number; h: number } {
  let w = projectX(b.lon1) - projectX(b.lon0)
  let h = b.lat1 - b.lat0
  const cx = projectX(b.lon0) + w / 2
  const cy = projectY(b.lat1) + h / 2
  if (w / h > aspect) h = w / aspect
  else w = h * aspect
  return { x: cx - w / 2, y: cy - h / 2, w, h }
}

/** The bounds around points, padded, at least `minSpan` degrees across. */
export function fitBounds(points: { lat: number; lon: number }[], minSpan = 1.2): Bounds | undefined {
  if (points.length === 0) return undefined
  let [lon0, lon1, lat0, lat1] = [Infinity, -Infinity, Infinity, -Infinity]
  for (const p of points) {
    lon0 = Math.min(lon0, p.lon)
    lon1 = Math.max(lon1, p.lon)
    lat0 = Math.min(lat0, p.lat)
    lat1 = Math.max(lat1, p.lat)
  }
  const grow = (a: number, b: number) => {
    const pad = Math.max((b - a) * 0.12, (minSpan - (b - a)) / 2, 0)
    return [a - pad, b + pad]
  }
  ;[lon0, lon1] = grow(lon0, lon1)
  ;[lat0, lat1] = grow(lat0, lat1)
  return { lon0, lat0, lon1, lat1 }
}

/** Bounds zoomed by `factor` (> 1: in) about their centre, or moved by a fraction of their size. */
export function zoomBounds(b: Bounds, factor: number): Bounds {
  const cx = (b.lon0 + b.lon1) / 2
  const cy = (b.lat0 + b.lat1) / 2
  const hw = (b.lon1 - b.lon0) / 2 / factor
  const hh = (b.lat1 - b.lat0) / 2 / factor
  return { lon0: cx - hw, lat0: cy - hh, lon1: cx + hw, lat1: cy + hh }
}

export function panBounds(b: Bounds, dLon: number, dLat: number): Bounds {
  return { lon0: b.lon0 + dLon, lat0: b.lat0 + dLat, lon1: b.lon1 + dLon, lat1: b.lat1 + dLat }
}

/** A place on the map: `n` is how many verses name it (in the scope shown). */
export interface GeoPoint {
  place_id: number
  he: string
  kind: PlaceKind | null
  lat: number
  lon: number
  n: number
}

/** The located places as map points, with their count in the scope asked for. */
export function geoPoints(items: PlaceSite[]): GeoPoint[] {
  return items.flatMap((p) =>
    p.lat != null && p.lon != null ? [{ place_id: p.place_id, he: p.he, kind: p.kind, lat: p.lat, lon: p.lon, n: p.n_here ?? p.n_verses }] : [],
  )
}
