import type { GoldLink } from '../api/types'

/** Marks a pair that Sefaria already cross-references; unlinked pairs show nothing. */
export function LinkBadge({ link }: { link: GoldLink | null }) {
  if (!link) return null
  const types = link.types.length ? link.types.join(', ') : 'untyped'
  const title =
    link.level === 'verse'
      ? `Sefaria links these verses (${types})`
      : `A Sefaria passage-level link covers this pair (${types})`
  return (
    <span className={`link-badge ${link.level}`} title={title}>
      {link.level === 'verse' ? 'Sefaria link' : 'Sefaria passage'}
    </span>
  )
}
