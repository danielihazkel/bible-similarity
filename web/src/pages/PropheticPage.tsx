import { Link } from 'react-router'
import { useBooks, useProphetic, usePropheticItems } from '../api/hooks'
import { isStageMissing } from '../api/client'
import type { ProphItem, PropheticResponse } from '../api/types'
import { BookSelect, KnownOnly, Choice } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { PrecisionNote } from '../components/PrecisionNote'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { readLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import type { ProphFormKey } from '../i18n/pages/prophetic'
import '../i18n/pages/prophetic'
import '../styles/pages/PropheticPage.css'

const PAGE_SIZE = 25
const FORMS: ProphFormKey[] = ['messenger', 'woe', 'nations', 'lawsuit', 'call']
const isForm = (x: string | null): x is ProphFormKey => FORMS.includes(x as ProphFormKey)

/** The forms of prophetic speech (DESIGN.md §16.92, D154): each form's findings by book, the
 * passages named in advance, and the findings with the words that mark them. */
export function PropheticPage() {
  const { m } = useLocale()
  const t = m.proph
  const res = useProphetic()
  const d = res.data
  return (
    <div className="page prophetic-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <PrecisionNote detector="prophetic" />
      {isStageMissing(res.error) ? (
        <NotComputed>{t.noData}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <Forms d={d} />
          <Known d={d} />
          <Books d={d} />
          <Items />
        </>
      )}
    </div>
  )
}

function Forms({ d }: { d: PropheticResponse }) {
  const t = useLocale().m.proph
  return (
    <section aria-label={t.form}>
      <p className="muted small">{t.counts(d.items)}</p>
      <dl className="pf-forms">
        {FORMS.map((f) => (
          <div key={f}>
            <dt>
              {t.forms[f]}: {t.formCount(d.counts[f] ?? 0)}
            </dt>
            <dd className="muted small">{t.formHints[f]}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Known({ d }: { d: PropheticResponse }) {
  const t = useLocale().m.proph
  return (
    <section aria-labelledby="pf-known">
      <h2 id="pf-known">{t.knownTitle}</h2>
      <p className="muted small">{t.knownLede(d.known_cover)}</p>
      <ul className="pf-known">
        {FORMS.filter((f) => d.known[f]).map((f) => {
          const k = d.known[f]
          return (
            <li key={f}>
              <span className={`dv-verdict ${k.holds ? 'holds' : 'fails'}`}>{t.verdict[k.holds ? 'holds' : 'fails']}</span> <strong>{t.forms[f]}</strong>{' '}
              {t.known(k.found, k.refs.length)}
              <ul className="small">
                {k.refs.map((r) => (
                  <li key={r.ref}>{t.knownRef(r.ref, r.found, r.cover)}</li>
                ))}
              </ul>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function Books({ d }: { d: PropheticResponse }) {
  const { m, locale } = useLocale()
  const t = m.proph
  const books = useBooks()
  const named = new Map((books.data ?? []).map((b) => [b.book_id, bookName(b, locale)]))
  return (
    <section aria-labelledby="pf-books">
      <h2 id="pf-books">{t.booksTitle}</h2>
      <p className="muted small">{t.booksLede}</p>
      <TableCsv name="prophetic-books" tabIndex={0} role="region" aria-labelledby="pf-books">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">{t.book}</th>
              {FORMS.map((f) => (
                <th key={f} scope="col" className="num">
                  {t.forms[f]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => (
              <tr key={b.book_id}>
                <td>{named.get(b.book_id) ?? b.book_id}</td>
                {FORMS.map((f) => (
                  <td key={f} className="num">
                    {b.counts[f] ?? 0}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function Items() {
  const { m, locale } = useLocale()
  const t = m.proph
  const [params, update] = useQueryParams()
  const fp = params.get('form')
  const form = isForm(fp) ? fp : undefined
  const bp = params.get('book')
  const book = bp === null || bp === '' ? undefined : Number(bp)
  const known = params.get('known') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = usePropheticItems({ form, book, known, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const options = [{ value: 'all', label: t.allForms }, ...FORMS.map((f) => ({ value: f, label: t.forms[f] }))]
  return (
    <section aria-labelledby="pf-items">
      <h2 id="pf-items">{t.listTitle}</h2>
      <div className="toolbar">
        <Choice<string> label={t.form} value={form ?? 'all'} options={options} onChange={(v) => set({ form: v === 'all' ? null : v })} />
        <BookSelect label={m.search.book} all={m.search.allBooks} books={books.data} value={book} onChange={(v) => set({ book: v })} />
        <KnownOnly checked={known} label={t.knownOnly} onChange={(on) => set({ known: on ? '1' : null })} />
      </div>
      <PagedList csv="prophetic" res={res} empty={t.none} summary={(d, p, pages) => t.itemCount(d.total, p, pages)}>
        {(d, stale) => (
          <ol className={`hits pf-items ${stale}`}>
            {d.items.map((x) => (
              <Item key={x.item_id} x={x} locale={locale} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function details(x: ProphItem, t: ReturnType<typeof useLocale>['m']['proph']): string[] {
  const d = x.detail
  const out: string[] = []
  if (d.kind) out.push(t.kind[d.kind])
  if (d.names?.length) out.push(t.names(d.names.slice(0, 4).map((n) => n.he).join(', ')))
  if (d.heading) out.push(t.heading)
  if (d.paragraphs && d.paragraphs > 1) out.push(t.paragraphs(d.paragraphs))
  if (d.dispute) out.push(t.dispute)
  if (d.witnesses) out.push(t.witnesses)
  if (d.objection) out.push(t.objection)
  if (d.reassurance) out.push(t.reassurance)
  if (x.known) out.push(t.namedTag)
  return out
}

function Item({ x, locale }: { x: ProphItem; locale: 'en' | 'he' }) {
  const t = useLocale().m.proph
  const first = locale === 'he' ? x.first_label_he : x.first_label
  const last = locale === 'he' ? x.last_label_he : x.last_label
  const rest = x.last_vid - x.first_vid + 1 - x.verses.length
  return (
    <li className={`hit pf-item pf-${x.form}`}>
      <div className="hit-head">
        <span className="verse-ref">{x.first_vid === x.last_vid ? first : `${first} – ${last}`}</span>{' '}
        <span className="muted small">{[t.forms[x.form as ProphFormKey], ...details(x, t)].join(' · ')}</span>
      </div>
      {x.verses.map((v) => {
        const hl: Highlight = new Map((x.marks[String(v.verse_id)] ?? []).map((i) => [i, 'focus']))
        return (
          <p key={v.verse_id} className="hit-text">
            <HebrewText verse={v} highlight={hl} />
          </p>
        )
      })}
      {rest > 0 && <p className="muted small">{t.more(rest)}</p>}
      <p className="small">
        <Link to={readLink(x.unit_id, '?layers=prophetic')}>{t.read}</Link>
      </p>
    </li>
  )
}
