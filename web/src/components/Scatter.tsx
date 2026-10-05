import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useT } from '../context/localeContext'
import { unitLink } from '../lib/links'

/** A plotted unit: `x`, `y` in 0..1. */
export interface ScatterPoint {
  unit_id: string
  x: number
  y: number
}

interface Props<P extends ScatterPoint> {
  points: P[]
  width: number
  height: number
  label: string
  fill: (p: P) => string
  radius: (p: P) => number
  /** Points drawn on top (e.g. a highlighted book). */
  front?: (p: P) => boolean
  caption: (p: P) => ReactNode
  idle: ReactNode
}

const PAD = 12
const TOUCH_PX = 12 // smallest hit radius in CSS pixels, so scaled-down canvases stay tappable
const BUCKET = 24 // hover lookup grid, in canvas pixels

/**
 * Canvas scatter of units, sharp on high-DPI screens. Hover (or tap) shows a point's caption and a
 * click opens the unit. With keyboard focus, ←/→ step through the points in their given order
 * (canon order) and Enter opens the current one. The points are drawn once per change of the
 * points or their styling; the hover ring lives on an overlay canvas, and the hover lookup uses
 * a bucket grid instead of scanning every point.
 */
export function Scatter<P extends ScatterPoint>({ points, width: W, height: H, label, fill, radius, front, caption, idle }: Props<P>) {
  const m = useT()
  const ref = useRef<HTMLCanvasElement>(null)
  const overlay = useRef<HTMLCanvasElement>(null)
  const navigate = useNavigate()
  const [hover, setHover] = useState<number>()
  const px = (p: P) => PAD + p.x * (W - 2 * PAD)
  const py = (p: P) => PAD + p.y * (H - 2 * PAD)
  const dpr = typeof window === 'undefined' ? 1 : Math.max(1, window.devicePixelRatio || 1)
  const current = hover === undefined ? undefined : points[hover]

  // the points: redrawn when they or their styling change (the parent re-renders), not on hover
  useEffect(() => {
    const ctx = ref.current?.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, W, H)
    const draw = (p: P) => {
      ctx.fillStyle = fill(p)
      ctx.beginPath()
      ctx.arc(PAD + p.x * (W - 2 * PAD), PAD + p.y * (H - 2 * PAD), radius(p), 0, 2 * Math.PI)
      ctx.fill()
    }
    for (const p of points) if (!front?.(p)) draw(p)
    if (front) for (const p of points) if (front(p)) draw(p)
  }, [points, fill, radius, front, W, H, dpr])

  // the hover ring
  useEffect(() => {
    const ctx = overlay.current?.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, W, H)
    if (!current) return
    ctx.strokeStyle = getComputedStyle(overlay.current!).color || '#000'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.arc(PAD + current.x * (W - 2 * PAD), PAD + current.y * (H - 2 * PAD), radius(current) + 3, 0, 2 * Math.PI)
    ctx.stroke()
  }, [current, radius, W, H, dpr])

  const grid = useMemo(() => {
    const g = new Map<string, number[]>()
    points.forEach((p, i) => {
      const key = `${Math.floor((PAD + p.x * (W - 2 * PAD)) / BUCKET)},${Math.floor((PAD + p.y * (H - 2 * PAD)) / BUCKET)}`
      const list = g.get(key)
      if (list) list.push(i)
      else g.set(key, [i])
    })
    return g
  }, [points, W, H])

  const nearest = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const scale = r.width ? W / r.width : 1
    const x = (e.clientX - r.left) * scale
    const y = (e.clientY - r.top) * scale
    let best: number | undefined
    let bd = Infinity
    const reach = Math.ceil(Math.max(TOUCH_PX * scale, 16) / BUCKET)
    const cx = Math.floor(x / BUCKET)
    const cy = Math.floor(y / BUCKET)
    for (let gx = cx - reach; gx <= cx + reach; gx++)
      for (let gy = cy - reach; gy <= cy + reach; gy++)
        for (const i of grid.get(`${gx},${gy}`) ?? []) {
          const p = points[i]
          const tol = Math.max(radius(p) + 4, TOUCH_PX * scale)
          const d = (px(p) - x) ** 2 + (py(p) - y) ** 2
          if (d < tol * tol && d < bd) [best, bd] = [i, d]
        }
    return best
  }

  const onKey = (e: React.KeyboardEvent<HTMLCanvasElement>) => {
    if (!points.length) return
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]
    if (step !== undefined) {
      e.preventDefault()
      setHover((h) => (h === undefined ? 0 : (h + step + points.length) % points.length))
    } else if (e.key === 'Enter' && current) {
      navigate(unitLink(current.unit_id))
    }
  }

  return (
    // left to right in either interface language: the axes have no reading direction to mirror
    <figure className="scatter" dir="ltr">
      <div className="scatter-stack">
      <canvas
        ref={ref}
        width={W * dpr}
        height={H * dpr}
        style={{ aspectRatio: `${W} / ${H}`, cursor: current ? 'pointer' : 'default' }}
        role="img"
        aria-label={m.ov.chart.scatterKeys(label)}
        tabIndex={0}
        onKeyDown={onKey}
        onMouseMove={(e) => setHover(nearest(e))}
        onMouseLeave={() => setHover(undefined)}
        onClick={(e) => {
          const i = nearest(e)
          if (i !== undefined) navigate(unitLink(points[i].unit_id))
        }}
      />
      <canvas
        ref={overlay}
        className="scatter-overlay"
        width={W * dpr}
        height={H * dpr}
        style={{ aspectRatio: `${W} / ${H}` }}
        aria-hidden="true"
      />
      </div>
      <figcaption className="muted small" aria-live="polite" dir="auto">
        {current ? caption(current) : idle}
      </figcaption>
    </figure>
  )
}
