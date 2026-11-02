// Drawing primitives for the line-art films: paths traced by a pen, glyph outlines, type, the
// capture frame. Style after mg-styles-15 "02 · Line Art": one champagne-gold line of constant
// width on a midnight ground, slowing at corners, glowing softly.

export const W = 1920
export const H = 1080
export const C = {
  ground: '#0B1320',
  gold: '#E9D7A5',
  aged: '#967D50',
  hot: '#FFF6DC',
}
export const gold = (a) => `rgba(233,215,165,${a})`
export const hot = (a) => `rgba(255,246,220,${a})`
export const LW = 3 // the line's width on screen, whatever the camera does

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x))
export const lerp = (a, b, t) => a + (b - a) * t
// cubic-bezier(.65,0,.35,1), close enough: the pen slows into and out of every move
export const ease = (t) => {
  t = clamp(t)
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
}
export const easeOut = (t) => 1 - (1 - clamp(t)) ** 3
export const span = (t, a, b) => clamp((t - a) / (b - a))
export const smooth = (t, a, b) => ease(span(t, a, b))
// up over [a, a + rise], down over [b - fall, b]
export const window_ = (t, a, b, rise = 0.5, fall = 0.5) => smooth(t, a, a + rise) * (1 - smooth(t, b - fall, b))

export function rng(seed) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// --- paths ---------------------------------------------------------------------------------

export class Path {
  constructor(pts, closed = false) {
    this.pts = closed && pts.length ? [...pts, pts[0]] : pts
    this.cum = [0]
    for (let i = 1; i < this.pts.length; i++) {
      const [x0, y0] = this.pts[i - 1]
      const [x1, y1] = this.pts[i]
      this.cum.push(this.cum[i - 1] + Math.hypot(x1 - x0, y1 - y0))
    }
  }
  get length() { return this.cum[this.cum.length - 1] }
  at(f) {
    const d = clamp(f) * this.length
    let i = 1
    while (i < this.cum.length - 1 && this.cum[i] < d) i++
    const seg = this.cum[i] - this.cum[i - 1] || 1
    const k = (d - this.cum[i - 1]) / seg
    const [x0, y0] = this.pts[i - 1]
    const [x1, y1] = this.pts[i] ?? this.pts[i - 1]
    return [lerp(x0, x1, k), lerp(y0, y1, k)]
  }
  // adds the stretch [a, b] (fractions of the length) to the current path
  trace(ctx, a = 0, b = 1) {
    if (this.pts.length < 2 || b <= a) return
    const da = a * this.length
    const db = b * this.length
    let started = false
    for (let i = 1; i < this.pts.length; i++) {
      const s0 = this.cum[i - 1]
      const s1 = this.cum[i]
      if (s1 < da) continue
      if (s0 > db) break
      const [x0, y0] = this.pts[i - 1]
      const [x1, y1] = this.pts[i]
      const len = s1 - s0 || 1
      const k0 = clamp((da - s0) / len)
      const k1 = clamp((db - s0) / len)
      if (!started) {
        ctx.moveTo(lerp(x0, x1, k0), lerp(y0, y1, k0))
        started = true
      }
      ctx.lineTo(lerp(x0, x1, k1), lerp(y0, y1, k1))
    }
  }
  static line(x0, y0, x1, y1) { return new Path([[x0, y0], [x1, y1]]) }
  static poly(pts, closed = false) { return new Path(pts, closed) }
  static quad(p0, p1, p2, n = 32) {
    const pts = []
    for (let i = 0; i <= n; i++) {
      const t = i / n
      const u = 1 - t
      pts.push([u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]])
    }
    return new Path(pts)
  }
  static cubic(p0, p1, p2, p3, n = 40) {
    const pts = []
    for (let i = 0; i <= n; i++) {
      const t = i / n
      const u = 1 - t
      const a = u * u * u
      const b = 3 * u * u * t
      const c = 3 * u * t * t
      const d = t * t * t
      pts.push([a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]])
    }
    return new Path(pts)
  }
  static arc(cx, cy, r, a0, a1, n = 96) {
    const pts = []
    for (let i = 0; i <= n; i++) {
      const a = lerp(a0, a1, i / n)
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)])
    }
    return new Path(pts)
  }
  static rect(x, y, w, h, r = 0) {
    const pts = []
    const corner = (cx, cy, a0) => {
      for (let i = 0; i <= 8; i++) {
        const a = a0 + (Math.PI / 2) * (i / 8)
        pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)])
      }
    }
    corner(x + w - r, y + r, -Math.PI / 2)
    corner(x + w - r, y + h - r, 0)
    corner(x + r, y + h - r, Math.PI / 2)
    corner(x + r, y + r, Math.PI)
    return new Path(pts, true)
  }
  static wave(x0, x1, y, amp, periods, phase = 0, n = 160) {
    const pts = []
    for (let i = 0; i <= n; i++) {
      const t = i / n
      pts.push([lerp(x0, x1, t), y + amp * Math.sin(phase + t * periods * Math.PI * 2)])
    }
    return new Path(pts)
  }
}

