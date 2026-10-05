import type { GoldLink } from '../api/types'
import { useT } from '../context/localeContext'

/** Marks a pair that Sefaria already cross-references; unlinked pairs show nothing. */
export function LinkBadge({ link }: { link: GoldLink | null }) {
  const m = useT()
  if (!link) return null
  // Sefaria's link types are its own English names
  const types = link.types.length ? link.types.join(', ') : m.link.untyped
  const title = link.level === 'verse' ? m.link.verseTitle(types) : m.link.passageTitle(types)
  return (
    <span className={`link-badge ${link.level}`} title={title}>
      {link.level === 'verse' ? m.link.verse : m.link.passage}
    </span>
  )
}
