import { Link } from 'react-router'
import { useGematriaLinks, useGematriaPairs } from '../api/hooks'
import type { GematriaLinksResponse, GematriaPairSort, LinkLemma, LinkMeasure, LinkTest, VerseLabel } from '../api/types'
import { Segmented } from '../components/Controls'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { lemmaLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const MEASURES: LinkMeasure[] = ['domains', 'root', 'vector']
const SORTS: GematriaPairSort[] = ['vector', 'domains', 'value']
const PAGE_SIZE = 25

/** Equal values, related words? (§16.59): equal-value pairs against matched pairs on three measures,
 * the check of the measures, the tradition's equivalences, Gen 1:1's numbers and the pairs. */
export function GematriaLinksPage() {
  const { m } = useLocale()
  const t = m.gl
  const res = useGematriaLinks()
  return (
    <div className="page gematria-links-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.equal.vector ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Tests data={res.data} />
          <Equivalences data={res.data} />
          <Genesis data={res.data} />
          <Pairs />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.gl
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

const num = (x: number, measure: LinkMeasure) => (measure === 'root' ? `${(100 * x).toFixed(2)}%` : x.toFixed(3))

function TestTable({ tests, label }: { tests: Partial<Record<LinkMeasure, LinkTest>>; label: string }) {
  const t = useLocale().m.gl
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label={label}>
      <table className="change-table gl-tests">
        <thead>
          <tr>
            <th>{t.cols.measure}</th>
            <th>{t.cols.pairs}</th>
            <th>{t.cols.matched}</th>
            <th>{t.cols.range}</th>
            <th>{t.cols.p}</th>
          </tr>
        </thead>
        <tbody>
          {MEASURES.filter((x) => tests[x]).map((x) => {
            const r = tests[x]!
            return (
              <tr key={x}>
                <td title={t.measureHints[x]}>{t.measures[x]}</td>
                <td>{num(r.observed, x)}</td>
                <td>{num(r.null_mean, x)}</td>
                <td>
                  {num(r.null_q05, x)} – {num(r.null_q95, x)}
                </td>
                <td>{r.p < 0.001 ? '< 0.001' : r.p.toFixed(3)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function Tests({ data }: { data: GematriaLinksResponse }) {
  const t = useLocale().m.gl
  const meta = data.meta
  const alpha = meta.alpha ?? 0.05
  const eq = Object.values(data.equal)
  const linked = eq.some((r) => r.observed > r.null_mean && r.p <= alpha / eq.length)
  const rf = Object.values(data.root_family)
  const seen = rf.length > 0 && rf.every((r) => r.observed > r.null_mean && r.p <= alpha)
  return (
    <>
      <p>{t.summary(meta.lemmas ?? 0, meta.pairs ?? 0, meta.same_letters ?? 0, meta.draws ?? 0)}</p>
      <section aria-label={t.testTitle}>
        <h2>{t.testTitle}</h2>
        <p>
          <Verdict holds={linked} /> <span className="muted small">{t.testVerdict(alpha)}</span>
        </p>
        <TestTable tests={data.equal} label={t.testTitle} />
      </section>
      {rf.length > 0 && (
        <section aria-label={t.checkTitle}>
          <h2>{t.checkTitle}</h2>
          <p>
            <Verdict holds={seen} /> <span className="muted small">{t.checkLede}</span>
          </p>
          <TestTable tests={data.root_family} label={t.checkTitle} />
        </section>
      )}
    </>
  )
}

function Word({ w }: { w: LinkLemma }) {
  return (
    <Link to={lemmaLink(w.lemma)} dir="rtl" lang="he" className="he">
      {w.he}
    </Link>
  )
}

function Equivalences({ data }: { data: GematriaLinksResponse }) {
  const t = useLocale().m.gl
  if (!data.equivalences.length) return null
  return (
    <section aria-label={t.eqTitle}>
      <h2>{t.eqTitle}</h2>
      <p className="muted small">{t.eqLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.eqTitle}>
        <table className="change-table gl-eq">
          <thead>
            <tr>
              <th>{t.eqCols.pair}</th>
              <th>{t.eqCols.value}</th>
              <th>{t.eqCols.domains}</th>
              <th>{t.eqCols.root}</th>
              <th>{t.eqCols.vector}</th>
            </tr>
          </thead>
          <tbody>
            {data.equivalences.map((e) => (
              <tr key={`${e.a_text}=${e.b_text}`}>
                <td dir="rtl" lang="he" className="he-cell">
                  {e.a && e.b ? (
                    <>
                      <Word w={e.a} /> = <Word w={e.b} />
                    </>
                  ) : (
                    `${e.a_text} = ${e.b_text}`
                  )}
                </td>
                {!e.found ? (
                  <td colSpan={4} className="muted">
                    {t.notFound}
                  </td>
                ) : (
                  <>
                    <td>
                      <Link to={`/gematria?q=${e.value}`}>{e.value}</Link>
                    </td>
                    <td>{e.domains == null ? '–' : `${Math.round(100 * e.domains)}%`}</td>
                    <td>{e.root ? t.same : t.differ}</td>
                    <td>
                      {e.vector?.toFixed(2)} <span className="muted small">({t.rank(e.vector_rank ?? 0)})</span>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Genesis({ data }: { data: GematriaLinksResponse }) {
  const { m, locale } = useLocale()
  const t = m.gl
  const v = data.verse
  if (!v) return null
  const label = (x: VerseLabel) => (locale === 'he' ? x.label_he : x.label_en)
  const ref = label(v.verse)
  return (
    <section aria-label={t.verseTitle(ref)} id="genesis">
      <h2>{t.verseTitle(ref)}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.verseTitle(ref)}>
        <table className="change-table gl-props">
          <thead>
            <tr>
              <th>{t.propCols.prop}</th>
              <th>{t.propCols.here}</th>
              <th>{t.propCols.verses}</th>
            </tr>
          </thead>
          <tbody>
            {v.properties.map((p) => (
              <tr key={p.key}>
                <td>{t.props(p)}</td>
                <td>{p.holds_here ? '✓' : '–'}</td>
                <td>{p.verses.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        <Verdict holds={v.unique_here && v.unique_share <= (data.meta.alpha ?? 0.05)} /> {t.allLine(ref, v.all, v.expected_all)}
      </p>
      <p>{t.ownLine(ref, v.words, v.letters, v.largest_prime, v.twins.length, v.unique_share)}</p>
      {v.twins.length > 0 && (
        <p className="small">
          {t.twins}:{' '}
          {v.twins.map((x, i) => (
            <span key={x.verse_id}>
              {i > 0 && ', '}
              <Link to={unitLink(`v:${x.verse_id}`)}>{label(x)}</Link>
            </span>
          ))}
        </p>
      )}
    </section>
  )
}

function Pairs() {
  const t = useLocale().m.gl
  const [params, update] = useQueryParams()
  const s = params.get('sort')
  const sort: GematriaPairSort = SORTS.includes(s as GematriaPairSort) ? (s as GematriaPairSort) : 'vector'
  const sameLetters = params.get('same') === '1'
  const v = params.get('value')
  const value = v !== null && /^\d+$/.test(v) ? Number(v) : undefined
  const page = parsePage(params.get('page'))
  const res = useGematriaPairs({ value, sort, sameLetters, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.pairsTitle} id="pairs">
      <h2>{t.pairsTitle}</h2>
      <div className="toolbar">
        <Segmented label={t.sort} value={sort} onChange={(x) => set({ sort: x === 'vector' ? null : x })} options={SORTS.map((x) => ({ value: x, label: t.sorts[x] }))} />
        <label className="control">
          <span>{t.valueFilter}</span>
          <input type="number" min={0} inputMode="numeric" value={value ?? ''} placeholder={t.allValues} onChange={(e) => set({ value: e.target.value || null })} />
        </label>
        <label className="check">
          <input type="checkbox" checked={sameLetters} onChange={(e) => set({ same: e.target.checked ? '1' : null })} /> {t.sameLetters}
        </label>
      </div>
      <PagedList res={res} empty={t.emptyPairs} summary={(d, pg, pages) => `${t.pairsSummary(d.total)} · ${t.pageOf(pg, pages)}`}>
        {(d, stale) => (
          <ol className={`gl-pairs ${stale}`}>
            {d.items.map((p) => (
              <li key={`${p.a.lemma}=${p.b.lemma}`}>
                <span dir="rtl" lang="he" className="he-label">
                  <Word w={p.a} /> = <Word w={p.b} />
                </span>{' '}
                <Link to={`/gematria?q=${p.value}`} title={t.valueTitle(p.value)}>
                  {p.value}
                </Link>{' '}
                <span className="muted small">{t.pairLine(p.vector, p.domains)}</span> {p.root && <span className="type-tag">{t.oneRoot}</span>}{' '}
                {p.same_letters && <span className="type-tag">{t.spelledAlike}</span>}
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}
