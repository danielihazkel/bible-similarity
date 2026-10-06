import { Link } from 'react-router'
import { useBorrowingBetween, useBorrowingSequence } from '../api/hooks'
import type { BorrowingSequence } from '../api/types'
import { useLocale } from '../context/localeContext'

/** "Which borrowed?" for one scored parallel (DESIGN.md §16.27). */
export function BorrowSentence({ s }: { s: BorrowingSequence }) {
  const { m, locale } = useLocale()
  const t = m.bor
  const a = locale === 'he' ? s.a_label_he : s.a_label
  const b = locale === 'he' ? s.b_label_he : s.b_label
  if (s.direction === 'unclear') return <>{t.lineUnclear(a, b)}</>
  const [src, dst] = s.direction === 'a_to_b' ? [a, b] : [b, a]
  return <>{t.line(src, dst, Math.abs(s.votes))}</>
}

export function BorrowLineForSequence({ seqId }: { seqId: number }) {
  const t = useLocale().m.bor
  const res = useBorrowingSequence(seqId)
  if (!res.data) return null
  return (
    <p className="muted small borrow-line">
      <BorrowSentence s={res.data} /> · <Link to="/borrowing">{t.title}</Link>
    </p>
  )
}

export function BorrowLineBetween({ a, b }: { a: string; b: string }) {
  const t = useLocale().m.bor
  const res = useBorrowingBetween(a, b)
  if (!res.data || res.data.length === 0) return null
  return (
    <ul className="muted small borrow-line">
      {res.data.map((s) => (
        <li key={s.seq_id}>
          <BorrowSentence s={s} /> · <Link to={`/sequences/${s.seq_id}`}>{t.parallel}</Link>
        </li>
      ))}
    </ul>
  )
}
