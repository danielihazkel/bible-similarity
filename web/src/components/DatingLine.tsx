import { Link } from 'react-router'
import { useUnitDating } from '../api/hooks'
import { useLocale } from '../context/localeContext'

/** A chapter's Late Biblical Hebrew profile in one line (DESIGN.md §16.24). */
export function DatingLine({ unitId, bookId }: { unitId: string; bookId: number }) {
  const { m } = useLocale()
  const t = m.dat
  const res = useUnitDating(unitId)
  const d = res.data
  if (!d || d.score === null) return null
  return (
    <p className="muted small unit-dating">
      <Link to={`/language?book=${bookId}`}>{t.unitLine(d.score.toFixed(2))}</Link>
      {d.out_of_domain && t.unitPoetry}
      {d.drivers.length > 0 && ` · ${t.unitDrivers}: ${d.drivers.map((f) => t.features[f] ?? f).join(' · ')}`}
    </p>
  )
}
