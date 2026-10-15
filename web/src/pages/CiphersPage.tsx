import { Link } from 'react-router'
import { useBooks, useCipherHits, useCiphers } from '../api/hooks'
import type { CipherHit, CipherName, CiphersResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const CHAPTERS_SHOWN = 15
const CIPHERS: CipherName[] = ['atbash', 'albam']

/** Atbash and albam (§16.54): the checks against random letter swaps, the places named in advance,
 * the names read through each swap and the chapters where they gather. */
export function CiphersPage() {
  const { m } = useLocale()
  const t = m.cph
  const res = useCiphers()
  return (
    <div className="page ciphers-page">
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
          <Checks data={res.data} />
          <Hits />
          <Chapters data={res.data} />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.cph
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function Checks({ data }: { data: CiphersResponse }) {
  const { m, locale } = useLocale()
  const t = m.cph
  const meta = data.meta
  const alpha = meta.alpha ?? 0.05
  const tests = meta.tests ?? {}
  const more = (x: { observed: number; expected: number; p: number }) => x.observed > x.expected && x.p <= alpha
  const found = meta.known_found ?? 0
  const where = [...new Set(data.known.map((k) => (locale === 'he' ? k.verse.label_he : k.verse.label_en).replace(/:.*$/, '')))].join(locale === 'he' ? ' ו' : ' and ')
  return (
    <>
      <p>{t.summary(meta.names ?? 0, meta.spans ?? 0, meta.single_spans ?? 0, meta.shuffles ?? 0)}</p>
      <section aria-label={t.checksTitle}>
        <h2>{t.checksTitle}</h2>
        <ol className="dlg-checks">
          {data.known.length > 0 && (
            <li>
              <Verdict holds={found === data.known.length} /> {t.known(found, data.known.length)}
            </li>
          )}
          {tests.jeremiah && (
            <li>
              <Verdict holds={more(tests.jeremiah)} /> {t.jeremiah(tests.jeremiah.observed, tests.jeremiah.expected, tests.jeremiah.p, where)}
            </li>
          )}
          {tests.elsewhere && (
            <li>
              <Verdict holds={more(tests.elsewhere)} /> {t.elsewhere(tests.elsewhere.observed, tests.elsewhere.expected, tests.elsewhere.p)}
            </li>
          )}
          {tests.albam && (
            <li>
              <Verdict holds={more(tests.albam)} /> {t.albam(tests.albam.observed, tests.albam.expected, tests.albam.p)}
            </li>
          )}
        </ol>
      </section>
      <section aria-label={t.knownTitle}>
        <h2>{t.knownTitle}</h2>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.knownCols.where}</th>
                <th>{t.knownCols.cipher}</th>
                <th>{t.knownCols.text}</th>
                <th>{t.knownCols.name}</th>
                <th>{t.knownCols.found}</th>
              </tr>
            </thead>
            <tbody>
              {data.known.map((k) => (
                <tr key={`${k.verse.verse_id}:${k.text}`}>
                  <td>
                    <Link to={unitLink(`v:${k.verse.verse_id}`)}>{locale === 'he' ? k.verse.label_he : k.verse.label_en}</Link>
                  </td>
                  <td>{t.ciphers[k.cipher]}</td>
                  <td dir="rtl" lang="he" className="he-cell">
                    {k.text}
                  </td>
                  <td dir="rtl" lang="he" className="he-cell">
                    {k.name}
                  </td>
                  <td className={k.found ? undefined : 'muted'}>{k.found ? t.found : t.missing}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function Hits() {
  const { m, locale } = useLocale()
  const t = m.cph
  const [params, update] = useQueryParams()
  const c = params.get('cipher')
  const cipher = c === 'atbash' || c === 'albam' ? c : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const known = params.get('known') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useCipherHits({ cipher, book, unit, known, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <section aria-label={t.hitsTitle}>
      <h2>{t.hitsTitle}</h2>
      <p className="muted small">{t.hitsLede}</p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented
          label={t.cipher}
          value={cipher ?? 'both'}
          onChange={(v) => set({ cipher: v === 'both' ? null : v })}
          options={[{ value: 'both', label: t.both }, ...CIPHERS.map((x) => ({ value: x, label: t.ciphers[x] }))]}
        />
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
        <label className="check">
          <input type="checkbox" checked={known} onChange={(e) => set({ known: e.target.checked ? '1' : null })} />
          {t.knownOnly}
        </label>
      </div>
      <PagedList res={res} empty={t.emptyHits} summary={(d, p, pages) => `${t.hitCount(d.total)} · ${t.pageOf(p, pages)}`}>
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((h) => (
              <HitItem key={h.hit_id} h={h} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function HitItem({ h }: { h: CipherHit }) {
  const t = useLocale().m.cph
  const hl: Highlight = new Map()
  for (let i = h.first_tok; i <= h.last_tok; i++) hl.set(i, 'shared')
  return (
    <li className="hit cipher-hit">
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${h.verse.verse_id}`)}>
          <UnitName en={h.verse.ref} he={h.verse.ref_he} />
        </Link>{' '}
        <span className="type-tag">{t.ciphers[h.cipher]}</span>{' '}
        <span dir="rtl" lang="he" className="he">
          {h.span}
        </span>{' '}
        <span className="muted small">{t.reads}</span>{' '}
        <b dir="rtl" lang="he" className="he">
          {h.reads}
        </b>
        {h.known && <span className="muted small"> · {t.named}</span>}
      </div>
      <p className="hit-text">
        <HebrewText verse={h.verse} highlight={hl} />
      </p>
    </li>
  )
}

function Chapters({ data }: { data: CiphersResponse }) {
  const { m } = useLocale()
  const t = m.cph
  const rows = [...data.chapters].sort((a, b) => a.p - b.p || a.unit_id.localeCompare(b.unit_id)).slice(0, CHAPTERS_SHOWN)
  if (rows.length === 0) return null
  return (
    <section aria-label={t.chaptersTitle}>
      <h2>{t.chaptersTitle}</h2>
      <p className="muted small">{t.chaptersLede(data.meta.n_chapters ?? 0)}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.chaptersTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.chaptersCols.chapter}</th>
              <th>{t.chaptersCols.cipher}</th>
              <th>{t.chaptersCols.hits}</th>
              <th>{t.chaptersCols.expected}</th>
              <th>{t.chaptersCols.p}</th>
              <th>{t.chaptersCols.q}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.cipher}:${r.unit_id}`}>
                <td>
                  <Link to={`/ciphers?unit=${encodeURIComponent(r.unit_id)}&cipher=${r.cipher}`}>
                    <UnitName en={r.label_en} he={r.label_he} />
                  </Link>
                </td>
                <td>{t.ciphers[r.cipher]}</td>
                <td>{m.num(r.hits)}</td>
                <td>{r.expected.toFixed(2)}</td>
                <td>{r.p.toFixed(3)}</td>
                <td>{r.q.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
