import { Link } from 'react-router'
import { useBooks, useMasorah } from '../api/hooks'
import type { Book, MasorahMiddle, MasorahResponse, MasorahText, MasorahTotal } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const TEXTS: MasorahText[] = ['ketiv', 'qere']

/** The Masorah's counts (§16.55): the middles the tradition names against ours, each book's verse
 * total against ours with the reason it differs, and every book counted in both texts. */
export function MasorahPage() {
  const { m } = useLocale()
  const t = m.msr
  const res = useMasorah()
  const [params, update] = useQueryParams()
  return (
    <div className="page masorah-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.meta.checks ? (
        <p className="status">{t.noData}</p>
      ) : (
        <Body
          data={res.data}
          text={params.get('text') === 'qere' || params.get('text') === 'ketiv' ? (params.get('text') as MasorahText) : (res.data.meta.text ?? 'ketiv')}
          setText={(v) => update({ text: v === (res.data.meta.text ?? 'ketiv') ? null : v })}
        />
      )}
    </div>
  )
}

function Body({ data, text, setText }: { data: MasorahResponse; text: MasorahText; setText: (t: MasorahText) => void }) {
  const t = useLocale().m.msr
  const meta = data.meta
  const books = useBooks()
  const byId = new Map(books.data?.map((b) => [b.book_id, b]))
  const byName = new Map(books.data?.map((b) => [b.name, b]))
  return (
    <>
      {meta.torah && <p>{t.summary(meta.torah.verses, meta.torah.words_ketiv, meta.torah.letters_ketiv, meta.torah.words_qere, meta.torah.letters_qere)}</p>}
      {meta.kq && <p className="muted small">{t.kq(meta.kq.pairs, meta.kq.changed.ketiv, meta.kq.changed.qere)}</p>}
      <section aria-label={t.middlesTitle}>
        <h2>{t.middlesTitle}</h2>
        <p className="muted small">{t.middlesLede(meta.tolerance ?? 1)}</p>
        <div className="toolbar">
          <Segmented label={t.text} value={text} onChange={setText} options={TEXTS.map((x) => ({ value: x, label: t.texts[x] }))} />
        </div>
        <ol className="msr-middles">
          {data.middles
            .filter((r) => r.text === null || r.text === text)
            .map((r) => (
              <MiddleItem key={`${r.claim}:${r.text}`} r={r} book={byName.get(r.span)} />
            ))}
        </ol>
      </section>
      <Totals rows={data.totals.filter((r) => r.scope === 'book')} byId={byId} />
      <Sections rows={data.totals.filter((r) => r.scope === 'section')} />
      <BookCounts data={data} byId={byId} />
    </>
  )
}

function MiddleItem({ r, book }: { r: MasorahMiddle; book?: Book }) {
  const { m, locale } = useLocale()
  const t = m.msr
  const span = r.span === 'Torah' ? t.torah : book ? bookName(book, locale) : r.span
  const ref = (v: MasorahMiddle['trad_verse']) => (locale === 'he' ? v.ref_he : v.ref)
  const even = r.n % 2 === 0
  const pos = Math.floor(r.mid_pos) + 1
  const trad =
    r.unit === 'letter' && r.trad_word && r.trad_letter
      ? `${t.tradLetter(r.trad_letter, r.trad_word)}, `
      : r.unit === 'word' && r.trad_word
        ? `${t.tradWords(r.trad_word)}, `
        : ''
  const ours = r.unit === 'letter' && r.mid_word && r.mid_letter ? `${t.oursLetter(r.mid_letter, r.mid_word)}, ` : r.unit === 'word' && r.mid_word ? `${r.mid_word}, ` : ''
  const mark = (tok: number | null | undefined): Highlight => (tok != null && tok >= 0 ? new Map([[tok, 'focus']]) : new Map())
  const same = r.trad_verse.verse_id === r.mid_verse.verse_id
  return (
    <li className="msr-middle">
      <div className="hit-head">
        <b>{t.heading(span, t.units[r.unit])}</b> <span className={`dlg-verdict ${r.holds ? 'holds' : 'fails'}`}>{r.holds ? t.verdict.holds : t.verdict.fails}</span>
      </div>
      <p>
        {t.says(t.sources[r.source])} {trad}
        <Link to={unitLink(`v:${r.trad_verse.verse_id}`)}>{ref(r.trad_verse)}</Link>. {t.ours} {ours}
        <Link to={unitLink(`v:${r.mid_verse.verse_id}`)}>{ref(r.mid_verse)}</Link> ({t.position(r.unit, pos, r.n, even)}). {t.distance(r.unit, r.distance, r.verses_apart)}
      </p>
      {r.unit !== 'verse' && (
        <div className="msr-verses">
          <p className="hit-text">
            <span className="muted small">{t.tradVerse}: </span>
            <HebrewText verse={r.trad_verse} highlight={mark(r.trad_tok)} />
          </p>
          {!same && (
            <p className="hit-text">
              <span className="muted small">{t.ourVerse}: </span>
              <HebrewText verse={r.mid_verse} highlight={mark(r.mid_tok)} />
            </p>
          )}
        </div>
      )}
    </li>
  )
}

