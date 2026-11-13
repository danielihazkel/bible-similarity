// The layers of the layered reader (DESIGN.md §16.39) and their `?layers=` URL form.

import type { Layer } from '../i18n/pages/reader'
import { byFamily, type Family, familyOfPage } from './nav'

export const LAYERS: readonly Layer[] = ['speakers', 'cola', 'leitworte', 'refrains', 'phrases', 'rare', 'wordplay', 'ketiv', 'mood', 'sources', 'turns', 'gematria', 'places', 'divine', 'reception', 'witnesses', 'mainline', 'prophetic']
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

/** The nav page of each layer's analysis: the layer's family in the reader's bar is that page's. */
export const LAYER_PAGE: Record<Layer, string> = {
  speakers: '/speech',
  cola: '/poetry',
  leitworte: '/structure',
  refrains: '/refrains',
  phrases: '/phrases',
  rare: '/vocabulary',
  wordplay: '/wordplay',
  ketiv: '/ketiv',
  mood: '/psalms',
  sources: '/pentateuch',
  turns: '/divisions',
  gematria: '/gematria',
  places: '/places',
  divine: '/divine',
  reception: '/reception',
  witnesses: '/witnesses',
  mainline: '/mainline',
  prophetic: '/prophetic',
}

/** The layers under the nav's families, in the nav's order. */
export const layerFamilies = (): (Family & { items: Layer[] })[] => byFamily([...LAYERS], (l) => familyOfPage(LAYER_PAGE[l]) ?? {})

/** Named sets of layers: the one a chapter opens with, one for a poem, one for a story, none. */
export const PRESETS = {
  default: DEFAULT_LAYERS,
  poetry: ['cola', 'leitworte', 'refrains', 'wordplay', 'mood'],
  narrative: ['speakers', 'mainline', 'turns', 'places'],
  none: [],
} as const satisfies Record<string, readonly Layer[]>
export type Preset = keyof typeof PRESETS
export const PRESET_KEYS = Object.keys(PRESETS) as Preset[]

/** The `?layers=` value of a set (null: the default set, which needs no parameter). */
export function layersParam(set: readonly Layer[]): string | null {
  const next = LAYERS.filter((l) => set.includes(l)).join(',')
  return next === LAYERS.filter((l) => DEFAULT_LAYERS.includes(l)).join(',') ? null : next
}

/** The preset the layers that are on make up, if any. */
export function presetOf(layers: Set<Layer>): Preset | undefined {
  return PRESET_KEYS.find((p) => PRESETS[p].length === layers.size && PRESETS[p].every((l) => layers.has(l)))
}
