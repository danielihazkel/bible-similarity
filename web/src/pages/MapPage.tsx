import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useAffinity, useAffinityPairs, useBooks, useCorpusMap } from '../api/hooks'
import type { Book, MapPoint, UnitSummary, UnitType, Verse } from '../api/types'
import { BookHeatmap } from '../components/BookHeatmap'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { LinkBadge } from '../components/LinkBadge'
import { Scatter } from '../components/Scatter'
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
          <MapScatter
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

function MapScatter({ points, books, colorBy, focus }: { points: MapPoint[]; books: Book[]; colorBy: ColorBy; focus?: number }) {
  const section = useMemo(() => new Map(books.map((b) => [b.book_id, SECTIONS.indexOf(b.section)])), [books])
  const r = points.length > 1000 ? 3 : points.length > 100 ? 4.5 : 8
  return (
    <Scatter
      points={points}
      width={720}
      height={560}
      label="Map of units by meaning"
      fill={(p) => color(colorBy === 'cluster' ? p.cluster : (section.get(p.book_id) ?? 0), focus !== undefined && p.cluster !== focus ? 0.12 : 0.85)}
      radius={() => r}
      front={focus === undefined ? undefined : (p) => p.cluster === focus}
      caption={(p) => (
        <>
          {p.label_en}{' '}
          <span dir="rtl" lang="he">
            {p.label_he}
          </span>{' '}
          · {p.n_verses} verses · click to open
        </>
      )}
      idle="Hover a point; click to open the unit."
    />
  )
}

function Affinity({ books, order, pair, onPair }: { books: Book[]; order: Order; pair: string | null; onPair: (p: string | null) => void }) {
  const aff = useAffinity()
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
  return (
    <div className="affinity">
      <BookHeatmap
        books={books}
        order={ids}
        value={(ra, rb) => {
          const v = lift.get(`${ra}-${rb}`)
          return v ? Math.log1p(v.lift) / maxLog : 0
        }}
        title={(ra, rb) => {
          const v = lift.get(`${ra}-${rb}`)
          return `${name.get(ra)?.name} ↔ ${name.get(rb)?.name}: ${v?.n ?? 0} pairs, lift ${(v?.lift ?? 0).toFixed(1)}`
        }}
        selected={pair}
        onSelect={onPair}
        label="Book by book affinity"
      />
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
