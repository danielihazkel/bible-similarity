// The registry of the unit page's data panels: which panel is shown where and for which unit
// types, the dossier entry that says whether it has anything to fetch, and the section it adds to
// the page. The panels themselves are in `components/UnitPanels.tsx`, by id.

import type { DossierKind, UnitSummary } from '../api/types'
import type { Messages } from '../i18n'
import '../i18n/pages/places'

export type PanelId = 'names' | 'network' | 'where' | 'themes' | 'dating' | 'phrases' | 'wordplay' | 'sequences'

export interface PanelSpec {
  id: PanelId
  /** `context`: under the text, before the word panel; `after`: under the similar units. */
  slot: 'context' | 'after'
  /** The unit types the panel is shown for. */
  types: readonly UnitSummary['unit_type'][]
  /** The dossier entry that says whether there is anything to fetch. */
  dossier?: DossierKind
  /** A section of the page with a heading of its own: its name in the page's section strip. */
  section?: (m: Messages) => string
}

const PASSAGES = ['chapter', 'pericope', 'parasha'] as const
const ALL = ['verse', ...PASSAGES] as const

/** The unit page's data panels, in page order. */
export const UNIT_PANELS: readonly PanelSpec[] = [
  { id: 'names', slot: 'context', types: PASSAGES },
  { id: 'network', slot: 'context', types: PASSAGES },
  { id: 'where', slot: 'context', types: ['chapter', 'pericope'], section: (m) => m.pl.whereTitle },
  { id: 'themes', slot: 'context', types: PASSAGES },
  { id: 'dating', slot: 'context', types: ['chapter'] },
  { id: 'phrases', slot: 'after', types: ['verse'], dossier: 'phrases', section: (m) => m.unit.sharedPhrases },
  { id: 'wordplay', slot: 'after', types: ALL, dossier: 'wordplay', section: (m) => m.unit.wordplay },
  { id: 'sequences', slot: 'after', types: ALL, dossier: 'sequences', section: (m) => m.unit.runs },
]

/** The id of a panel's root element: what a link to it, and the section strip, jump to. */
export const panelAnchor = (id: PanelId) => `unit-${id}`

/** The registered panels of one slot for a unit, in page order. */
export const panelsFor = (unit: UnitSummary, slot: PanelSpec['slot']): PanelSpec[] => UNIT_PANELS.filter((p) => p.slot === slot && p.types.includes(unit.unit_type))

/** The sections the panels of a slot may add to a unit's page, in page order: the section strip
 * lists those that are drawn. */
export function panelSections(unit: UnitSummary, slot: PanelSpec['slot'], m: Messages): { id: string; label: string }[] {
  return panelsFor(unit, slot).flatMap((p) => (p.section ? [{ id: panelAnchor(p.id), label: p.section(m) }] : []))
}
