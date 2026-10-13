import { Link } from 'react-router'
import { psalmParams, usePsalmList, usePsalms } from '../api/hooks'
import type { Psalm, PsalmsMeta, PsalmsResponse, PsalmVerse } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { readLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const SHOWN = ['first_singular', 'first_plural', 'second', 'imperative_plural', 'distress', 'praise']

/** Psalms (§16.42): the counted form against Gunkel's genres, the checks, the lament's turn. */
export function PsalmsPage() {
  const { m } = useLocale()
  const t = m.psa
  const res = usePsalms()
  return (
    <div className="page psalms-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.meta.genre_test ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Genres meta={res.data.meta} />
          <Checks meta={res.data.meta} />
          <Turns data={res.data} />
          <List meta={res.data.meta} />
        </>
      )}
    </div>
  )
}

const genreName = (t: ReturnType<typeof useLocale>['m']['psa'], g: string | null) => (g ? (t.genres[g] ?? g) : t.unlabelled)

function Genres({ meta }: { meta: PsalmsMeta }) {
  const { m } = useLocale()
  const t = m.psa
  const g = meta.genre_test!
  const r = meta.robustness
  const genres = Object.keys(meta.genres ?? {})
  const clusters = Object.keys(meta.cluster_profiles ?? {}).map(Number)
  const n = new Map((meta.crosstab ?? []).map((c) => [`${c.genre}:${c.cluster}`, c.n]))
  return (
    <section aria-label={t.genreTitle}>
      <h2>{t.genreTitle}</h2>
      <p className="small">{t.genreLede(meta.labelled ?? 0, meta.k ?? 0, meta.title_words ?? 0)}</p>
      <p>{t.genreResult(g.nmi, g.null, g.p)}</p>
      {r && <p className="muted small">{t.robustGenres(r.form_only.nmi, r.form_only.p, r.domains_only.nmi, r.domains_only.p, r.titles_kept.nmi)}</p>}
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.crosstabTitle}>
        <table className="change-table psalm-crosstab">
          <caption>{t.crosstabTitle}</caption>
          <thead>
            <tr>
              <th>{t.genreHead}</th>
              {clusters.map((c) => (
                <th key={c} className="num">
                  {t.cluster(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {genres.map((genre) => (
              <tr key={genre}>
                <th scope="row">{genreName(t, genre)}</th>
                {clusters.map((c) => {
                  const v = n.get(`${genre}:${c}`) ?? 0
                  return (
                    <td key={c} className={`num ${v ? '' : 'muted'}`}>
                      {v}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.profileTitle}>
        <table className="change-table psalm-profiles">
          <caption>
            {t.profileTitle} ({t.per100})
          </caption>
          <thead>
            <tr>
              <th>{t.clusterHead}</th>
              {(meta.features ?? []).map((f) => (
                <th key={f} className="num">
                  {t.features[f] ?? f}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clusters.map((c) => (
              <tr key={c}>
                <th scope="row">{t.cluster(c)}</th>
                {(meta.features ?? []).map((f) => (
                  <td key={f} className="num">
                    {t.per100Value(meta.cluster_profiles?.[String(c)]?.[f])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Checks({ meta }: { meta: PsalmsMeta }) {
  const { m } = useLocale()
  const t = m.psa
  const checks = meta.checks ?? []
  const alpha = meta.alpha ?? 0.05
  if (!checks.length) return null
  return (
    <section aria-label={t.checksTitle}>
      <h2>{t.checksTitle}</h2>
      <p className="small">{t.checksLede(meta.checks_held ?? 0, checks.length)}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.checksTitle}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.checkCols.genre}</th>
              <th>{t.checkCols.feature}</th>
              <th>{t.checkCols.expected}</th>
              <th className="num">{t.checkCols.mean}</th>
              <th className="num">{t.checkCols.rest}</th>
              <th className="num">{t.checkCols.q}</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={`${c.genre}-${c.feature}`}>
                <td>{genreName(t, c.genre)}</td>
                <td>{t.features[c.feature] ?? c.feature}</td>
                <td>{c.direction === 'higher' ? t.higher : t.lower}</td>
                <td className="num">{t.per100Value(c.mean)}</td>
                <td className="num">{t.per100Value(c.rest)}</td>
                <td className={`num ${c.q <= alpha ? 'on' : ''}`}>{c.q < 0.001 ? '< 0.001' : c.q.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Turns({ data }: { data: PsalmsResponse }) {
  const { m, locale } = useLocale()
  const t = m.psa
  const meta = data.meta
  const k = meta.known_turns
  const lvh = meta.laments_vs_hymns
  const tol = meta.robustness?.tolerance
  return (
    <section aria-label={t.turnTitle}>
      <h2>{t.turnTitle}</h2>
      <p className="small">{t.turnLede(meta.min_side ?? 2)}</p>
      {k && <p>{t.knownLede(k.found, k.n, k.expected, k.p, meta.tolerance ?? 1)}</p>}
      {tol && <p className="muted small">{t.robustTolerance(Object.entries(tol).map(([tl, r]) => ({ tol: tl, ...r })))}</p>}
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownCols.named}>
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.knownCols.named}</th>
              <th>{t.knownCols.found}</th>
              <th className="num">{t.knownCols.p}</th>
              <th className="num">{t.knownCols.chance}</th>
            </tr>
          </thead>
          <tbody>
            {data.known.map((r) => (
              <tr key={r.verse_id} className={r.found ? 'found' : undefined}>
                <td>
                  <Link to={readLink(`v:${r.verse_id}`, '?layers=mood')}>{locale === 'he' ? r.label_he : r.label}</Link>
                </td>
                <td>
                  {r.turn_vid == null ? (
                    <span className="muted">{t.tooShort}</span>
                  ) : (
                    <>
                      <Link to={unitLink(`v:${r.turn_vid}`)}>{locale === 'he' ? r.turn_label_he : r.turn_label}</Link>
                      {r.found ? ' ✓' : ''}
                    </>
                  )}
                </td>
                <td className="num">{r.p == null ? '–' : r.p.toFixed(2)}</td>
                <td className="num">{r.chance == null ? '–' : r.chance.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {lvh && <p>{t.lvh(lvh.laments, lvh.n_laments, lvh.hymns, lvh.n_hymns, lvh.p)}</p>}
    </section>
  )
}

function List({ meta }: { meta: PsalmsMeta }) {
  const { m } = useLocale()
  const t = m.psa
  const [params, update] = useQueryParams()
  const genre = params.get('genre') || undefined
  const clusterParam = params.get('cluster')
  const cluster = clusterParam ? Number(clusterParam) : undefined
  const turned = params.get('turned') === '1'
  const sort = params.get('sort') === 'turn' ? 'turn' : 'chapter'
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const query = { genre, cluster, turned, unit, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } as const
  const res = usePsalmList(query)
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const alpha = meta.alpha ?? 0.05
  return (
    <section aria-label={t.listTitle}>
      <h2>{t.listTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{t.genreHead}</span>
          <select value={genre ?? ''} onChange={(e) => set({ genre: e.target.value || null })}>
            <option value="">{t.allGenres}</option>
            {Object.keys(meta.genres ?? {}).map((g) => (
              <option key={g} value={g}>
                {genreName(t, g)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.clusterHead}</span>
          <select value={cluster ?? ''} onChange={(e) => set({ cluster: e.target.value || null })}>
            <option value="">{t.allClusters}</option>
            {Object.keys(meta.cluster_profiles ?? {}).map((c) => (
              <option key={c} value={c}>
                {t.cluster(Number(c))}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.sortLabel}</span>
          <select value={sort} onChange={(e) => set({ sort: e.target.value === 'turn' ? 'turn' : null })}>
            {Object.entries(t.sorts).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={turned} onChange={(e) => set({ turned: e.target.checked ? '1' : null })} />
          {t.turnedOnly}
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
              all={{ list: 'psalms', params: psalmParams(query) }}
              filename={`psalms-p${p}.csv`}
              rows={() =>
                d.items.map((s) => ({
                  psalm: s.label,
                  genre: s.genre ?? '',
                  cluster: s.cluster,
                  ...s.features,
                  turn: s.turn?.label ?? '',
                  turn_p: s.turn?.p ?? '',
                }))
              }
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((s) => (
              <PsalmItem key={s.unit_id} s={s} alpha={alpha} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function PsalmItem({ s, alpha }: { s: Psalm; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.psa
  const label = locale === 'he' ? s.label_he : s.label
  return (
    <li className="hit psalm">
      <div className="hit-head">
        <Link to={unitLink(s.unit_id)}>{label}</Link> <span className={`type-tag ${s.genre ? '' : 'muted'}`}>{genreName(t, s.genre)}</span>{' '}
        <span className="muted small">
          {t.cluster(s.cluster)} · {t.words(s.words)}
        </span>{' '}
        <Link className="small" to={readLink(s.unit_id, '?layers=mood')} title={t.readTitle}>
          {t.read}
        </Link>
      </div>
      <p className="small psalm-features">
        {SHOWN.map((f, i) => (
          <span key={f}>
            {i > 0 && ' · '}
            {t.features[f]} {t.per100Value(s.features[f])}
          </span>
        ))}{' '}
        <span className="muted">({t.per100})</span>
      </p>
      <p className={`small ${s.turn && s.turn.p <= alpha ? '' : 'muted'}`}>
        {s.turn ? t.turnAt(locale === 'he' ? s.turn.label_he : s.turn.label, s.turn.p, s.turn.before, s.turn.after) : t.noTurn}
      </p>
      <MoodStrip label={label} mood={s.mood} turn={s.turn?.verse ?? null} />
    </li>
  )
}

const BAR = 6
const HALF = 18

/** Praise above the line, distress below, per word of each verse; the turn as a rule before its verse. */
function MoodStrip({ label, mood, turn }: { label: string; mood: PsalmVerse[]; turn: number | null }) {
  const { m, locale } = useLocale()
  const t = m.psa
  if (!mood.length) return null
  const width = mood.length * BAR
  const x = (i: number) => (locale === 'he' ? width - (i + 1) * BAR : i * BAR)
  const h = (n: number, words: number) => (words ? Math.min(1, (n / words) * 4) * HALF : 0)
  const turnAt = turn === null ? -1 : mood.findIndex((v) => v.verse === turn)
  return (
    <svg className="mood-strip" width={width} height={HALF * 2 + 2} role="img" aria-label={t.moodLabel(label)}>
      <line className="mood-axis" x1={0} x2={width} y1={HALF + 1} y2={HALF + 1} />
      {mood.map((v, i) => (
        <g key={v.verse}>
          <title>{t.moodTitle(v.verse, v.praise, v.distress)}</title>
          <rect className="mood-praise" x={x(i)} y={HALF + 1 - h(v.praise, v.words)} width={BAR - 1} height={h(v.praise, v.words)} />
          <rect className="mood-distress" x={x(i)} y={HALF + 1} width={BAR - 1} height={h(v.distress, v.words)} />
        </g>
      ))}
      {turnAt > 0 && <line className="mood-turn" x1={locale === 'he' ? x(turnAt) + BAR : x(turnAt)} x2={locale === 'he' ? x(turnAt) + BAR : x(turnAt)} y1={0} y2={HALF * 2 + 2} />}
    </svg>
  )
}
