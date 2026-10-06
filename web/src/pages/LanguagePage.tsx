import { Link } from 'react-router'
import { useBooks, useDating, useDatingBook } from '../api/hooks'
import type { DatingBook } from '../api/types'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { hebrewNumeral } from '../lib/hebrew'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const fmt = (x: number | null) => (x === null ? '—' : x.toFixed(2))

/** The Late Biblical Hebrew profile of every book and chapter (DESIGN.md §16.24). */
export function LanguagePage() {
  const { m, locale } = useLocale()
  const t = m.dat
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  const res = useDating()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const names = new Map(books.data?.map((b) => [b.book_id, bookName(b, locale)]) ?? [])
  const syn = d.synoptic
  return (
    <div className="page language-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">{t.caveat}</p>
      {d.books.length === 0 ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          {d.held_out_auc !== null && d.held_out_auc_grammar !== null && (
            <p className="muted small">{t.check(d.held_out_auc.toFixed(2), d.held_out_auc_grammar.toFixed(2))}</p>
          )}
          {syn.pairs ? (
            <section aria-label={t.examplesTitle}>
              <p>{t.synoptic(syn.later ?? 0, syn.pairs, (syn.p ?? 1).toExponential(0), syn.later_grammar ?? 0)}</p>
              <details>
                <summary>{t.examplesTitle}</summary>
                <ul className="synoptic-list">
                  {d.synoptic_examples.map((e) => (
                    <li key={`${e.early_first}-${e.late_first}`}>
                      <Link to={unitLink(`v:${e.early_first}`)}>{locale === 'he' ? e.early_label_he : e.early_label}</Link>{' '}
                      <span className="muted small">{e.early_score.toFixed(2)}</span> →{' '}
                      <Link to={unitLink(`v:${e.late_first}`)}>{locale === 'he' ? e.late_label_he : e.late_label}</Link>{' '}
                      <span className="muted small">{e.late_score.toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          ) : null}

          <section aria-label={t.byBook}>
            <h2>{t.byBook}</h2>
            <p className="muted small">{t.byBookLede}</p>
            <ul className="profile-bars">
              {d.books.map((b) => (
                <BookBar
                  key={b.book_id}
                  b={b}
                  name={names.get(b.book_id) ?? String(b.book_id)}
                  on={book === b.book_id}
                  onPick={() => update({ book: book === b.book_id ? null : String(b.book_id) }, false)}
                />
              ))}
            </ul>
          </section>
          {book !== undefined && <BookChapters bookId={book} name={names.get(book) ?? String(book)} />}
        </>
      )}
    </div>
  )
}

function BookBar({ b, name, on, onPick }: { b: DatingBook; name: string; on: boolean; onPick: () => void }) {
  const t = useLocale().m.dat
  const tags = [b.role === 'scored' ? '' : t.roles[b.role], b.out_of_domain ? t.outOfDomain : '']
    .filter(Boolean)
    .join(' · ')
  return (
    <li className={`${b.role} ${b.out_of_domain ? 'out-of-domain' : ''}`}>
      <button type="button" className={on ? 'on' : undefined} aria-pressed={on} onClick={onPick}>
        <span className="bar-label">{name}</span>
        <span className="bar-track" aria-hidden="true">
          {b.low !== null && b.high !== null && (
            <span className="bar-range" style={{ insetInlineStart: `${b.low * 100}%`, width: `${(b.high - b.low) * 100}%` }} />
          )}
          {b.score !== null && <span className="bar-mark" style={{ insetInlineStart: `${b.score * 100}%` }} />}
        </span>
        <span className="bar-n">{fmt(b.score)}</span>
        <span className="muted small bar-tags">{tags}</span>
      </button>
    </li>
  )
}

function BookChapters({ bookId, name }: { bookId: number; name: string }) {
  const { m, locale } = useLocale()
  const t = m.dat
  const res = useDatingBook(bookId)
  if (res.error) return <PanelError what={t.chapters(name)} error={res.error} />
  if (!res.data) return <Loading />
  return (
    <section aria-label={t.chapters(name)}>
      <h2>{t.chapters(name)}</h2>
      <div className="table-wrap">
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.chapter}</th>
              <th className="num">{t.words}</th>
              <th>{t.score}</th>
              <th>{t.drivers}</th>
            </tr>
          </thead>
          <tbody>
            {res.data.map((c) => (
              <tr key={c.unit_id} className={c.out_of_domain ? 'out-of-domain' : undefined}>
                <td>
                  <Link to={unitLink(c.unit_id)}>{locale === 'he' ? `${name} ${hebrewNumeral(c.chapter)}` : `${name} ${c.chapter}`}</Link>
                  {c.out_of_domain && <span className="muted small"> · {t.outOfDomain}</span>}
                </td>
                <td className="num">{m.num(c.n_words)}</td>
                <td title={c.role !== 'scored' ? t.heldOut : undefined}>
                  {c.score === null ? (
                    <span className="muted small">{t.tooShort}</span>
                  ) : (
                    <span className="score-cell">
                      <span className="bar-track" aria-hidden="true">
                        <span className="bar-fill" style={{ width: `${c.score * 100}%` }} />
                      </span>
                      <span className="num">{c.score.toFixed(2)}</span>
                    </span>
                  )}
                </td>
                <td className="small">{c.drivers.map((f) => t.features[f] ?? f).join(' · ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
