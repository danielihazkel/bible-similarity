import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAffinity, useAffinityPairs, useBooks, useCorpusMap } from '../api/hooks'
import type { Book, MapPoint, UnitSummary, UnitType, Verse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { LinkBadge } from '../components/LinkBadge'
import { ErrorBox, Loading } from '../components/Status'
import { unitTypeLabel } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha']
type ColorBy = 'cluster' | 'section'
type Order = 'related' | 'canon'

// Categorical hues (12, colour-blind-aware order), cycled for >12 clusters; sections use the first 3.
const HUES = [210, 25, 140, 330, 50, 270, 175, 0, 95, 300, 230, 120]
const color = (i: number, alpha = 1) => `hsla(${HUES[i % HUES.length]}, 62%, ${i >= HUES.length ? 38 : 48}%, ${alpha})`
const SECTIONS = ['Torah', 'Prophets', 'Writings']

export function MapPage() {
  const [params, update] = useQueryParams()
  const raw = params.get('type') as UnitType | null
  const unitType = raw && TYPES.includes(raw) ? raw : 'chapter'
  const colorBy: ColorBy = params.get('color') === 'section' ? 'section' : 'cluster'
  const order: Order = params.get('order') === 'canon' ? 'canon' : 'related'
  const books = useBooks()
  const map = useCorpusMap(unitType)
  const [focus, setFocus] = useState<number>()

  return (
    <div className="page map-page">
      <h1>Map of the Tanakh</h1>
      <p className="lede">
        Every {unitTypeLabel(unitType).toLowerCase()} placed by meaning (t-SNE of the semantic embeddings): nearby points read
        alike. Colours are thematic clusters, labelled by the lemmas they use most.
      </p>
      <div className="toolbar">
        <Segmented
          label="Unit type"
          value={unitType}
          onChange={(t) => {
            setFocus(undefined)
            update({ type: t === 'chapter' ? null : t })
          }}
          options={TYPES.map((t) => ({ value: t, label: unitTypeLabel(t) }))}
        />
        <Segmented
          label="Colour by"
          value={colorBy}
          onChange={(c) => update({ color: c === 'cluster' ? null : c })}
          options={[
            { value: 'cluster', label: 'Clusters' },
            { value: 'section', label: 'Torah / Prophets / Writings' },
          ]}
        />
      </div>
      {map.isPending || books.isPending ? (
        <Loading />
      ) : map.error ? (
        <ErrorBox error={map.error} />
      ) : books.error ? (
        <ErrorBox error={books.error} />
      ) : (
        <div className="map-grid">
          <Scatter
            points={map.data.points}
            books={books.data}
            colorBy={colorBy}
            focus={focus}
          />
          {colorBy === 'cluster' ? (
            <ul className="cluster-legend" aria-label="Clusters">
              {map.data.clusters.map((c) => (
                <li key={c.cluster}>
                  <button
                    type="button"
                    className={focus === c.cluster ? 'on' : undefined}
                    aria-pressed={focus === c.cluster}
                    onClick={() => setFocus(focus === c.cluster ? undefined : c.cluster)}
                  >
                    <span className="swatch" style={{ background: color(c.cluster) }} />
                    <span dir="rtl" lang="he" className="he">
                      {c.lemmas.map((l) => l.he_lemma).join(' · ')}
                    </span>
                    <span className="muted small">{c.size}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="cluster-legend">
              {SECTIONS.map((s, i) => (
                <li key={s}>
                  <span className="legend-row">
                    <span className="swatch" style={{ background: color(i) }} /> {s}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <h2>How the books talk to each other</h2>
      <p className="muted small">
        Cross-book verse pairs in each other's fused top 10, relative to what the books' sizes would predict (lift; darker =
        more). Click a cell for its strongest pairs.
      </p>
      <div className="toolbar">
        <Segmented
          label="Book order"
          value={order}
          onChange={(o) => update({ order: o === 'related' ? null : o })}
          options={[
            { value: 'related', label: 'Related books together' },
            { value: 'canon', label: 'Canon order' },
          ]}
        />
      </div>
      {books.data && <Affinity books={books.data} order={order} pair={params.get('pair')} onPair={(p) => update({ pair: p })} />}
    </div>
  )
}

function Scatter({ points, books, colorBy, focus }: { points: MapPoint[]; books: Book[]; colorBy: ColorBy; focus?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const navigate = useNavigate()
  const [hover, setHover] = useState<MapPoint>()
  const section = useMemo(() => new Map(books.map((b) => [b.book_id, SECTIONS.indexOf(b.section)])), [books])
  const W = 720
  const H = 560
  const pad = 12
  const px = (p: MapPoint) => pad + p.x * (W - 2 * pad)
  const py = (p: MapPoint) => pad + p.y * (H - 2 * pad)
  const radius = points.length > 1000 ? 3 : points.length > 100 ? 4.5 : 8

  useEffect(() => {
    const ctx = ref.current?.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, W, H)
    for (const p of points) {
      const c = colorBy === 'cluster' ? p.cluster : (section.get(p.book_id) ?? 0)
      const dim = focus !== undefined && p.cluster !== focus
      ctx.fillStyle = color(c, dim ? 0.12 : 0.85)
      ctx.beginPath()
      ctx.arc(px(p), py(p), radius, 0, 2 * Math.PI)
      ctx.fill()
    }
  })

  const nearest = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - r.left) / r.width) * W
    const y = ((e.clientY - r.top) / r.height) * H
    let best: MapPoint | undefined
    let bd = (radius + 4) ** 2
    for (const p of points) {
      const d = (px(p) - x) ** 2 + (py(p) - y) ** 2
      if (d < bd) [best, bd] = [p, d]
    }
    return best
  }

  return (
    <figure className="scatter">
      <canvas
        ref={ref}
        width={W}
        height={H}
        role="img"
        aria-label="Map of units by meaning"
        style={{ cursor: hover ? 'pointer' : 'default' }}
        onMouseMove={(e) => setHover(nearest(e))}
        onMouseLeave={() => setHover(undefined)}
        onClick={(e) => {
          const p = nearest(e)
          if (p) navigate(unitLink(p.unit_id))
        }}
      />
      <figcaption className="muted small">
        {hover ? (
          <>
            {hover.label_en}{' '}
            <span dir="rtl" lang="he">
              {hover.label_he}
            </span>{' '}
            · {hover.n_verses} verses · click to open
          </>
        ) : (
          'Hover a point; click to open the unit.'
        )}
      </figcaption>
    </figure>
  )
}

function Affinity({ books, order, pair, onPair }: { books: Book[]; order: Order; pair: string | null; onPair: (p: string | null) => void }) {
  const aff = useAffinity()
  const [sel, setSel] = useState<string>()
  const [a, b] = (pair ?? '').split('-').map(Number)
  const examples = useAffinityPairs(Number.isInteger(a) && Number.isInteger(b) && pair ? a : undefined, b)
  if (aff.isPending) return <Loading />
  if (aff.error) return <ErrorBox error={aff.error} />
  const ids = order === 'canon' || aff.data.order.length === 0 ? books.map((x) => x.book_id) : aff.data.order
  const name = new Map(books.map((x) => [x.book_id, x]))
  const lift = new Map<string, { lift: number; n: number }>()
  for (const c of aff.data.cells) {
    lift.set(`${c.a}-${c.b}`, { lift: c.lift, n: c.n_pairs })
    lift.set(`${c.b}-${c.a}`, { lift: c.lift, n: c.n_pairs })
  }
  const maxLog = Math.max(...aff.data.cells.map((c) => Math.log1p(c.lift)), 1e-9)
  const cell = 14
  const label = 96
  const n = ids.length
  const size = label + n * cell
  return (
    <div className="affinity">
      <div className="table-wrap">
        <svg width={size + 36} height={size} role="img" aria-label="Book by book affinity">
          {ids.map((id, i) => (
            <text key={`r${id}`} x={label - 4} y={label + i * cell + cell * 0.75} textAnchor="end" className="axis">
              {name.get(id)?.name}
            </text>
          ))}
          {ids.map((id, j) => (
            <text
              key={`c${id}`}
              transform={`translate(${label + j * cell + cell * 0.7}, ${label - 4}) rotate(-60)`}
              className="axis"
            >
              {name.get(id)?.name}
            </text>
          ))}
          {ids.map((ra, i) =>
            ids.map((rb, j) => {
              if (ra === rb) return null
              const v = lift.get(`${ra}-${rb}`)
              const t = v ? Math.log1p(v.lift) / maxLog : 0
              const key = `${ra}-${rb}`
              const on = sel === key || pair === key
              return (
                <rect
                  key={key}
                  x={label + j * cell}
                  y={label + i * cell}
                  width={cell - 1}
                  height={cell - 1}
                  className={`aff-cell ${on ? 'on' : ''}`}
                  style={{ fillOpacity: 0.06 + 0.94 * t }}
                  onMouseEnter={() => setSel(key)}
                  onMouseLeave={() => setSel(undefined)}
                  onClick={() => onPair(pair === key ? null : key)}
                >
                  <title>
                    {`${name.get(ra)?.name} ↔ ${name.get(rb)?.name}: ${v?.n ?? 0} pairs, lift ${(v?.lift ?? 0).toFixed(1)}`}
                  </title>
                </rect>
              )
            }),
          )}
        </svg>
      </div>
      {pair && examples.data && (
        <section aria-label="Book pair examples">
          <h3>
            {name.get(a)?.name} ↔ {name.get(b)?.name}: strongest pairs
          </h3>
          {examples.data.length === 0 ? (
            <p className="status">No pairs.</p>
          ) : (
            <ol className="disc-list">
              {examples.data.map((p) => (
                <li key={`${p.a.unit_id}|${p.b.unit_id}`} className="disc">
                  <div className="hit-head">
                    <span className="score">{p.score.toFixed(3)}</span>
                    <LinkBadge link={p.link} />
                    <span className="hit-actions">
                      <Link className="linkish" to={compareLink(p.a.unit_id, p.b.unit_id)}>
                        Compare
                      </Link>
                    </span>
                  </div>
                  <div className="disc-pair">
                    <ExampleSide unit={p.a} verse={p.a_verse} />
                    <ExampleSide unit={p.b} verse={p.b_verse} />
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  )
}

function ExampleSide({ unit, verse }: { unit: UnitSummary; verse: Verse }) {
  return (
    <div className="disc-side">
      <Link className="hit-ref" to={unitLink(unit.unit_id)}>
        {unit.label_en}
      </Link>
      <p className="hit-text">
        <HebrewText verse={verse} />
      </p>
    </div>
  )
}
