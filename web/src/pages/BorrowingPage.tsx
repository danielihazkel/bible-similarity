import { Link } from 'react-router'
import { useBooks, useBorrowing } from '../api/hooks'
import type { BorrowingBookPair, BorrowingSequence } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { sequenceLink } from '../lib/links'
import { bookName } from '../lib/names'

const SIGNS = ['language', 'spelling', 'smoothing', 'expansion'] as const

/** Which side of each cross-book parallel looks like the borrower, and the check (§16.27). */
export function BorrowingPage() {
  const { m, locale } = useLocale()
  const t = m.bor
  const books = useBooks()
  const res = useBorrowing()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const names = new Map(books.data?.map((b) => [b.book_id, bookName(b, locale)]) ?? [])
  const name = (id: number) => names.get(id) ?? String(id)
  const n = d.checks.language?.n ?? 0
  return (
    <div className="page borrowing-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">{t.caveat}</p>
      {d.books.length === 0 ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <section aria-label={t.checkTitle}>
            <h2>{t.checkTitle}</h2>
            <p className="muted small">{t.checkLede(n)}</p>
            <ul className="sign-checks">
              {[...SIGNS, 'all_signs' as const].map((s) => {
                const c = d.checks[s]
                if (!c) return null
                const label = s === 'all_signs' ? t.allSigns : t.signs[s]
                return (
                  <li key={s}>
                    <strong title={s === 'all_signs' ? undefined : t.signHints[s]}>{label}</strong>:{' '}
                    {t.right(c.agree, c.n, c.p === null ? '—' : c.p.toExponential(0))}
                    {s !== 'all_signs' && (
                      <span className="muted small"> · {d.used_signs.includes(s) ? t.votes : t.noVote}</span>
                    )}
                  </li>
                )
              })}
            </ul>
            {d.held_out && <p>{t.heldOut(d.held_out.agree, d.held_out.n, d.held_out.unclear ?? 0)}</p>}
          </section>
          <section aria-label={t.pairs}>
            <h2>{t.pairs}</h2>
            {d.books.map((p) => (
              <BookPair key={`${p.a_book}-${p.b_book}`} p={p} name={name} />
            ))}
          </section>
        </>
      )}
    </div>
  )
}

function BookPair({ p, name }: { p: BorrowingBookPair; name: (id: number) => string }) {
  const { m } = useLocale()
  const t = m.bor
  const [src, dst] = p.direction === 'b_to_a' ? [p.b_book, p.a_book] : [p.a_book, p.b_book]
  return (
    <details className="borrow-pair">
      <summary>
        <strong>{p.direction === 'unclear' ? `${name(p.a_book)} ↔ ${name(p.b_book)}` : t.flow(name(src), name(dst))}</strong>
        {p.direction === 'unclear' && <span className="muted small"> · {t.unclear}</span>}
        {p.known && <span className="known-tag small">{t.accepted}</span>}
        <span className="muted small"> · {t.counts(p.sequences, p.direction === 'b_to_a' ? p.b_to_a : p.a_to_b, p.direction === 'b_to_a' ? p.a_to_b : p.b_to_a)}</span>
      </summary>
      <div className="table-wrap">
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.parallel}</th>
              {SIGNS.map((s) => (
                <th key={s} title={t.signHints[s]}>
                  {t.signs[s]}
                </th>
              ))}
              <th>{t.direction}</th>
            </tr>
          </thead>
          <tbody>
            {p.items.map((s) => (
              <Row key={s.seq_id} s={s} name={name} />
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

function Row({ s, name }: { s: BorrowingSequence; name: (id: number) => string }) {
  const { m, locale } = useLocale()
  const t = m.bor
  const later = (x: number | null) =>
    x === null || x === 0 ? '—' : t.later(name(x > 0 ? s.b_book : s.a_book))
  const dir =
    s.direction === 'unclear'
      ? t.unclear
      : s.direction === 'a_to_b'
        ? t.flow(name(s.a_book), name(s.b_book))
        : t.flow(name(s.b_book), name(s.a_book))
  return (
    <tr>
      <td>
        <Link to={sequenceLink(s.seq_id)}>
          {locale === 'he' ? `${s.a_label_he} ↔ ${s.b_label_he}` : `${s.a_label} ↔ ${s.b_label}`}
        </Link>
      </td>
      {SIGNS.map((k) => (
        <td key={k} className="small" title={s[k] === null ? undefined : s[k]!.toFixed(2)}>
          {later(s[k])}
        </td>
      ))}
      <td className="small">{dir}</td>
    </tr>
  )
}
