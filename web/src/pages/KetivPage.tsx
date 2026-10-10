import { Link } from 'react-router'
import { useBooks, useKetiv, useKqPairs } from '../api/hooks'
import type { Book, KetivMeta, KqBook, KqClass, KqGrammar, KqLetter, KqPair, KqParallel } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { withFinals } from '../lib/hebrew'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookName, bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const CLASSES: KqClass[] = ['vowel_letter', 'swap', 'vowel_position', 'metathesis', 'division', 'qere_only', 'ketiv_only', 'same_letters', 'other']
const GRAMMARS: KqGrammar[] = ['spelling', 'form', 'word']
const PARALLELS: KqParallel[] = ['qere', 'ketiv', 'neither']
const LETTERS_SHOWN = 15
const fq = (q: number) => (q < 0.001 ? '< 0.001' : q < 0.01 ? q.toFixed(3) : q.toFixed(2))

function pick<T extends string>(v: string | null, options: T[]): T | undefined {
  return options.includes(v as T) ? (v as T) : undefined
}

/** What is written against what is read: every ketiv / qere described (DESIGN.md §16.30). */
export function KetivPage() {
  const { m } = useLocale()
  const t = m.kq
  const res = useKetiv()
  const books = useBooks()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { meta } = res.data
  const byId = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  return (
    <div className="page ketiv-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {meta.pairs === undefined ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <p className="small">{t.summary(meta.pairs)}</p>
          <Findings meta={meta} />
          <Classes meta={meta} />
          <div className="ketiv-tables">
            <BookTable books={res.data.books} byId={byId} />
            <LetterTable letters={res.data.letters} />
          </div>
          <Features meta={meta} />
          <PairList books={books.data ?? []} />
        </>
      )}
    </div>
  )
}

function Findings({ meta }: { meta: KetivMeta }) {
  const t = useLocale().m.kq
  const c = meta.checks
  if (!c) return null
  const la = c.lookalike
  const lf = c.late_fuller
  return (
    <section aria-label={t.findings}>
      <h2>{t.findings}</h2>
      <ul className="division-findings small">
        {la.all.share != null && (
          <li>{t.lookalike(la.all.share, la.all.expected, la.all.p, la.without_wy.share, la.without_wy.expected, la.without_wy.p)}</li>
        )}
        {lf.late != null && lf.other != null && (
          <li>{t.lateFuller(lf.late, lf.late_n ?? 0, lf.other, lf.other_n ?? 0, lf.books ?? 0, lf.p)}</li>
        )}
        <li>
          <Link to="?parallel=qere#ketiv-list">{t.parallel(c.parallel.qere, c.parallel.ketiv, c.parallel.neither, c.parallel.p)}</Link>
        </li>
        <li>{t.plural(c.plural_suffix.plural, c.plural_suffix.waw_yw)}</li>
        {(meta.euphemisms ?? 0) > 0 && (
          <li>
            <Link to="?euphemism=1#ketiv-list">{t.euphemisms(meta.euphemisms ?? 0)}</Link>
          </li>
        )}
        <li>{t.books(c.books.p)}</li>
      </ul>
    </section>
  )
}

function Classes({ meta }: { meta: KetivMeta }) {
  const { m } = useLocale()
  const t = m.kq
  return (
    <section aria-label={t.classesTitle}>
      <h2>{t.classesTitle}</h2>
      <ul className="kq-classes">
        {CLASSES.filter((c) => meta.classes?.[c]).map((c) => (
          <li key={c}>
            <Link to={`?cls=${c}#ketiv-list`}>{t.classes[c].label}</Link> <strong>{meta.classes?.[c]?.toLocaleString()}</strong>
            <span className="muted small"> · {t.classes[c].hint}</span>
          </li>
        ))}
      </ul>
      <p className="muted small">
        {GRAMMARS.filter((g) => meta.grammar?.[g])
          .map((g) => `${t.grammar[g]}: ${meta.grammar?.[g]?.toLocaleString()}`)
          .join(' · ')}
      </p>
    </section>
  )
}

