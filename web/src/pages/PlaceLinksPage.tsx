import { useState } from 'react'
import { Link } from 'react-router'
import { useBasemap, usePlaceLinkPairs, usePlaceLinks } from '../api/hooks'
import type { DecayRow, DecayVariant, LinkPoint, PlaceLinkPair, PlaceLinkSort, PlaceLinksResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { GeoMap } from '../components/GeoMap'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { type Bounds, fitBounds, type GeoPoint, VIEWS } from '../lib/geo'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const SORTS: PlaceLinkSort[] = ['g2', 'km', 'near']
const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

/** Named together, near together? (§16.61): linked pairs of places, link strength against
 * distance with the points shuffled, the decay by distance, the far pairs as leads. */
export function PlaceLinksPage() {
  const { m } = useLocale()
  const t = m.plk
  const res = usePlaceLinks()
  const all = res.data?.variants.find((v) => v.variant === 'all')
  return (
    <div className="page place-links-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !all ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Summary data={res.data} all={all} />
          <Variants data={res.data} />
          <Chart points={res.data.scatter} farKm={res.data.meta.far_km ?? 150} />
          <Bins data={res.data} />
          <Leads data={res.data} />
          <Pairs />
          <p className="muted small">{t.credit}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.plk
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

const holdsOf = (r: DecayRow, alpha: number) => r.test.p != null && r.test.rho != null && r.test.null_mean != null && r.test.p <= alpha && r.test.rho < r.test.null_mean

function Summary({ data, all }: { data: PlaceLinksResponse; all: DecayRow }) {
  const t = useLocale().m.plk
  const x = all.test
  if (x.p == null || x.rho == null) return null
  return (
    <>
      <p>
        <Verdict holds={holdsOf(all, data.meta.alpha ?? 0.05)} />{' '}
        {t.summary(x.pairs, x.places ?? 0, data.meta.min_together ?? 2, x.rho, x.null_mean ?? 0, x.null_q05 ?? 0, x.null_q95 ?? 0, x.p, data.meta.shuffles ?? 0)}
      </p>
      <p className="muted small">{t.caveat}</p>
    </>
  )
}

function Variants({ data }: { data: PlaceLinksResponse }) {
  const { m, locale } = useLocale()
  const t = m.plk
  const alpha = data.meta.alpha ?? 0.05
  const hint = (v: DecayVariant) =>
    v === 'all' ? t.variantHints.all : v === 'sure' ? t.variantHints.sure(data.meta.sure_score ?? 500) : t.variantHints.no_lists((locale === 'he' ? data.lists_he : data.lists_en).join(', '))
  return (
    <section aria-label={t.variantsTitle}>
      <h2>{t.variantsTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.variantsTitle}>
        <table className="change-table plk-table">
          <thead>
            <tr>
              <th>{t.vcols.variant}</th>
              <th>{t.vcols.places}</th>
              <th>{t.vcols.pairs}</th>
              <th>{t.vcols.rho}</th>
              <th>{t.vcols.shuffled}</th>
              <th>{t.vcols.p}</th>
            </tr>
          </thead>
          <tbody>
            {data.variants.map((r) => (
              <tr key={r.variant}>
                <td>
                  {t.variants[r.variant]}
                  <div className="muted small">{hint(r.variant)}</div>
                </td>
                {r.test.p == null || r.test.rho == null ? (
                  <td colSpan={5} className="muted">
                    {t.untested(r.test.pairs)}
                  </td>
                ) : (
                  <>
                    <td>{r.test.places}</td>
                    <td>{r.test.pairs}</td>
                    <td>{t.rho(r.test.rho)}</td>
                    <td>{t.range(r.test.null_mean ?? 0, r.test.null_q05 ?? 0, r.test.null_q95 ?? 0)}</td>
                    <td>
                      <Verdict holds={holdsOf(r, alpha)} /> {fp(r.test.p)}
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

const W = 560
const H = 300
const PAD = { l: 44, r: 26, t: 12, b: 36 }

/** Every linked pair: km across and G² up, both on log scales; the far pairs marked. */
function Chart({ points, farKm }: { points: LinkPoint[]; farKm: number }) {
  const t = useLocale().m.plk
  if (!points.length) return null
  const lx = (km: number) => Math.log10(Math.max(1, km))
  const ly = (g2: number) => Math.log10(Math.max(1, g2))
  const xMax = Math.ceil(Math.max(...points.map((p) => lx(p.km)), 3))
  const yMax = Math.ceil(Math.max(...points.map((p) => ly(p.g2)), 2))
  const x = (km: number) => PAD.l + (lx(km) / xMax) * (W - PAD.l - PAD.r)
  const y = (g2: number) => H - PAD.b - (ly(g2) / yMax) * (H - PAD.t - PAD.b)
  const xTicks = Array.from({ length: xMax + 1 }, (_, i) => 10 ** i)
  const yTicks = Array.from({ length: yMax + 1 }, (_, i) => 10 ** i)
  return (
    <section aria-label={t.chartTitle}>
      <h2>{t.chartTitle}</h2>
      <figure className="plk-chart" dir="ltr">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.chartLabel(points.length)}>
          {xTicks.map((v) => (
            <g key={`x${v}`} className="plk-tick">
              <line x1={x(v)} x2={x(v)} y1={PAD.t} y2={H - PAD.b} />
              <text x={x(v)} y={H - PAD.b + 14} textAnchor="middle">
                {v.toLocaleString('en-US')}
              </text>
            </g>
          ))}
          {yTicks.map((v) => (
            <g key={`y${v}`} className="plk-tick">
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} />
              <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end">
                {v.toLocaleString('en-US')}
              </text>
            </g>
          ))}
          <line className="plk-far-line" x1={x(farKm)} x2={x(farKm)} y1={PAD.t} y2={H - PAD.b} />
          {points.map((p, i) => (
            <circle key={i} className={p.far ? 'plk-dot far' : 'plk-dot'} cx={x(p.km)} cy={y(p.g2)} r={2.6} />
          ))}
          <text className="plk-axis" x={(PAD.l + W - PAD.r) / 2} y={H - 4} textAnchor="middle">
            {t.axisKm}
          </text>
          <text className="plk-axis" transform={`translate(12 ${(PAD.t + H - PAD.b) / 2}) rotate(-90)`} textAnchor="middle">
            {t.axisG2}
          </text>
        </svg>
        <figcaption className="small muted" dir="auto">
          <span className="plk-key far" aria-hidden="true" /> {t.far(farKm)} <span className="plk-key" aria-hidden="true" /> {t.near}
        </figcaption>
      </figure>
    </section>
  )
}

function Bins({ data }: { data: PlaceLinksResponse }) {
  const t = useLocale().m.plk
  const [params, update] = useQueryParams()
  const variants = data.variants.filter((v) => v.bins.length > 0)
  const asked = params.get('bins')
  const row = variants.find((v) => v.variant === asked) ?? variants[0]
  if (!row) return null
  const max = Math.max(...row.bins.map((b) => b.share ?? 0), 1e-9)
  return (
    <section aria-label={t.binsTitle}>
      <h2>{t.binsTitle}</h2>
      <p className="muted small">{t.binsLede(data.meta.min_together ?? 2)}</p>
      {variants.length > 1 && (
        <Segmented
          label={t.variant}
          value={row.variant}
          onChange={(x) => update({ bins: x === variants[0].variant ? null : x }, false)}
          options={variants.map((v) => ({ value: v.variant, label: t.variants[v.variant] }))}
        />
      )}
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.binsTitle}>
        <table className="change-table plk-table plk-bins">
          <thead>
            <tr>
              <th>{t.bcols.km}</th>
              <th>{t.bcols.pairs}</th>
              <th>{t.bcols.linked}</th>
              <th>{t.bcols.share}</th>
              <th>{t.bcols.g2}</th>
            </tr>
          </thead>
          <tbody>
            {row.bins.map((b) => (
              <tr key={b.bin}>
                <td>{t.bin(b.lo_km, b.hi_km)}</td>
                <td>{b.pairs.toLocaleString('en-US')}</td>
                <td>{b.linked}</td>
                <td>
                  <span className="plk-bar" style={{ inlineSize: `${((b.share ?? 0) / max) * 6}rem` }} aria-hidden="true" /> {b.share == null ? '–' : t.share(b.share)}
                </td>
                <td>{b.median_g2 == null ? '–' : t.g2(b.median_g2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function PlaceName({ id, he }: { id: number; he: string }) {
  const t = useLocale().m.plk
  return (
    <Link to={`/place-links?place=${id}#pairs`} dir="rtl" lang="he" className="he" title={t.pairsOf(he)}>
      {he}
    </Link>
  )
}

function Leads({ data }: { data: PlaceLinksResponse }) {
  const { m, locale } = useLocale()
  const t = m.plk
  const basemap = useBasemap()
  const [moved, setMoved] = useState<Bounds>()
  const farKm = data.meta.far_km ?? 150
  const seen = new Map<number, GeoPoint>()
  for (const l of data.leads) for (const s of [l.a, l.b]) seen.set(s.place_id, { place_id: s.place_id, he: s.he, kind: s.kind, lat: s.lat, lon: s.lon, n: 1 })
  const points = [...seen.values()]
  const bounds = moved ?? fitBounds(points, 4) ?? VIEWS.east
  return (
    <section className="plk-leads" id="leads" aria-label={t.leadsTitle}>
      <h2>{t.leadsTitle}</h2>
      <p className="muted small">{t.leadsLede(farKm, data.meta.far_pairs ?? 0)}</p>
      {data.known.map((k) => (
        <p key={`${k.a}-${k.b}`}>
          <Verdict holds={k.holds} />{' '}
          <span dir="rtl" lang="he" className="he">
            {k.a}
          </span>{' '}
          {t.and}
          {locale === 'he' ? '' : ' '}
          <span dir="rtl" lang="he" className="he">
            {k.b}
          </span>
          {k.found ? t.known(k.rank ?? null, data.meta.far_pairs ?? 0, data.meta.top ?? 10, k.pair?.km ?? null) : t.knownMissing}
        </p>
      ))}
      <div className="places-layout plk-leads-layout">
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.leadsTitle}>
          <table className="change-table plk-table">
            <thead>
              <tr>
                <th>{t.lcols.rank}</th>
                <th>{t.lcols.pair}</th>
                <th>{t.lcols.together}</th>
                <th>{t.lcols.g2}</th>
                <th>{t.lcols.km}</th>
              </tr>
            </thead>
            <tbody>
              {data.leads.map((l) => (
                <tr key={`${l.a.place_id}-${l.b.place_id}`}>
                  <td>{l.lead_rank}</td>
                  <td>
                    <PlaceName id={l.a.place_id} he={l.a.he} /> – <PlaceName id={l.b.place_id} he={l.b.he} />
                  </td>
                  <td>{l.n_together}</td>
                  <td>{t.g2(l.g2)}</td>
                  <td>{t.km(l.km)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="places-map">
          <GeoMap
            basemap={basemap.data}
            points={points}
            bounds={bounds}
            onBounds={setMoved}
            onSelect={() => undefined}
            label={t.leadsMap}
            labels={12}
            paths={data.leads.map((l) => ({ key: `${l.a.place_id}-${l.b.place_id}`, className: 'plk-link', coords: [[l.a.lon, l.a.lat] as [number, number], [l.b.lon, l.b.lat] as [number, number]] }))}
          />
        </div>
      </div>
    </section>
  )
}

function Pairs() {
  const t = useLocale().m.plk
  const [params, update] = useQueryParams()
  const s = params.get('sort')
  const sort: PlaceLinkSort = SORTS.includes(s as PlaceLinkSort) ? (s as PlaceLinkSort) : 'g2'
  const p = params.get('place')
  const place = p !== null && /^\d+$/.test(p) ? Number(p) : undefined
  const page = parsePage(params.get('page'))
  const res = usePlaceLinkPairs({ place, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const first = res.data?.items[0]
  const he = place == null || !first ? undefined : first.a.place_id === place ? first.a.he : first.b.he
  return (
    <section aria-label={t.pairsTitle} id="pairs">
      <h2>{t.pairsTitle}</h2>
      <div className="toolbar">
        <Segmented label={t.sort} value={sort} onChange={(x) => set({ sort: x === 'g2' ? null : x })} options={SORTS.map((x) => ({ value: x, label: t.sorts[x] }))} />
        {place != null && (
          <span>
            {he && (
              <span className="plk-filter" dir="auto">
                {t.placeFilter(he)}
              </span>
            )}{' '}
            <button type="button" className="linkish" onClick={() => set({ place: null })}>
              {t.allPlaces}
            </button>
          </span>
        )}
      </div>
      <PagedList res={res} empty={t.emptyPairs} summary={(d, pg, pages) => `${t.pairsSummary(d.total)} · ${t.pageOf(pg, pages)}`}>
        {(d, stale) => (
          <ol className={`plk-pairs ${stale}`}>
            {d.items.map((x) => (
              <PairItem key={`${x.a.place_id}-${x.b.place_id}`} pair={x} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function PairItem({ pair: x }: { pair: PlaceLinkPair }) {
  const t = useLocale().m.plk
  return (
    <li>
      <PlaceName id={x.a.place_id} he={x.a.he} /> – <PlaceName id={x.b.place_id} he={x.b.he} /> <span className="muted small">{t.pairLine(x.n_together, x.g2, x.km)}</span>{' '}
      <Link className="small" to={`/places?p=${x.a.place_id}`} aria-label={t.onMap(x.a.he)}>
        ↗
      </Link>
    </li>
  )
}