// Draws `paths` one after another as a single pen, the fraction `p` of their total length.
// Returns the pen's tip (or null when nothing is being drawn).
export function ink(ctx, paths, p, { width = LW, color = C.gold, alpha = 1 } = {}) {
  if (p <= 0 || !paths.length) return null
  const total = paths.reduce((s, q) => s + q.length, 0)
  let left = clamp(p) * total
  let tip = null
  ctx.save()
  ctx.globalAlpha *= alpha
  ctx.strokeStyle = color
  ctx.lineWidth = width / scaleOf(ctx)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  for (const q of paths) {
    if (left <= 0) break
    const f = Math.min(1, left / (q.length || 1))
    ctx.beginPath()
    q.trace(ctx, 0, f)
    ctx.stroke()
    if (f < 1) tip = q.at(f)
    left -= q.length
  }
  ctx.restore()
  return p < 1 ? tip : null
}

export function scaleOf(ctx) {
  const m = ctx.getTransform()
  return Math.hypot(m.a, m.b) || 1
}

// --- type ----------------------------------------------------------------------------------

export const SERIF = 'Cormorant Garamond'
export const HEBREW = 'Frank Ruhl Libre'
export const MONO = 'JetBrains Mono'

export function text(ctx, s, x, y, o = {}) {
  const { font = SERIF, size = 40, weight = 500, color = C.gold, alpha = 1, align = 'center',
    spacing = 0, baseline = 'alphabetic', rtl = false } = o
  if (alpha <= 0) return 0
  ctx.save()
  ctx.globalAlpha *= alpha
  ctx.fillStyle = color
  ctx.font = `${weight} ${size}px "${font}"`
  ctx.textAlign = align
  ctx.textBaseline = baseline
  ctx.direction = rtl ? 'rtl' : 'ltr'
  ctx.letterSpacing = `${spacing}px`
  ctx.fillText(s, x, y)
  const w = ctx.measureText(s).width
  ctx.restore()
  return w
}

// small capitals label, wide tracking: the films' captions
export function label(ctx, s, x, y, alpha = 1, o = {}) {
  return text(ctx, s.toUpperCase(), x, y, { size: 22, weight: 600, spacing: 6, alpha, ...o })
}

// Lays out Hebrew words right to left from `right`; returns [{word, x0, x1}] (x0 < x1).
export function hebrewWords(ctx, words, right, { size = 72, weight = 400, font = HEBREW, gap = null } = {}) {
  ctx.save()
  ctx.font = `${weight} ${size}px "${font}"`
  ctx.direction = 'rtl'
  const space = gap ?? ctx.measureText(' ').width * 1.4
  let x = right
  const out = []
  for (const w of words) {
    const width = ctx.measureText(w).width
    out.push({ word: w, x0: x - width, x1: x })
    x -= width + space
  }
  ctx.restore()
  return out
}

// Glyph outlines from an opentype.js font, as closed Paths (one per contour), and the Path2D
// to fill them. Hebrew is laid out by reversing the letters (no niqqud: no shaping needed).
export function glyphs(font, s, x, y, size, { align = 'center', rtl = false } = {}) {
  const str = rtl ? [...s].reverse().join('') : s
  const adv = font.getAdvanceWidth(str, size)
  const x0 = align === 'center' ? x - adv / 2 : align === 'right' ? x - adv : x
  const p = font.getPath(str, x0, y, size)
  const paths = []
  let cur = []
  let last = [0, 0]
  for (const c of p.commands) {
    if (c.type === 'M') {
      if (cur.length > 1) paths.push(new Path(cur, true))
      cur = [[c.x, c.y]]
    } else if (c.type === 'L') cur.push([c.x, c.y])
    else if (c.type === 'Q') {
      for (let i = 1; i <= 8; i++) {
        const t = i / 8
        const u = 1 - t
        cur.push([u * u * last[0] + 2 * u * t * c.x1 + t * t * c.x, u * u * last[1] + 2 * u * t * c.y1 + t * t * c.y])
      }
    } else if (c.type === 'C') {
      for (let i = 1; i <= 10; i++) {
        const t = i / 10
        const u = 1 - t
        cur.push([
          u * u * u * last[0] + 3 * u * u * t * c.x1 + 3 * u * t * t * c.x2 + t * t * t * c.x,
          u * u * u * last[1] + 3 * u * u * t * c.y1 + 3 * u * t * t * c.y2 + t * t * t * c.y,
        ])
      }
    } else if (c.type === 'Z') {
      if (cur.length > 1) paths.push(new Path(cur, true))
      cur = []
    }
    if (c.x !== undefined) last = [c.x, c.y]
  }
  if (cur.length > 1) paths.push(new Path(cur, true))
  return { paths, fill: new Path2D(p.toPathData(2)), width: adv }
}

// A glyph run drawn by the pen, then filled from its outline (line to fill).
export function traced(ctx, g, draw, fill, alpha = 1) {
  const tip = ink(ctx, g.paths, draw, { alpha })
  if (fill > 0) {
    ctx.save()
    ctx.globalAlpha *= alpha * fill
    ctx.fillStyle = C.gold
    ctx.fill(g.fill)
    ctx.restore()
  }
  return tip
}

// --- numbers ---------------------------------------------------------------------------------

export const fmt = (n) => Math.round(n).toLocaleString('en-US')

const ONES = ['', 'א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט']
const TENS = ['', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ']
export function numeral(n) {
  let out = ''
  for (const [v, l] of [[400, 'ת'], [300, 'ש'], [200, 'ר'], [100, 'ק']]) {
    while (n >= v) { out += l; n -= v }
  }
  if (n === 15) return `${out}טו`
  if (n === 16) return `${out}טז`
  return out + TENS[Math.floor(n / 10)] + ONES[n % 10]
}

// verse-ending sof pasuq and the te'amim: kept for display, removed for layout by word
export const stripAccents = (s) => s.replace(/[֑-ֽ֯]/g, '')
