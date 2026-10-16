import { useEffect, useMemo, useRef, useState } from 'react'
import type { BasemapResponse } from '../api/types'
import { useT } from '../context/localeContext'
import { type Bounds, type GeoPoint, panBounds, projectX, projectY, ringsPath, viewBox, zoomBounds } from '../lib/geo'

interface Props {
  basemap: BasemapResponse | undefined
  points: GeoPoint[]
  bounds: Bounds
  /** Pan and zoom: called with the new bounds; without it the map is fixed. */
  onBounds?: (b: Bounds) => void
  selected?: number
  onSelect: (placeId: number) => void
  label: string
  /** Names written beside the most named points. */
  labels?: number
  aspect?: number
  /** Lines under the points, as [lon, lat] (a list's path). */
  paths?: { key: string; className: string; coords: [number, number][] }[]
  /** A point's fill in place of its kind's colour (a district's). */
  fillOf?: (p: GeoPoint) => string | undefined
  /** The name written beside a point (default: its Hebrew name). */
  labelOf?: (p: GeoPoint) => string
}

const R_MIN = 3 // point radius in CSS pixels: R_MIN + R_LOG × log2(1 + verses), at most R_MAX
const R_LOG = 1
const R_MAX = 13
const FONT = 12
const CHAR = 0.62 // a Hebrew letter's width, in font sizes (for keeping labels apart)
const ZOOM = 1.6

/**
 * The places on an SVG map of the region (§16.57): Natural Earth's land, lakes and rivers under
 * points sized by how often each place is named and coloured by its kind. Drag to pan, the
 * buttons (or + / −) to zoom; with keyboard focus, ←/→ step through the places, most named first,
 * and Enter opens the current one.
 */
