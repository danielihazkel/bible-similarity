import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useBasemap, usePlaceDistricts, usePlaceList, usePlaceLists } from '../api/hooks'
import type { DistrictGrouping, NullHistogram, PlaceList, PlaceListsResponse, PlaceListStep } from '../api/types'
import { Segmented } from '../components/Controls'
import { GeoMap } from '../components/GeoMap'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { type Bounds, fitBounds, type GeoPoint, VIEWS } from '../lib/geo'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

const NAMED_UP_TO = 20 // a list this long has its places' names written on the map; a longer one, their numbers
const LONGEST = 3 // steps named as the longest

/** Place lists on the ground (§16.58): each list's path in the text's order against random orders
 * of its places, one list on the map, and Joshua's town lists by district. */
export function PlaceListsPage() {
  const { m } = useLocale()
  const t = m.pls
  const res = usePlaceLists()
  return (
    <div className="page place-lists-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.lists.length ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Lists data={res.data} />
          {res.data.groupings.length > 0 && <Districts groupings={res.data.groupings} alpha={res.data.meta.alpha ?? 0.05} />}
          <p className="muted small">{t.credit}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.pls
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function Lists({ data }: { data: PlaceListsResponse }) {
  const { m, locale } = useLocale()
  const t = m.pls
  const [params, update] = useQueryParams()
  const meta = data.meta
  const alpha = meta.alpha ?? 0.05
  const order = meta.order ?? {}
  const key = data.lists.some((l) => l.key === params.get('list')) ? params.get('list')! : data.lists[0].key
  const label = (l: PlaceList) => (locale === 'he' ? l.label_he : l.label_en)
  const selected = data.lists.find((l) => l.key === key)!
  return (
    <>
      <p>
        {t.summary(order.all?.held ?? 0, order.all?.n ?? 0, order.sure?.held ?? 0, order.sure?.n ?? 0, meta.shuffles ?? 0, meta.sure_score ?? 0)}
      </p>
      <p className="muted small">{t.caveat}</p>
      <section aria-label={t.listsTitle}>
        <h2>{t.listsTitle}</h2>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.listsTitle}>
          <table className="change-table pls-table">
            <thead>
              <tr>
                <th>{t.cols.list}</th>
                <th>{t.cols.kind}</th>
                <th title={t.colHints.places}>{t.cols.places}</th>
                <th>{t.cols.path}</th>
                <th>{t.cols.random}</th>
                <th>{t.cols.short}</th>
                <th title={t.colHints.order}>{t.cols.order}</th>
                <th>{t.cols.p}</th>
                <th>{t.cols.sure}</th>
              </tr>
            </thead>
            <tbody>
              {data.lists.map((l) => {
                const a = l.all
                const s = l.sure
                return (
                  <tr key={l.key} className={l.key === key ? 'on' : undefined} aria-current={l.key === key ? 'true' : undefined}>
                    <td>
                      <button type="button" className="linkish" onClick={() => update({ list: l.key, show: null }, false)} aria-label={t.open(label(l))}>
                        {label(l)}
                      </button>
                    </td>
                    <td>{t.kinds[l.kind]}</td>
                    <td>{t.placesOf(a.n, l.n_named)}</td>
                    {a.p == null ? (
                      <td colSpan={6} className="muted">
                        {t.untested(a.n)}
                      </td>
                    ) : (
                      <>
                        <td>{t.km(a.path_km ?? 0)}</td>
                        <td>{t.km(a.null_mean ?? 0)}</td>
                        <td>{t.km(a.short_km ?? 0)}</td>
                        <td>{a.order_score == null ? '–' : t.order(a.order_score)}</td>
                        <td>
                          <Verdict holds={a.p <= alpha} /> {t.p(a.p)}
                        </td>
                      </>
                    )}
                    <td className={s.p == null ? 'muted' : undefined}>
                      {s.p == null ? t.untested(s.n) : `${t.placesOf(s.n, l.n_named)} · p ${t.p(s.p)}`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
      <ListDetail list={selected} />
    </>
  )
}

function ListDetail({ list }: { list: PlaceList }) {
  const { m, locale } = useLocale()
  const t = m.pls
  const [params, update] = useQueryParams()
  const show = params.get('show') === 'short' ? 'short' : 'text'
  const res = usePlaceList(list.key)
  const basemap = useBasemap()
  const [picked, setPicked] = useState<number>()
  const [moved, setMoved] = useState<{ key: string; bounds: Bounds }>()
  const steps = useMemo(() => (res.data?.list.key === list.key ? res.data.steps : []), [res.data, list.key])
  const points: GeoPoint[] = useMemo(
    () => steps.flatMap((s) => (s.place.lat != null && s.place.lon != null ? [{ place_id: s.place.place_id, he: s.place.he, kind: s.place.kind, lat: s.place.lat, lon: s.place.lon, n: 1 }] : [])),
    [steps],
  )
  const pos = useMemo(() => new Map(steps.map((s) => [s.place.place_id, s.pos])), [steps])
  const label = locale === 'he' ? list.label_he : list.label_en
  const a = list.all
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const ordered = show === 'short' ? [...steps].sort((x, y) => x.short_pos - y.short_pos) : steps
  const coords = ordered.flatMap((s) => (s.place.lat != null && s.place.lon != null ? [[s.place.lon, s.place.lat] as [number, number]] : []))
  const bounds = moved?.key === list.key ? moved.bounds : (fitBounds(points) ?? VIEWS.land)
  const longest = new Set(
    [...steps]
      .filter((s) => s.km != null)
      .sort((x, y) => (y.km ?? 0) - (x.km ?? 0))
      .slice(0, LONGEST)
      .map((s) => s.pos),
  )
  return (
    <section className="pls-detail" aria-label={t.pathTitle(label)}>
      <h2>{t.pathTitle(label)}</h2>
      {a.p != null && <p>{t.pathNote(a.n, a.path_km ?? 0, a.null_mean ?? 0, a.short_km ?? 0, a.p)}</p>}
      <div className="places-layout">
        <div className="places-map">
          <Segmented label={t.show} value={show} onChange={(x) => update({ show: x === 'text' ? null : x }, false)} options={(['text', 'short'] as const).map((x) => ({ value: x, label: t.shows[x] }))} />
          <GeoMap
            basemap={basemap.data}
            points={points}
            bounds={bounds}
            onBounds={(b) => setMoved({ key: list.key, bounds: b })}
            selected={picked}
            onSelect={setPicked}
            label={t.mapLabel(label)}
            labels={points.length}
            paths={[{ key: show, className: `pls-path ${show}`, coords }]}
            labelOf={(p) => (points.length <= NAMED_UP_TO ? `${pos.get(p.place_id)} ${p.he}` : String(pos.get(p.place_id)))}
          />
          {a.hist && a.path_km != null && <NullHist hist={a.hist} path={a.path_km} short={a.short_km} mean={a.null_mean ?? 0} />}
        </div>
        <aside className="places-side">
          <h3>{t.stepsTitle}</h3>
          <p className="muted small">{t.stepsLede}</p>
          <ol className="pls-steps">
            {steps.map((s) => (
              <Step key={s.pos} step={s} long={longest.has(s.pos)} on={s.place.place_id === picked} onPick={() => setPicked(s.place.place_id)} />
            ))}
          </ol>
        </aside>
      </div>
    </section>
  )
}

function Step({ step: s, long, on, onPick }: { step: PlaceListStep; long: boolean; on: boolean; onPick: () => void }) {
  const { m, locale } = useLocale()
  const t = m.pls
  return (
    <li value={s.pos} className={[long ? 'long' : '', on ? 'on' : ''].join(' ').trim() || undefined}>
      <button type="button" className="linkish" onClick={onPick}>
        <span dir="rtl" lang="he" className="he">
          {s.place.he}
        </span>
      </button>{' '}
      {s.km != null && <span className={long ? 'pls-km long' : 'pls-km muted small'}>{t.km(s.km)}</span>}{' '}
      {s.sure && (
        <span className="type-tag" title={t.sureTitle(s.place.score ?? 0)}>
          {t.sure}
        </span>
      )}{' '}
      <Link className="small" to={unitLink(`v:${s.verse.verse_id}`)}>
        {locale === 'he' ? s.verse.label_he : s.verse.label_en}
      </Link>{' '}
      <Link className="small" to={`/places?p=${s.place.place_id}`} aria-label={t.onMap(s.place.he)}>
        ↗
      </Link>
    </li>
  )
}

const W = 320
const H = 110
const PAD = 14

/** The random orders' path lengths binned, with the text's path (and a short path, when in range)
 * marked. */
function NullHist({ hist, path, short, mean }: { hist: NullHistogram; path: number; short: number | null; mean: number }) {
  const t = useLocale().m.pls
  const max = Math.max(1, ...hist.counts)
  const span = hist.hi - hist.lo || 1
  const x = (km: number) => PAD + ((km - hist.lo) / span) * (W - 2 * PAD)
  const bw = (W - 2 * PAD) / hist.counts.length
  return (
    <figure className="pls-hist" dir="ltr">
      <figcaption className="small" dir="auto">
        {t.histTitle}
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.histLabel(path, mean)}>
        {hist.counts.map((c, i) => (
          <rect key={i} className="pls-bar" x={PAD + i * bw} y={H - 20 - (c / max) * (H - 40)} width={Math.max(0.5, bw - 1)} height={(c / max) * (H - 40)} />
        ))}
        <line className="pls-axis" x1={PAD} x2={W - PAD} y1={H - 20} y2={H - 20} />
        <text className="pls-tick" x={PAD} y={H - 6}>
          {t.km(hist.lo)}
        </text>
        <text className="pls-tick" x={W - PAD} y={H - 6} textAnchor="end">
          {t.km(hist.hi)}
        </text>
        {short != null && short >= hist.lo && short <= hist.hi && (
          <g className="pls-mark short">
            <line x1={x(short)} x2={x(short)} y1={16} y2={H - 20} />
            <text x={x(short)} y={12} textAnchor="middle">
              {t.histShort}
            </text>
          </g>
        )}
        <g className="pls-mark text">
          <line x1={x(path)} x2={x(path)} y1={16} y2={H - 20} />
          <text x={x(path)} y={12} textAnchor={x(path) < W / 4 ? 'start' : 'middle'}>
            {t.histText}
          </text>
        </g>
      </svg>
    </figure>
  )
}

/** A district's colour: twelve distinct ones, in turn (a 13th district reuses the first). */
const DISTRICT_COLOURS = ['#c0392b', '#2471a3', '#d68910', '#229954', '#7d3c98', '#17a589', '#a04000', '#d4499a', '#5d6d7e', '#7d9c1e', '#1b4f72', '#b7950b']
const districtFill = (d: number) => DISTRICT_COLOURS[(d - 1 + DISTRICT_COLOURS.length) % DISTRICT_COLOURS.length]

function Districts({ groupings, alpha }: { groupings: DistrictGrouping[]; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.pls
  const [params, update] = useQueryParams()
  const key = groupings.some((g) => g.key === params.get('group')) ? params.get('group')! : groupings[0].key
  const g = groupings.find((x) => x.key === key)!
  const res = usePlaceDistricts(key)
  const basemap = useBasemap()
  const [moved, setMoved] = useState<{ key: string; bounds: Bounds }>()
  const towns = useMemo(() => (res.data?.grouping.key === key ? res.data.towns : []), [res.data, key])
  const districtOf = useMemo(() => new Map(towns.map((x) => [x.place.place_id, x.district])), [towns])
  const points: GeoPoint[] = useMemo(
    () => towns.flatMap((x) => (x.place.lat != null && x.place.lon != null ? [{ place_id: x.place.place_id, he: x.place.he, kind: x.place.kind, lat: x.place.lat, lon: x.place.lon, n: 1 }] : [])),
    [towns],
  )
  const name = (k: string) => t.groupings[k] ?? k
  const a = g.all
  const s = g.sure
  const bounds = moved?.key === key ? moved.bounds : (fitBounds(points) ?? VIEWS.land)
  return (
    <section className="pls-districts" id="districts" aria-label={t.districtsTitle}>
      <h2>{t.districtsTitle}</h2>
      <p className="muted small">{t.districtsLede}</p>
      {groupings.length > 1 && (
        <Segmented label={t.grouping} value={key} onChange={(x) => update({ group: x === groupings[0].key ? null : x }, false)} options={groupings.map((x) => ({ value: x.key, label: name(x.key) }))} />
      )}
      {a.p != null && (
        <p>
          <Verdict holds={a.p <= alpha} /> {t.districtSummary(a.n, a.districts ?? 0, a.within_km ?? 0, a.null_mean ?? 0, a.p, a.nearest_same ?? 0)}
          {s.p != null && <> {t.districtSure(s.n, s.within_km ?? 0, s.null_mean ?? 0, s.p)}</>}
        </p>
      )}
      <div className="places-layout pls-district-layout">
        <div className="places-map">
          {res.isPending ? (
            <Loading />
          ) : res.error ? (
            <ErrorBox error={res.error} />
          ) : (
            <GeoMap
              basemap={basemap.data}
              points={points}
              bounds={bounds}
              onBounds={(b) => setMoved({ key, bounds: b })}
              onSelect={() => undefined}
              label={t.districtMap(name(key))}
              fillOf={(p) => districtFill(districtOf.get(p.place_id) ?? 0)}
            />
          )}
        </div>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.districtsTitle}>
          <table className="change-table pls-table">
            <thead>
              <tr>
                <th>{t.dcols.district}</th>
                <th>{t.dcols.towns}</th>
                <th>{t.dcols.apart}</th>
                <th>{t.dcols.random}</th>
                <th>{t.dcols.p}</th>
                <th>{t.dcols.sure}</th>
              </tr>
            </thead>
            <tbody>
              {g.districts.map((d) => (
                <tr key={d.district}>
                  <td>
                    <span className="geo-key" style={{ background: districtFill(d.district) }} aria-hidden="true" />{' '}
                    <Link to={unitLink(`v:${d.first_vid}`)}>{locale === 'he' ? d.label_he : d.label_en}</Link>
                  </td>
                  <td>{d.all?.n ?? 0}</td>
                  {d.all?.p == null ? (
                    <td colSpan={3} className="muted">
                      {t.single}
                    </td>
                  ) : (
                    <>
                      <td>{t.km(d.all.within_km ?? 0)}</td>
                      <td>{t.km(d.all.null_mean ?? 0)}</td>
                      <td>
                        <Verdict holds={d.all.p <= alpha} /> {t.p(d.all.p)}
                      </td>
                    </>
                  )}
                  <td className={d.sure?.p == null ? 'muted' : undefined}>{d.sure?.p == null ? (d.sure?.n ?? 0) : `${d.sure.n} · p ${t.p(d.sure.p)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
