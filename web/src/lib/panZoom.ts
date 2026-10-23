// Drag to pan, pinch or Ctrl + wheel to zoom: the gestures of the map (GeoMap) and the family tree,
// in CSS pixels. The caller keeps its own view (bounds, a transform) and applies each step to it.

import { type RefObject, useEffect, useRef } from 'react'

export interface PanZoomOptions {
  /** Moved by (dx, dy) CSS pixels since the last call. */
  onPan?: (dx: number, dy: number) => void
  /** Zoomed by `factor` (> 1: in) about (x, y), in CSS pixels from the element's top left. */
  onZoom?: (factor: number, x: number, y: number) => void
  /** What a wheel does: 'ctrl' (the default) zooms only with Ctrl and leaves a plain wheel to
   * scroll the page; 'zoom' zooms with a plain wheel too, Shift + wheel or a sideways swipe pans. */
  wheel?: 'ctrl' | 'zoom'
}

const SLOP = 4 // CSS pixels a pointer moves before a press becomes a drag
const WHEEL = 0.002 // zoom per wheel pixel (Ctrl + wheel, a touchpad's pinch)
const LINE = 16 // CSS pixels a wheel "line" counts as (Firefox's line mode)
const STEP_MAX = 1.5 // the most one wheel event zooms by (a mouse's notches can be large)

/** A wheel event's (dx, dy) in CSS pixels, whatever its unit. */
const wheelPixels = (w: WheelEvent): [number, number] => {
  const f = w.deltaMode === 1 ? LINE : w.deltaMode === 2 ? 800 : 1
  return [w.deltaX * f, w.deltaY * f]
}

interface Centre {
  x: number
  y: number
  d: number // the distance between the first two pointers (0 with one)
}

/**
 * Pointer handlers for an element that pans and zooms, and `dragged()`: whether the press that
 * ends in a click was a drag (its click should then do nothing). By default a plain wheel still
 * scrolls the page and Ctrl + wheel zooms (`wheel: 'zoom'` zooms with any wheel). The element wants
 * `touch-action: none`.
 */
export function usePanZoom(ref: RefObject<Element | null>, options: PanZoomOptions) {
  const opts = useRef(options)
  useEffect(() => {
    opts.current = options
  })
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const last = useRef<Centre | undefined>(undefined)
  const origin = useRef({ x: 0, y: 0 })
  const moved = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onWheel = (e: Event) => {
      const w = e as WheelEvent
      const o = opts.current
      const ctrl = w.ctrlKey || w.metaKey
      if (!ctrl && o.wheel !== 'zoom') return
      const [dx, dy] = wheelPixels(w)
      // Shift + wheel, or a touchpad's sideways swipe: move across
      if (!ctrl && (w.shiftKey || Math.abs(dx) > Math.abs(dy))) {
        if (!o.onPan) return
        w.preventDefault()
        o.onPan(-(w.shiftKey && !dx ? dy : dx), 0)
        return
      }
      if (!o.onZoom) return
      w.preventDefault()
      const r = el.getBoundingClientRect()
      const f = Math.min(STEP_MAX, Math.max(1 / STEP_MAX, Math.exp(-dy * WHEEL)))
      o.onZoom(f, w.clientX - r.left, w.clientY - r.top)
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [ref])

  const centre = (): Centre | undefined => {
    const ps = [...pointers.current.values()]
    if (!ps.length) return undefined
    const x = ps.reduce((s, p) => s + p.x, 0) / ps.length
    const y = ps.reduce((s, p) => s + p.y, 0) / ps.length
    return { x, y, d: ps.length > 1 ? Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y) : 0 }
  }

  const onPointerDown = (e: React.PointerEvent<Element>) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return
    if (!pointers.current.size) {
      moved.current = false
      origin.current = { x: e.clientX, y: e.clientY }
    }
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    last.current = centre()
  }
  const onPointerMove = (e: React.PointerEvent<Element>) => {
    const p = pointers.current.get(e.pointerId)
    if (!p) return
    p.x = e.clientX
    p.y = e.clientY
    const c = centre()
    const l = last.current
    if (!c || !l) return
    if (!moved.current) {
      if (pointers.current.size < 2 && Math.hypot(c.x - origin.current.x, c.y - origin.current.y) < SLOP) return
      moved.current = true
    }
    e.currentTarget.setPointerCapture?.(e.pointerId)
    if (c.d > 0 && l.d > 0 && opts.current.onZoom) {
      const r = e.currentTarget.getBoundingClientRect()
      opts.current.onZoom(c.d / l.d, c.x - r.left, c.y - r.top)
    }
    opts.current.onPan?.(c.x - l.x, c.y - l.y)
    last.current = c
  }
  const onPointerUp = (e: React.PointerEvent<Element>) => {
    pointers.current.delete(e.pointerId)
    last.current = centre()
    // the click that ends a drag comes after this: forget the drag once it has passed
    if (!pointers.current.size) setTimeout(() => (moved.current = false), 0)
  }

  return {
    handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp },
    dragged: () => moved.current,
  }
}