export function GeoMap({ basemap, points, bounds, onBounds, selected, onSelect, label, labels = 0, aspect = 0.85, paths = [], fillOf, labelOf = (p) => p.he }: Props) {
  const m = useT()
  const t = m.geo
  const ref = useRef<SVGSVGElement>(null)
  const [width, setWidth] = useState(640)
  const [cur, setCur] = useState<number>()
  const drag = useRef<{ x: number; y: number; b: Bounds; moved: boolean } | undefined>(undefined)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([e]) => e.contentRect.width && setWidth(e.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const vb = viewBox(bounds, aspect)
  const k = vb.w / width // map units per CSS pixel
  const land = useMemo(() => (basemap?.shapes ?? []).filter((s) => s.layer === 'land').map((s) => ringsPath(s.rings, true)), [basemap])
  const lakes = useMemo(() => (basemap?.shapes ?? []).filter((s) => s.layer === 'lakes').map((s) => ringsPath(s.rings, true)), [basemap])
  const rivers = useMemo(() => (basemap?.shapes ?? []).filter((s) => s.layer === 'rivers').map((s) => ringsPath(s.rings, false)), [basemap])
  // most named first: drawn first (the small on top), stepped through first
  const order = useMemo(() => [...points].sort((a, b) => b.n - a.n || a.place_id - b.place_id), [points])
  // a fixed scale, so a point's size means the same in a chapter as in the whole Bible
  const radius = (p: GeoPoint) => Math.min(R_MAX, R_MIN + R_LOG * Math.log2(1 + p.n)) * k
  const current = cur === undefined ? undefined : order[cur]
  // names beside the most named places in view (and the one selected), none over another
  const named = new Set<number>()
  const boxes: [number, number, number, number][] = []
  const inView = (p: GeoPoint) => {
    const x = projectX(p.lon)
    const y = projectY(p.lat)
    return x >= vb.x && x <= vb.x + vb.w && y >= vb.y && y <= vb.y + vb.h
  }
  const candidates = [...order.filter((p) => p.place_id === selected), ...order.filter((p) => p.place_id !== selected)]
  for (const p of candidates) {
    if (named.size >= labels + (selected === undefined ? 0 : 1) || !inView(p)) continue
    const x0 = projectX(p.lon) + radius(p) + 2 * k
    const box: [number, number, number, number] = [x0, projectY(p.lat) - 0.6 * FONT * k, x0 + labelOf(p).length * CHAR * FONT * k, projectY(p.lat) + 0.6 * FONT * k]
    if (boxes.some((b) => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3])) continue
    boxes.push(box)
    named.add(p.place_id)
  }

  const zoom = (f: number) => onBounds?.(zoomBounds(bounds, f))
  const onKey = (e: React.KeyboardEvent<SVGSVGElement>) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]
    if (step !== undefined && order.length) {
      e.preventDefault()
      setCur((c) => (c === undefined ? 0 : (c + step + order.length) % order.length))
    } else if (e.key === 'Enter' && current) onSelect(current.place_id)
    else if ((e.key === '+' || e.key === '=') && onBounds) zoom(ZOOM)
    else if (e.key === '-' && onBounds) zoom(1 / ZOOM)
  }
  const toDeg = (dx: number) => (dx * vb.w) / width
  const onDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!onBounds) return
    drag.current = { x: e.clientX, y: e.clientY, b: bounds, moved: false }
  }
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current
    if (!d || !onBounds) return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (!d.moved && Math.hypot(dx, dy) < 4) return
    if (!d.moved) e.currentTarget.setPointerCapture?.(e.pointerId)
    d.moved = true
    onBounds(panBounds(d.b, -toDeg(dx) / projectX(1), toDeg(dy)))
  }
  const onUp = () => {
    setTimeout(() => (drag.current = undefined), 0)
  }
  const pick = (p: GeoPoint) => {
    if (drag.current?.moved) return
    onSelect(p.place_id)
  }

  return (
    // left to right in either interface language: east is to the right
    <figure className="geo-map" dir="ltr">
      <svg
        ref={ref}
        viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
        style={{ aspectRatio: `${aspect}` }}
        role="img"
        aria-label={t.keys(label)}
        tabIndex={0}
        onKeyDown={onKey}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        className={onBounds ? 'pannable' : undefined}
      >
        <rect className="geo-sea" x={vb.x} y={vb.y} width={vb.w} height={vb.h} />
        {land.map((d, i) => (
          <path key={`l${i}`} className="geo-land" d={d} fillRule="evenodd" />
        ))}
        {lakes.map((d, i) => (
          <path key={`k${i}`} className="geo-lake" d={d} fillRule="evenodd" />
        ))}
        {rivers.map((d, i) => (
          <path key={`r${i}`} className="geo-river" d={d} vectorEffect="non-scaling-stroke" />
        ))}
        {paths.map((l) => (
          <path key={l.key} className={l.className} d={ringsPath([l.coords], false)} vectorEffect="non-scaling-stroke" />
        ))}
        {order.map((p) => (
          <circle
            key={p.place_id}
            className={`geo-pt kind-${p.kind ?? 'none'}${p.place_id === selected ? ' selected' : ''}${p === current ? ' current' : ''}`}
            cx={projectX(p.lon)}
            cy={projectY(p.lat)}
            r={radius(p)}
            style={fillOf ? { fill: fillOf(p) } : undefined}
            vectorEffect="non-scaling-stroke"
            onClick={() => pick(p)}
          >
            <title>{t.pointTitle(p.he, p.n)}</title>
          </circle>
        ))}
        {order
          .filter((p) => named.has(p.place_id))
          .map((p) => (
            <text key={`t${p.place_id}`} className="geo-label" x={projectX(p.lon) + radius(p) + 2 * k} y={projectY(p.lat) + 0.35 * FONT * k} fontSize={FONT * k} lang="he">
              {labelOf(p)}
            </text>
          ))}
      </svg>
      {onBounds && (
        <div className="geo-zoom" role="group" aria-label={t.zoom}>
          <button type="button" onClick={() => zoom(ZOOM)} aria-label={t.zoomIn}>
            +
          </button>
          <button type="button" onClick={() => zoom(1 / ZOOM)} aria-label={t.zoomOut}>
            −
          </button>
        </div>
      )}
      <figcaption className="muted small" aria-live="polite" dir="auto">
        {current ? t.pointTitle(current.he, current.n) : t.idle}
      </figcaption>
    </figure>
  )
}
