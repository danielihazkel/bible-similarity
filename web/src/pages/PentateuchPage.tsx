import { Link } from 'react-router'
import { usePentateuch, usePentateuchChapters } from '../api/hooks'
import type { PentateuchResponse, SourceWord } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { readLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 60
const BOOKS: [string, number][] = [
  ['Genesis', 0],
  ['Exodus', 1],
  ['Leviticus', 2],
  ['Numbers', 3],
]
const FIXED = { chunk: 10, smooth: 2 }

/** The Pentateuch's sources (§16.43): an unsupervised P / non-P split against the critics' P. */
export function PentateuchPage() {
  const { m } = useLocale()
  const t = m.pent
  const res = usePentateuch()
  return (
    <div className="page pentateuch-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.meta.tests ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Tests data={res.data} />
          <Words data={res.data} />
          <Chapters />
        </>
      )}
    </div>
  )
}

const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)

function Tests({ data }: { data: PentateuchResponse }) {
  const { m } = useLocale()
  const t = m.pent
  const meta = data.meta
  const k = meta.tests!
  const c = meta.confusion
  const n = meta.names
  return (
    <section aria-label={t.testsTitle}>
      <h2>{t.testsTitle}</h2>
      <p>{t.split(k.kappa.observed, k.kappa.null, k.kappa.p, meta.agreement ?? 0)}</p>
      <p>{t.genesis(k.kappa_genesis.observed, k.kappa_genesis.null, k.kappa_genesis.p)}</p>
      {n && <p>{t.names(k.names.observed, k.names.null, k.names.p, n.p_like.share, n.non_p.share, n.reference_p, n.reference_non)}</p>}
      {c && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.confusionTitle}>
          <table className="change-table pent-confusion">
            <caption>{t.confusionTitle}</caption>
            <thead>
              <tr>
                <th />
                <th className="num">{t.confusion.colP}</th>
                <th className="num">{t.confusion.colNon}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">{t.confusion.rowP}</th>
                <td className="num">{c.p_like_p}</td>
                <td className="num">{c.p_like_non}</td>
              </tr>
              <tr>
                <th scope="row">{t.confusion.rowNon}</th>
                <td className="num">{c.non_p}</td>
                <td className="num">{c.non_non}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      {meta.books && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
          <table className="change-table pent-books">
            <caption>{t.booksTitle}</caption>
            <thead>
              <tr>
                <th>{t.bookCols.book}</th>
                <th className="num">{t.bookCols.verses}</th>
                <th className="num">{t.bookCols.agree}</th>
                <th className="num">{t.bookCols.pLike}</th>
                <th className="num">{t.bookCols.pRef}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(meta.books).map(([name, b]) => (
                <tr key={name}>
                  <th scope="row">{t.bookNames[name] ?? name}</th>
                  <td className="num">{b.verses}</td>
                  <td className="num">{pct(b.agree)}</td>
                  <td className="num">{pct(b.p_like)}</td>
                  <td className="num">{pct(b.p_ref)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {meta.grid && meta.grid.length > 1 && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.gridTitle}>
          <table className="change-table pent-grid">
            <caption>
              {t.gridTitle}: {t.gridLede}
            </caption>
            <thead>
              <tr>
                <th className="num">{t.gridCols.chunk}</th>
                <th className="num">{t.gridCols.smooth}</th>
                <th className="num">{t.gridCols.kappa}</th>
                <th className="num">{t.gridCols.genesis}</th>
                <th className="num">{t.gridCols.names}</th>
              </tr>
            </thead>
            <tbody>
              {meta.grid.map((g) => (
                <tr key={`${g.chunk_verses}-${g.smooth}`} className={g.chunk_verses === FIXED.chunk && g.smooth === FIXED.smooth ? 'fixed' : undefined}>
                  <td className="num">{g.chunk_verses}</td>
                  <td className="num">{g.smooth}</td>
                  <td className="num">{g.kappa.toFixed(3)}</td>
                  <td className="num">{g.kappa_genesis.toFixed(3)}</td>
                  <td className="num">{`${g.names.toFixed(3)} (p ${g.names_p.toFixed(2)})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function WordList({ title, words }: { title: string; words: SourceWord[] }) {
  const { m } = useLocale()
  const t = m.pent
  return (
    <div>
      <h3>{title}</h3>
      <ol className="pent-words">
        {words.map((w) => {
          const stem = w.token.split('@')[1]
          return (
            <li key={w.token}>
              <span dir="rtl" lang="he" className="he-cell">
                {w.he ?? w.token}
              </span>
              {stem && <span className="muted small"> ({t.stems[stem] ?? stem})</span>} <span className="muted small">{w.weight.toFixed(2)}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function Words({ data }: { data: PentateuchResponse }) {
  const { m } = useLocale()
  const t = m.pent
  return (
    <section aria-label={t.wordsTitle}>
      <h2>{t.wordsTitle}</h2>
      <WordList title={t.pLikeWords} words={data.p_like} />
      <WordList title={t.nonPWords} words={data.non_p} />
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.synonymsTitle}>
        <table className="change-table pent-synonyms">
          <caption>{t.synonymsTitle}</caption>
          <thead>
            <tr>
              <th>{t.synCols.set}</th>
              <th>{t.synCols.members}</th>
              <th>{t.synCols.pLike}</th>
              <th>{t.synCols.nonP}</th>
            </tr>
          </thead>
          <tbody>
            {data.synonyms.map((s) => {
              const forms = s.members.map((mb, i) => {
                const stem = mb.split('@')[1]
                return `${s.he[i] ?? mb}${stem ? ` (${t.stems[stem] ?? stem})` : ''}`
              })
              return (
                <tr key={s.name}>
                  <td>{t.setNames[s.name] ?? s.name}</td>
                  <td dir="rtl" lang="he" className="he-cell">
                    {forms.join(' / ')}
                  </td>
                  <td>{s.p_like.join(' / ')}</td>
                  <td>{s.non_p.join(' / ')}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Chapters() {
  const { m, locale } = useLocale()
  const t = m.pent
  const [params, update] = useQueryParams()
  const book = Number(params.get('book') ?? '0')
  const page = parsePage(params.get('page'))
  const res = usePentateuchChapters(book, PAGE_SIZE, (page - 1) * PAGE_SIZE)
  return (
    <section aria-label={t.chaptersTitle}>
      <h2>{t.chaptersTitle}</h2>
      <p className="small">{t.chaptersLede}</p>
      <div className="toolbar">
        <label className="control">
          <span>{t.book}</span>
          <select value={book} onChange={(e) => update({ book: e.target.value === '0' ? null : e.target.value, page: null })}>
            {BOOKS.map(([name, id]) => (
              <option key={id} value={id}>
                {t.bookNames[name]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.empty}
        summary={(d, p, pages) => (
          <>
            {t.count(d.total)} · {m.pat.pageOf(p, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'pentateuch', params: { book } }}
              filename={`pentateuch-${book}.csv`}
              rows={() => d.items.map((c) => ({ chapter: c.label, verses: c.verses, p_like: c.p_like, p_ref: c.p_ref ?? '' }))}
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits pent-chapters ${stale}`}>
            {d.items.map((c) => (
              <li key={c.unit_id} className="hit pent-chapter">
                <Link to={readLink(c.unit_id, '?layers=sources')} title={t.read}>
                  {locale === 'he' ? c.label_he : c.label}
                </Link>{' '}
                <span className="src-bar" role="img" aria-label={t.chapterRow(c.p_like, c.p_ref)}>
                  <span className="src-bar-fill" style={{ width: `${c.p_like * 100}%` }} />
                  {c.p_ref != null && <span className="src-bar-ref" style={{ insetInlineStart: `calc(${c.p_ref * 100}% - 1px)` }} />}
                </span>{' '}
                <span className="muted small">{t.chapterRow(c.p_like, c.p_ref)}</span>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}
