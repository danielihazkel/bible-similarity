import { Link } from 'react-router'
import { useAcrostics, useBooks, acrosticsParams } from '../api/hooks'
import { AcrosticChain } from '../components/AcrosticChain'
import { ExportCsv } from '../components/ExportCsv'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { bookName, bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const Q_OPTIONS = ['0.05', '0.5', 'all']

/** Chapters whose lines run through the alphabet (alphabetic acrostics, whole or broken). */
export function AcrosticsPage() {
  const { m, locale } = useLocale()
  const t = m.pat.acrostics
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const qRaw = params.get('q') ?? '0.05'
  const qChoice = Q_OPTIONS.includes(qRaw) ? qRaw : '0.05'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = {
    maxQ: qChoice === 'all' ? undefined : Number(qChoice),
    book,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const res = useAcrostics(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const nameOf = (id: number) => {
    const b = books.data?.find((x) => x.book_id === id)
    return b ? bookName(b, locale) : ''
  }

  return (
    <div className="page acrostics-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.data?.known_recall != null && <p className="muted small">{t.check(res.data.known_recall)}</p>}
      <div className="toolbar">
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.pat.show}</span>
          <select value={qChoice} onChange={(e) => set({ q: e.target.value === '0.05' ? null : e.target.value })}>
            {Q_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {t.q[o]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{t.empty}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.pat.chapters(res.data.total)} · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'acrostics', params: acrosticsParams(query) }}
              filename={`acrostics-p${page}.csv`}
              rows={() =>
                res.data.items.map((a) => ({
                  chapter: a.unit.label_en,
                  letters: a.n_letters,
                  skipped: a.missing,
                  from: a.first_letter,
                  to: a.last_letter,
                  lines: a.granularity,
                  order: a.order_name,
                  p: a.p,
                  q: a.q,
                }))
              }
            />
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((a) => (
              <li key={a.unit.unit_id} className="disc acrostic-card">
                <div className="hit-head">
                  <Link to={unitLink(a.unit.unit_id, '?acrostic=1')}>
                    {unitLabel(a.unit, locale)}
                    {locale === 'en' && (
                      <>
                        {' '}
                        <span className="he-label" dir="rtl" lang="he">
                          {a.unit.label_he}
                        </span>
                      </>
                    )}
                  </Link>
                  <span className="phrase-tag">{t.letters(a.n_letters, a.missing)}</span>
                  <span className="muted small">
                    {m.granularity[a.granularity]}
                    {a.order_name === 'pe-ayin' && t.peAyin}
                  </span>
                  <span className={`small ${a.q <= 0.05 ? 'q-strong' : 'muted'}`} title={t.qTitle}>
                    {m.q(a.q)}
                  </span>
                  {!book && <span className="muted small">{nameOf(a.unit.book_id)}</span>}
                </div>
                <AcrosticChain a={a} />
              </li>
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}
