// The dossier of a unit (`/dossier`): which entries are findings, and where each is read in full.

import type { DossierEntry, UnitSummary } from '../api/types'
import { unitLink } from './links'

/** Whether an entry is a finding (a chip) rather than "nothing found". */
export function isFound(e: DossierEntry): boolean {
  if (!e.computed) return false
  if (e.kind === 'voices') return e.key !== null
  if (e.kind === 'network') return e.count !== null
  return (e.count ?? 0) > 0
}

/** Where a finding is read in full: a list page limited to the unit, or the panel that shows it. */
export function entryLink(e: DossierEntry, unit: UnitSummary): string | undefined {
  const u = encodeURIComponent(unit.unit_id)
  const target = e.target_unit ?? unit.unit_id
  switch (e.kind) {
    case 'phrases':
      return `/phrases?unit=${u}`
    case 'sequences':
      return `/sequences?unit=${u}&q=all&order=any`
    case 'changes':
      return `/changes?unit=${u}`
    case 'borrowing':
      return `/borrowing?unit=${u}`
    case 'wordplay':
      return `/wordplay?unit=${u}`
    case 'alliteration':
      return `/wordplay?view=alliteration&unit=${u}`
    case 'rhymes':
      return `/wordplay?view=rhyme&rq=all&unit=${u}`
    case 'typescenes':
      return `/typescenes?unit=${u}`
    case 'discoveries':
      return `/discoveries?unit=${u}`
    case 'seams':
      return `/style?book=${unit.book_id}`
    case 'labels':
      return '/labels'
    case 'acrostic':
      return unitLink(target, '?acrostic=1')
    case 'structure':
      return unitLink(target, '?structure=1')
    case 'dating':
      return `/language?book=${unit.book_id}`
    case 'speech':
      return unitLink(unit.unit_id, '?syntax=1')
    case 'voices':
      return e.key ? `/speech?view=voices&voice=${encodeURIComponent(e.key)}` : undefined
    case 'network':
      return `/network?type=${unit.unit_type}&unit=${u}`
    case 'echoes':
      return `/network?view=directions&unit=${u}`
    case 'mirrors':
      return `/structure?view=small&unit=${u}`
    case 'allusions':
      return `/phrases?view=spread&unit=${u}`
    case 'citations':
      return `/citations?unit=${u}`
    case 'ketiv':
      return `/ketiv?unit=${u}`
    case 'divisions':
      return `/divisions?book=${unit.book_id}&unit=${u}`
    case 'names':
      return unit.unit_type === 'verse' ? undefined : '#unit-names'
  }
}
