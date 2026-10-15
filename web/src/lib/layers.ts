// The layers of the layered reader (DESIGN.md §16.39) and their `?layers=` URL form.

import type { Layer } from '../i18n/pages/reader'

export const LAYERS: readonly Layer[] = ['speakers', 'cola', 'leitworte', 'refrains', 'phrases', 'rare', 'wordplay', 'ketiv', 'mood', 'sources', 'turns', 'gematria']
export const DEFAULT_LAYERS: Layer[] = ['speakers', 'leitworte', 'turns']

/** `?layers=` (comma-separated; absent: the default set, empty: none). */
export function parseLayers(v: string | null): Set<Layer> {
  if (v === null) return new Set(DEFAULT_LAYERS)
  return new Set(LAYERS.filter((l) => v.split(',').includes(l)))
}

/** The `?layers=` value with one layer switched (null: back to the default set). */
export function toggleLayer(layers: Set<Layer>, l: Layer): string | null {
  const next = LAYERS.filter((x) => (x === l) !== layers.has(x)).join(',')
  return next === DEFAULT_LAYERS.join(',') ? null : next
}