function signed(n: number, num: (n: number) => string) {
  return n > 0 ? `+${num(n)}` : n < 0 ? `−${num(-n)}` : num(0)
}

function RefRange({ r }: { r: MasorahTotal }) {
  const { locale } = useLocale()
  if (!r.ref_first) return null
  const first = locale === 'he' ? r.ref_first.label_he : r.ref_first.label_en
  const last = r.ref_last && r.ref_last.verse_id !== r.ref_first.verse_id ? (locale === 'he' ? r.ref_last.label_he : r.ref_last.label_en) : null
  return (
    <Link to={unitLink(`v:${r.ref_first.verse_id}`)}>
      {first}
      {last ? `–${last.replace(/^.*:/, '')}` : ''}
    </Link>
  )
}

function groupName(r: MasorahTotal, byId: Map<number, Book>, locale: string, groups: Record<string, string>) {
  if (r.name) return groups[r.name] ?? r.name
  const b = byId.get(r.first_book)
  return b ? bookName(b, locale) : String(r.first_book)
}

function Totals({ rows, byId }: { rows: MasorahTotal[]; byId: Map<number, Book> }) {
  const { m, locale } = useLocale()
  const t = m.msr
  if (rows.length === 0) return null
  const agree = rows.filter((r) => r.diff === 0).length
  return (
    <section aria-label={t.totalsTitle} id="totals">
      <h2>{t.totalsTitle}</h2>
      <p className="muted small">{t.totalsLede}</p>
      <p>{t.booksAgree(agree, rows.length)}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.totalsTitle}>
        <table className="change-table msr-totals">
          <thead>
            <tr>
              <th>{t.cols.book}</th>
              <th>{t.cols.tradition}</th>
              <th>{t.cols.ours}</th>
              <th>{t.cols.diff}</th>
              <th>{t.cols.why}</th>
              <th>{t.cols.also}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.first_book}:${r.last_book}`} className={r.diff === 0 ? undefined : 'msr-differs'}>
                <td>{groupName(r, byId, locale, t.groups)}</td>
                <td className="num">{m.num(r.tradition)}</td>
                <td className="num">{m.num(r.ours)}</td>
                <td className="num">{r.diff === 0 ? <span className="muted">{t.agree}</span> : signed(r.diff, m.num)}</td>
                <td>
                  {r.reason && (
                    <>
                      {t.reasons[r.reason]} <RefRange r={r} />
                    </>
                  )}
                </td>
                <td className="num">{r.also.map((x) => m.num(x)).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Sections({ rows }: { rows: MasorahTotal[] }) {
  const { m } = useLocale()
  const t = m.msr
  if (rows.length === 0) return null
  return (
    <section aria-label={t.sectionsTitle}>
      <h2>{t.sectionsTitle}</h2>
      <p className="muted small">{t.sectionsLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.sectionsTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.sectionCols.section}</th>
              <th>{t.sectionCols.count}</th>
              <th>{t.sectionCols.source}</th>
              <th>{t.sectionCols.tradition}</th>
              <th>{t.sectionCols.ours}</th>
              <th>{t.sectionCols.diff}</th>
              <th>{t.sectionCols.bookSum}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.name ? (t.groups[r.name] ?? r.name) : ''}</td>
                <td>{t.countOf(t.totalUnits[r.unit], r.text ? t.texts[r.text] : null)}</td>
                <td>{t.sources[r.source]}</td>
                <td className="num">{m.num(r.tradition)}</td>
                <td className="num">{m.num(r.ours)}</td>
                <td className="num">{signed(r.diff, m.num)}</td>
                <td className="num">{r.book_sum == null ? '' : m.num(r.book_sum)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function BookCounts({ data, byId }: { data: MasorahResponse; byId: Map<number, Book> }) {
  const { m } = useLocale()
  const t = m.msr
  if (data.books.length === 0) return null
  const c = t.booksCols
  return (
    <section aria-label={t.booksTitle}>
      <h2>{t.booksTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{c.book}</th>
              <th>{c.verses}</th>
              <th>{c.wordsK}</th>
              <th>{c.wordsQ}</th>
              <th>{c.lettersK}</th>
              <th>{c.lettersQ}</th>
            </tr>
          </thead>
          <tbody>
            {data.books.map((b) => {
              const book = byId.get(b.book_id)
              return (
                <tr key={b.book_id}>
                  <td>{book ? <UnitName en={book.name} he={book.he_name} /> : b.book_id}</td>
                  <td className="num">{m.num(b.verses)}</td>
                  <td className="num">{m.num(b.words_ketiv)}</td>
                  <td className="num">{m.num(b.words_qere)}</td>
                  <td className="num">{m.num(b.letters_ketiv)}</td>
                  <td className="num">{m.num(b.letters_qere)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