function BookTable({ books, byId }: { books: KqBook[]; byId: Map<number, Book> }) {
  const { m, locale } = useLocale()
  const t = m.kq
  const rows = [...books].filter((b) => b.n > 0).sort((a, b) => b.rate - a.rate)
  return (
    <section aria-label={t.booksTitle}>
      <h2>{t.booksTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.bookCols.book}</th>
              <th className="num">{t.bookCols.n}</th>
              <th className="num">{t.bookCols.rate}</th>
              <th className="num">{t.bookCols.fuller}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => {
              const book = byId.get(b.book_id)
              return (
                <tr key={b.book_id}>
                  <td>
                    <Link to={`?book=${b.book_id}#ketiv-list`}>{book ? bookName(book, locale) : b.book_id}</Link>
                  </td>
                  <td className="num">{b.n.toLocaleString()}</td>
                  <td className="num">{b.rate.toFixed(1)}</td>
                  <td className="num">{b.ketiv_fuller == null ? '–' : `${Math.round(b.ketiv_fuller * 100)}%`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function LetterTable({ letters }: { letters: KqLetter[] }) {
  const t = useLocale().m.kq
  return (
    <section aria-label={t.lettersTitle}>
      <h2>{t.lettersTitle}</h2>
      <p className="muted small">{t.lettersLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.lettersTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.letterCols.pair}</th>
              <th className="num">{t.letterCols.n}</th>
              <th className="num">{t.letterCols.expected}</th>
              <th className="num">{t.letterCols.ratio}</th>
              <th className="num">{t.letterCols.q}</th>
            </tr>
          </thead>
          <tbody>
            {letters.slice(0, LETTERS_SHOWN).map((l) => (
              <tr key={l.pair}>
                <td>
                  <span dir="rtl" lang="he" className="he">
                    {l.pair[0]} / {l.pair[1]}
                  </span>
                  {l.lookalike && ' ★'}
                </td>
                <td className="num">{l.n}</td>
                <td className="num">{l.expected.toFixed(1)}</td>
                <td className="num">{l.ratio == null ? '–' : `×${l.ratio.toFixed(1)}`}</td>
                <td className="num">{fq(l.q)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Features({ meta }: { meta: KetivMeta }) {
  const t = useLocale().m.kq
  if (!meta.features?.length) return null
  return (
    <section aria-label={t.featuresTitle}>
      <h2>{t.featuresTitle}</h2>
      <ul className="kq-features small">
        {meta.features.map(([f, n]) => (
          <li key={f}>
            {t.feature(f)} <span className="muted">· {n.toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function PairList({ books }: { books: Book[] }) {
  const { m, locale } = useLocale()
  const t = m.kq
  const [params, update] = useQueryParams()
  const cls = pick(params.get('cls'), CLASSES)
  const grammar = pick(params.get('grammar'), GRAMMARS)
  const parallel = pick(params.get('parallel'), PARALLELS)
  const euphemism = params.get('euphemism') === '1' ? true : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const res = useKqPairs({ cls, grammar, parallel, euphemism, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listTitle} id="ketiv-list">
      <h2>{t.listTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{t.filters.cls}</span>
          <select value={cls ?? ''} onChange={(e) => set({ cls: e.target.value || null })}>
            <option value="">{t.filters.any}</option>
            {CLASSES.map((c) => (
              <option key={c} value={c}>
                {t.classes[c].label}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.filters.grammar}</span>
          <select value={grammar ?? ''} onChange={(e) => set({ grammar: e.target.value || null })}>
            <option value="">{t.filters.any}</option>
            {GRAMMARS.map((g) => (
              <option key={g} value={g}>
                {t.grammar[g]}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.filters.parallel}</span>
          <select value={parallel ?? ''} onChange={(e) => set({ parallel: e.target.value || null })}>
            <option value="">{t.filters.any}</option>
            {PARALLELS.map((p) => (
              <option key={p} value={p}>
                {t.parallelOpt[p]}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.filters.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.par.allBooks}</option>
            {books.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={euphemism === true} onChange={(e) => set({ euphemism: e.target.checked ? '1' : null })} />
          {t.filters.euphemism}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.none}
        summary={(data) => t.page(data.total, page, pages)}
      >
        {(data, stale) => (
          <ol className={`disc-list ${stale}`}>
            {data.items.map((p) => (
              <PairItem key={p.kq_id} p={p} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function PairItem({ p }: { p: KqPair }) {
  const { m, locale } = useLocale()
  const t = m.kq
  const highlight: Highlight = new Map(p.display.map((i) => [i, 'focus']))
  return (
    <li className="disc kq-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${p.verse_id}`)}>{locale === 'he' ? p.label_he : p.label}</Link>
        <span className="kq-pair" dir="rtl" lang="he">
          <span className="kq-side" title={t.written}>
            {p.ketiv || t.nothing}
          </span>
          <span className="muted"> ← </span>
          <span className="kq-side kq-read" title={t.read}>
            {p.qere || t.nothing}
          </span>
        </span>
        <span className="phrase-tag" title={t.classes[p.cls].hint}>
          {t.classes[p.cls].label}
        </span>
        {p.letters && (
          <span className="small he" dir="rtl" lang="he">
            {p.letters.replace('>', ' ← ')}
          </span>
        )}
        {p.fuller && <span className="muted small">{t.fullerTag(p.fuller)}</span>}
        {p.euphemism && <span className="small">{t.euphemismTag}</span>}
      </div>
      {p.features.length > 0 && <p className="muted small kq-features-line">{p.features.map(t.feature).join(' · ')}</p>}
      {p.parallel && p.partner_vid !== null && (
        <p className="small">
          <Link to={unitLink(`v:${p.partner_vid}`)}>
            {t.partner((locale === 'he' ? p.partner_label_he : p.partner_label) ?? '', withFinals(p.partner_form ?? ''), p.parallel)}
          </Link>
        </p>
      )}
      <HebrewText verse={p.verse} highlight={highlight} />
    </li>
  )
}
