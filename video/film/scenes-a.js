// Film A, "Every verse, every echo": one function per scene of video/script/a-general.yaml.
// g.L is the glowing line layer, g.P the plain layer (captures); s.u is the time since the scene
// began and s.cue(i) when its i-th narration line starts (both in seconds, scene-local).

import {
  C, HEBREW, MONO, Path, clamp, ease, fmt, gold, glyphs, hebrewWords, hot, ink, label, lerp, rng, smooth, span,
  stripAccents, text, traced, window_,
} from './lib.js'

const memo = new Map()
const once = (key, make) => {
  if (!memo.has(key)) memo.set(key, make())
  return memo.get(key)
}

// --- hook: ב, then a verse field and its echoes --------------------------------------------------

const FIELD = { cx: 960, cy: 500, r: 400 }
function fieldPoints(n) {
  return once('field', () => {
    const golden = Math.PI * (3 - Math.sqrt(5))
    const pts = new Float32Array(n * 2)
    for (let i = 0; i < n; i++) {
      const r = FIELD.r * Math.sqrt((i + 0.5) / n)
      const a = i * golden
      pts[2 * i] = FIELD.cx + r * Math.cos(a)
      pts[2 * i + 1] = FIELD.cy + r * Math.sin(a)
    }
    return pts
  })
}

// The three parts of the canon: canon order runs outward, so each part ends on a ring. Each
// ring is named at the right, with a leader from where it crosses the leader's angle.
function sectionRings(g, s, field, n) {
  const { L } = g
  const sections = [['Torah', 'תורה', -0.5], ["Nevi'im", 'נביאים', -0.12], ['Ketuvim', 'כתובים', 0.28]]
  const a = smooth(s.u, 4.4, 5.4) * (1 - smooth(s.u, s.cue(1) + 0.4, s.cue(1) + 1.4))
  if (a <= 0) return
  sections.forEach(([sec, he, angle], k) => {
    const last = field.books.filter((b) => b.section === sec).at(-1)
    const end = field.books[field.books.indexOf(last) + 1]?.start ?? n
    const r = FIELD.r * Math.sqrt(end / n) + 4
    const p = smooth(s.u, 4.4 + k * 0.3, 5.4 + k * 0.3)
    ink(L, [Path.arc(FIELD.cx, FIELD.cy, r, -Math.PI / 2, Math.PI * 1.5)], p, { width: 1.6, color: C.hot, alpha: a })
    const x0 = FIELD.cx + r * Math.cos(angle)
    const y0 = FIELD.cy + r * Math.sin(angle)
    const y1 = FIELD.cy - 150 + k * 110
    ink(L, [Path.poly([[x0, y0], [FIELD.cx + FIELD.r + 60, y1], [FIELD.cx + FIELD.r + 110, y1]])], p, { width: 1.2, alpha: a * 0.8 })
    text(L, he, FIELD.cx + FIELD.r + 124, y1 + 12, { font: HEBREW, size: 36, align: 'left', alpha: a * p })
  })
}

function hook(g, s) {
  const { L } = g
  const { field } = g.data
  const n = field.n
  const pts = fieldPoints(n)
  const bet = once('bet', () => glyphs(g.fonts.hebrew, 'ב', 960, 700, 520))
  // the letter: drawn, filled, then it gives way to the field
  const fade = 1 - smooth(s.u, 2.3, 3.2)
  if (fade > 0) g.tip(traced(L, bet, smooth(s.u, -0.4, 1.5), smooth(s.u, 1.4, 2.0) * 0.85, fade))
  g.camera(lerp(1.06, 1, smooth(s.u, 0, 5)))
  // the verses in canon order, spiralling out from the centre
  const d = smooth(s.u, 2.0, 5.0)
  const shown = Math.floor(d * n)
  L.save()
  L.fillStyle = gold(0.55)
  for (let i = 0; i < shown; i++) L.fillRect(pts[2 * i] - 1.1, pts[2 * i + 1] - 1.1, 2.2, 2.2)
  L.fillStyle = hot(0.9)
  for (let i = Math.max(0, shown - 400); i < shown; i++) L.fillRect(pts[2 * i] - 1.4, pts[2 * i + 1] - 1.4, 2.8, 2.8)
  L.restore()
  sectionRings(g, s, field, n)
  // the count
  const count = fmt(Math.min(n, shown))
  text(L, count, FIELD.cx, 1000, { size: 64, weight: 500, alpha: smooth(s.u, 2.2, 2.8), spacing: 2 })
  label(L, 'verses · פסוקים', FIELD.cx, 1040, smooth(s.u, 2.6, 3.2) * 0.8)
  // echoes: arcs between verses that match across books, growing in
  const a0 = s.cue(1) - 0.2
  const arcs = field.arcs
  const grow = span(s.u, a0, a0 + 3.6)
  const pulse = Math.exp(-(((s.u - s.cue(2) - 0.8) / 0.7) ** 2))
  L.save()
  L.lineCap = 'round'
  for (let k = 0; k < arcs.length; k++) {
    const start = (k / arcs.length) * 0.85
    const p = clamp((grow - start) / 0.15)
    if (p <= 0) break
    const [a, b] = arcs[k]
    const p0 = [pts[2 * a], pts[2 * a + 1]]
    const p2 = [pts[2 * b], pts[2 * b + 1]]
    const mid = [lerp(p0[0], p2[0], 0.5), lerp(p0[1], p2[1], 0.5)]
    const ctrl = [lerp(mid[0], FIELD.cx, 0.55), lerp(mid[1], FIELD.cy, 0.55)]
    const q = Path.quad(p0, ctrl, p2, 18)
    L.strokeStyle = k < 300 ? hot(0.2 + 0.5 * pulse) : gold(0.16 + 0.4 * pulse)
    L.lineWidth = 1.1
    L.beginPath()
    q.trace(L, 0, ease(p))
    L.stroke()
  }
  L.restore()
}

// --- the question: parallels, then the size of the search ------------------------------------------

function columns(L, x, ys, p, { tick = 18, alpha = 1 } = {}) {
  const top = ys[0]
  const bottom = ys.at(-1)
  ink(L, [Path.line(x, top - 20, x, bottom + 20)], p, { width: 1.5, alpha: 0.5 * alpha })
  L.save()
  L.strokeStyle = gold(0.9 * alpha)
  L.lineWidth = 2
  L.lineCap = 'round'
  ys.forEach((y, i) => {
    const q = clamp(p * ys.length - i)
    if (q <= 0) return
    L.beginPath()
    L.moveTo(x - (tick / 2) * q, y)
    L.lineTo(x + (tick / 2) * q, y)
    L.stroke()
  })
  L.restore()
}

function question(g, s) {
  const { L } = g
  const { pairs, numbers } = g.data
  // left: Psalm 14 against Psalm 53
  const leftA = window_(s.u, s.cue(1) - 0.3, s.cue(4) + 0.4, 0.6, 0.8)
  const yA = pairs.ps14.map((_, i) => 330 + i * 64)
  const yB = pairs.ps53.map((_, i) => 330 + i * 64)
  const xa = 360
  const xb = 720
  if (leftA > 0) {
    columns(L, xa, yA, smooth(s.u, s.cue(1), s.cue(1) + 1.2), { alpha: leftA })
    columns(L, xb, yB, smooth(s.u, s.cue(1) + 0.3, s.cue(1) + 1.5), { alpha: leftA })
    text(L, 'תהלים יד', xa, 270, { font: HEBREW, size: 40, alpha: leftA * smooth(s.u, s.cue(1), s.cue(1) + 0.6) })
    text(L, 'תהלים נג', xb, 270, { font: HEBREW, size: 40, alpha: leftA * smooth(s.u, s.cue(1) + 0.3, s.cue(1) + 0.9) })
    const links = pairs.ps14_53.map(([a, b]) => {
      const i = pairs.ps14.indexOf(a)
      const j = pairs.ps53.indexOf(b)
      return Path.cubic([xa + 14, yA[i]], [xa + 160, yA[i]], [xb - 160, yB[j]], [xb - 14, yB[j]])
    })
    links.forEach((q, k) => {
      const p = smooth(s.u, s.cue(1) + 1.2 + k * 0.18, s.cue(1) + 2.0 + k * 0.18)
      g.tip(ink(L, [q], p, { alpha: leftA, color: C.hot }))
    })
    const v = pairs.text.ps14_1
    text(L, v.he, 540, 860, { font: HEBREW, size: 30, alpha: leftA * 0.85 * smooth(s.u, s.cue(1) + 2, s.cue(1) + 3), rtl: true })
  }
  // right: II Samuel 22 against Psalm 18, all 51 verses
  const right = window_(s.u, s.cue(2) - 0.3, s.cue(4) + 0.4, 0.6, 0.8)
  if (right > 0) {
    const x1 = 1200
    const x2 = 1580
    const ys = pairs.sam22.map((_, i) => 250 + i * 11.6)
    columns(L, x1, ys, smooth(s.u, s.cue(2), s.cue(2) + 1.6), { tick: 14, alpha: right })
    columns(L, x2, ys, smooth(s.u, s.cue(2) + 0.3, s.cue(2) + 1.9), { tick: 14, alpha: right })
    text(L, 'שמואל ב כב', x1, 205, { font: HEBREW, size: 36, alpha: right })
    text(L, 'תהלים יח', x2, 205, { font: HEBREW, size: 36, alpha: right })
    const done = smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 2.4)
    const k = Math.floor(done * pairs.sam_ps.length)
    L.save()
    L.strokeStyle = hot(0.55 * right)
    L.lineWidth = 1.2
    pairs.sam_ps.slice(0, k).forEach(([a, b]) => {
      const i = a - pairs.sam22[0]
      const j = b - pairs.ps18[0]
      L.beginPath()
      L.moveTo(x1 + 10, ys[i])
      L.bezierCurveTo(x1 + 140, ys[i], x2 - 140, ys[j], x2 - 10, ys[j])
      L.stroke()
    })
    L.restore()
    text(L, `${k} / ${pairs.sam22.length}`, (x1 + x2) / 2, 900, { size: 56, alpha: right * smooth(s.u, s.cue(3), s.cue(3) + 0.5) })
  }
  // the viewer's Compare page
  const dev = window_(s.u, s.cue(4) - 0.2, s.cue(5) + 0.3, 0.1, 0.6)
  if (dev > 0) {
    L.save()
    L.globalAlpha = dev
    g.P.globalAlpha = dev
    g.device(260, 120, 1400, 800, smooth(s.u, s.cue(4) - 0.2, s.cue(4) + 1.1), 'compare', s.u - s.cue(4))
    L.restore()
  }
  // quieter echoes: three kinds, in line
  const quiet = window_(s.u, s.cue(5) + 0.3, s.cue(7) + 0.2, 0.5, 0.6)
  if (quiet > 0) {
    const items = [
      ['a borrowed phrase', (x, y, p) => ink(L, [Path.line(x - 90, y, x - 20, y), Path.line(x + 20, y, x + 90, y), Path.quad([x - 55, y - 4], [x, y - 60], [x + 55, y - 4])], p)],
      ['a scene told again', (x, y, p) => ink(L, [Path.rect(x - 95, y - 40, 80, 80, 8), Path.rect(x + 15, y - 40, 80, 80, 8), Path.line(x - 15, y, x + 15, y)], p)],
      ['a rare word, back again', (x, y, p) => ink(L, [Path.arc(x, y, 34, -Math.PI / 2, Math.PI * 1.5), Path.line(x, y - 70, x, y - 46), Path.line(x, y + 46, x, y + 70)], p)],
    ]
    items.forEach(([name, draw], k) => {
      const x = 480 + k * 480
      const p = smooth(s.u, s.cue(6) + k * 0.9, s.cue(6) + k * 0.9 + 1.2)
      L.save()
      L.globalAlpha = quiet
      g.tip(draw(x, 470, p))
      label(L, name, x, 600, smooth(s.u, s.cue(6) + k * 0.9 + 0.6, s.cue(6) + k * 0.9 + 1.2))
      L.restore()
    })
  }
  // every verse against every other: the grid
  const grid = smooth(s.u, s.cue(7) - 0.1, s.cue(7) + 0.5)
  if (grid > 0) {
    const n = numbers.rows.verses
    const x0 = 960 - 260
    const y0 = 170
    const size = 520
    const paths = [Path.rect(x0, y0, size, size, 0)]
    for (let i = 1; i < 26; i++) {
      paths.push(Path.line(x0, y0 + (i * size) / 26, x0 + size, y0 + (i * size) / 26))
      paths.push(Path.line(x0 + (i * size) / 26, y0, x0 + (i * size) / 26, y0 + size))
    }
    const p = smooth(s.u, s.cue(7), s.cue(7) + 2.6)
    ink(L, paths.slice(0, 1), clamp(p * 3), { alpha: grid })
    ink(L, paths.slice(1), clamp(p * 1.4 - 0.3), { width: 1, alpha: grid * 0.45 })
    ink(L, [Path.line(x0, y0, x0 + size, y0 + size)], clamp(p * 2 - 0.8), { alpha: grid, color: C.hot })
    text(L, `${fmt(n)} × ${fmt(n)}`, 960, 790, { size: 54, alpha: grid * smooth(s.u, s.cue(7) + 1, s.cue(7) + 1.6), spacing: 2 })
  }
  label(L, 'which passages are alike?', 960, 110, window_(s.u, 0, s.cue(1) + 1.5, 0.6, 0.6) * 0.9)
}

// --- three lenses ---------------------------------------------------------------------------

function lenses(g, s) {
  const { L } = g
  const icons = window_(s.u, 0, s.cue(5) + 0.4, 0.4, 0.7)
  const y = 420
  // words: two lines of word-bars, the shared ones joined
  if (icons > 0) {
    L.save()
    L.globalAlpha = icons
    const p1 = smooth(s.u, s.cue(1) - 0.2, s.cue(1) + 1.4)
    const xs = [380, 440, 520, 575]
    const top = xs.map((x, i) => Path.line(x, y - 40, x + (i % 2 ? 40 : 60), y - 40))
    const bot = [390, 470, 515, 590].map((x, i) => Path.line(x, y + 40, x + (i % 2 ? 50 : 35), y + 40))
    g.tip(ink(L, [...top, ...bot], p1))
    ink(L, [Path.line(410, y - 32, 405, y + 32), Path.line(600, y - 32, 610, y + 32)], smooth(s.u, s.cue(1) + 1.0, s.cue(1) + 1.8), { color: C.hot })
    label(L, 'words', 480, y + 130, smooth(s.u, s.cue(1) + 0.5, s.cue(1) + 1.1))
    text(L, 'מילים', 480, y + 175, { font: HEBREW, size: 30, alpha: smooth(s.u, s.cue(1) + 0.7, s.cue(1) + 1.3) * 0.8 })
    // meaning: one idea as a wave, two different shapes on it
    const p2 = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 1.6)
    g.tip(ink(L, [Path.wave(860, 1060, y, 34, 1.5, 0)], p2))
    L.fillStyle = hot(smooth(s.u, s.cue(2) + 1.2, s.cue(2) + 1.6))
    for (const [x, yy] of [[880, y - 20], [1040, y + 20]]) {
      L.beginPath()
      L.arc(x, yy, 7, 0, Math.PI * 2)
      L.fill()
    }
    label(L, 'meaning', 960, y + 130, smooth(s.u, s.cue(2) + 0.5, s.cue(2) + 1.1))
    text(L, 'משמעות', 960, y + 175, { font: HEBREW, size: 30, alpha: smooth(s.u, s.cue(2) + 0.7, s.cue(2) + 1.3) * 0.8 })
    // both: the two braided
    const p3 = smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 1.6)
    g.tip(ink(L, [Path.wave(1340, 1540, y, 30, 2, 0)], p3))
    ink(L, [Path.wave(1340, 1540, y, 30, 2, Math.PI)], p3, { color: C.hot })
    label(L, 'both together', 1440, y + 130, smooth(s.u, s.cue(3) + 0.5, s.cue(3) + 1.1))
    text(L, 'שניהם יחד', 1440, y + 175, { font: HEBREW, size: 30, alpha: smooth(s.u, s.cue(3) + 0.7, s.cue(3) + 1.3) * 0.8 })
    // subtler lenses
    const p4 = smooth(s.u, s.cue(4), s.cue(4) + 2.2)
    const yy = 790
    const at = [600, 960, 1320]
    const [a, b, c] = at
    const small = [
      ['grammar', [Path.line(a, yy - 30, a, yy), Path.line(a, yy, a - 30, yy + 30), Path.line(a, yy, a + 30, yy + 30)]],
      ['fields of meaning', [Path.arc(b - 15, yy, 28, 0, Math.PI * 2, 48), Path.arc(b + 15, yy, 28, 0, Math.PI * 2, 48)]],
      ['clauses built alike', [Path.poly([[c - 20, yy - 30], [c - 34, yy - 30], [c - 34, yy + 30], [c - 20, yy + 30]]), Path.poly([[c + 20, yy - 30], [c + 34, yy - 30], [c + 34, yy + 30], [c + 20, yy + 30]])]],
    ]
    small.forEach(([name, paths], k) => {
      const q = clamp(p4 * 3 - k)
      ink(L, paths, q, { width: 2, alpha: 0.85 })
      label(L, name, at[k], yy + 72, q * 0.7, { size: 18 })
    })
    L.restore()
  }
  const dev = smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 0.4)
  if (dev > 0) g.device(260, 120, 1400, 800, smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 1.2), 'unit', s.u - s.cue(5))
  label(L, 'more than one way to read', 960, 110, window_(s.u, 0, s.cue(5), 0.6, 0.6) * 0.9)
}

// --- told twice: Samuel–Kings against Chronicles ------------------------------------------------

function toldTwice(g, s) {
  const { L } = g
  const { retold } = g.data
  const b = retold.books
  const x0 = 170
  const x1 = 1750
  const topBooks = ['I Samuel', 'II Samuel', 'I Kings', 'II Kings']
  const botBooks = ['I Chronicles', 'II Chronicles']
  const topFirst = b['I Samuel'].first
  const topLast = b['II Kings'].last
  const botFirst = b['I Chronicles'].first
  const botLast = b['II Chronicles'].last
  const xt = (v) => lerp(x0, x1, (v - topFirst) / (topLast - topFirst))
  const xb = (v) => lerp(x0 + 180, x1 - 180, (v - botFirst) / (botLast - botFirst))
  const yt = 330
  const yb = 690
  const bands = window_(s.u, 0, s.cue(3) + 0.3, 0.4, 0.6)
  if (bands > 0) {
    L.save()
    L.globalAlpha = Math.min(1, bands)
    const p = smooth(s.u, s.cue(1) - 0.4, s.cue(1) + 1.6)
    g.tip(ink(L, [Path.line(x0, yt, x1, yt)], p))
    ink(L, [Path.line(xb(botFirst), yb, xb(botLast), yb)], smooth(s.u, s.cue(1), s.cue(1) + 1.8))
    const he = { 'I Samuel': 'שמואל א', 'II Samuel': 'שמואל ב', 'I Kings': 'מלכים א', 'II Kings': 'מלכים ב', 'I Chronicles': 'דברי הימים א', 'II Chronicles': 'דברי הימים ב' }
    for (const name of topBooks) {
      const xs = xt(b[name].first)
      ink(L, [Path.line(xs, yt - 14, xs, yt + 14)], p)
      text(L, he[name], (xs + xt(b[name].last)) / 2, yt - 36, { font: HEBREW, size: 30, alpha: p * 0.9 })
    }
    for (const name of botBooks) {
      const xs = xb(b[name].first)
      ink(L, [Path.line(xs, yb - 14, xs, yb + 14)], p)
      text(L, he[name], (xs + xb(b[name].last)) / 2, yb + 58, { font: HEBREW, size: 30, alpha: p * 0.9 })
    }
    // the parallel runs found, beyond chance
    const runs = retold.runs
    runs.forEach((r, k) => {
      const q = smooth(s.u, s.cue(2) + k * 0.12, s.cue(2) + k * 0.12 + 0.9)
      if (q <= 0) return
      L.save()
      L.globalAlpha *= q
      L.fillStyle = gold(0.12)
      L.beginPath()
      L.moveTo(xt(r.a), yt + 4)
      L.lineTo(xt(r.a_end), yt + 4)
      L.lineTo(xb(r.b_end), yb - 4)
      L.lineTo(xb(r.b), yb - 4)
      L.closePath()
      L.fill()
      L.restore()
      ink(L, [Path.line(xt(r.a), yt + 4, xb(r.b), yb - 4)], q, { width: 1.4, color: C.hot, alpha: 0.8 })
    })
    label(L, `${runs.length} parallel runs, beyond chance`, 960, 860, smooth(s.u, s.cue(2) + 1.5, s.cue(2) + 2.2) * 0.85)
    L.restore()
  }
  const dev = window_(s.u, s.cue(3) - 0.2, s.cue(4) + 0.4, 0.1, 0.6)
  if (dev > 0) {
    L.save()
    L.globalAlpha = dev
    g.P.globalAlpha = dev
    g.device(260, 120, 1400, 800, smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 1.0), 'synopses', s.u - s.cue(3))
    L.restore()
  }
  // the changes, word by word; then which side is later
  const ch = window_(s.u, s.cue(4) + 0.3, s.dur + 2, 0.5, 0.2)
  if (ch > 0) {
    L.save()
    L.globalAlpha = ch
    const top = [0, 1, 2, 3, 4, 5]
    const bot = [0, 1, 'changed', 3, 'added', 5]
    const p = smooth(s.u, s.cue(4) + 0.4, s.cue(4) + 2.2)
    const w = 120
    const gap = 26
    const left = 960 - (6 * w + 5 * gap) / 2
    top.forEach((k, i) => {
      if (i === 4) return // left out of the other
      ink(L, [Path.rect(left + i * (w + gap), 430, w, 50, 8)], clamp(p * 2 - i * 0.15), { width: 2 })
    })
    bot.forEach((k, i) => {
      const hotBox = typeof k === 'string'
      ink(L, [Path.rect(left + i * (w + gap), 560, w, 50, 8)], clamp(p * 2 - i * 0.15), { width: hotBox ? 3 : 2, color: hotBox ? C.hot : C.gold })
    })
    label(L, 'changed', left + 2 * (w + gap) + w / 2, 650, p, { size: 18 })
    label(L, 'added', left + 4 * (w + gap) + w / 2, 650, p, { size: 18 })
    label(L, 'left out', left + 4 * (w + gap) + w / 2, 410, p * 0.8, { size: 18 })
    // later or earlier
    const d = smooth(s.u, s.cue(5) - 0.2, s.cue(5) + 1.2)
    ink(L, [Path.line(660, 790, 1250, 790), Path.poly([[1225, 772], [1255, 790], [1225, 808]])], d, { color: C.hot })
    label(L, 'earlier', 600, 798, d, { align: 'right' })
    label(L, 'later', 1300, 798, d, { align: 'left' })
    text(L, '30 / 35', 960, 900, { size: 60, alpha: smooth(s.u, s.cue(6), s.cue(6) + 0.6) })
    label(L, 'known directions found', 960, 945, smooth(s.u, s.cue(6) + 0.3, s.cue(6) + 0.9) * 0.8)
    L.restore()
  }
  label(L, 'told twice', 960, 110, window_(s.u, 0, s.cue(3), 0.6, 0.6) * 0.9)
}

// --- the reader ---------------------------------------------------------------------------------

function reader(g, s) {
  const { L } = g
  const v = g.data.verses.gen3_9
  // set without the te'amim (the font places them poorly); the atnah is found in the original
  const marked = once('reader-marked', () => v.he.replace('׃', '').split(' '))
  const words = once('reader-words', () => marked.map(stripAccents))
  const size = 78
  const right = 1600
  const boxes = hebrewWords(L, words, right, { size })
  const total = boxes[0].x1 - boxes.at(-1).x0
  const shift = (1600 - 320 - total) / 2 // centre the line
  const y = 500
  const show = window_(s.u, 0, s.cue(5) + 0.4, 0.5, 0.6)
  if (show > 0) {
    L.save()
    L.globalAlpha = show
    L.translate(-shift, 0)
    boxes.forEach((b, i) => {
      const a = smooth(s.u, 0.3 + i * 0.12, 0.9 + i * 0.12)
      text(L, b.word, b.x1, y, { font: HEBREW, size, alpha: a, align: 'right', rtl: true, weight: 400 })
    })
    // who speaks, to whom: the spoken word, and an arc from the speaker to the addressee
    const said = boxes.at(-1)
    const p = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 1.2)
    const god = boxes[1]
    const adam = boxes[3]
    g.tip(ink(L, [Path.quad([god.x0 + (god.x1 - god.x0) / 2, y - 80], [(god.x1 + adam.x0) / 2, y - 190], [adam.x0 + (adam.x1 - adam.x0) / 2, y - 80])], p, { color: C.hot }))
    ink(L, [Path.rect(said.x0 - 14, y - 82, said.x1 - said.x0 + 28, 112, 12)], smooth(s.u, s.cue(2) + 0.8, s.cue(2) + 1.8))
    label(L, 'speaker → addressee', (god.x1 + adam.x0) / 2, y - 210, p * 0.8, { size: 18 })
    // the two halves of the verse, at the atnah
    const atnah = marked.findIndex((w) => w.includes('֑'))
    const cut = atnah >= 0 ? boxes[atnah].x0 - 22 : null
    const ph = smooth(s.u, s.cue(3) + 1.2, s.cue(3) + 2.2)
    if (cut) {
      g.tip(ink(L, [Path.line(cut, y - 110, cut, y + 60)], ph, { color: C.hot }))
      text(L, 'צלע א', (boxes[0].x1 + cut) / 2, y + 110, { font: HEBREW, size: 30, alpha: ph * 0.85 })
      text(L, 'צלע ב', (cut + boxes.at(-1).x0) / 2, y + 110, { font: HEBREW, size: 30, alpha: ph * 0.85 })
    }
    L.restore()
    // the layers, each on its own channel, switched on one after another
    const yy = 800
    const layers = [
      ['speakers', (x, a) => {
        L.fillStyle = gold(0.35 * a)
        L.beginPath()
        L.roundRect(x - 34, yy - 16, 68, 32, 6)
        L.fill()
      }],
      ['key words', (x, a) => ink(L, [Path.line(x - 34, yy, x + 34, yy)], a, { width: 8 })],
      ['verse halves', (x, a) => ink(L, [Path.line(x, yy - 24, x, yy + 24)], a, { color: C.hot })],
      ['wordplay', (x, a) => ink(L, [Path.rect(x - 34, yy - 18, 68, 36, 6)], a, { width: 2 })],
      ['rare words', (x, a) => {
        ink(L, [Path.line(x - 30, yy + 10, x + 30, yy + 10)], a, { width: 2, alpha: 0.6 })
        L.fillStyle = hot(a)
        L.beginPath()
        L.arc(x, yy - 12, 5, 0, Math.PI * 2)
        L.fill()
      }],
    ]
    layers.forEach(([name, swatch], k) => {
      const t0 = [s.cue(2), s.cue(3), s.cue(3) + 1.2, s.cue(4), s.cue(4) + 1.0][k]
      const a = smooth(s.u, t0, t0 + 0.6)
      const x = 360 + k * 300
      L.save()
      L.globalAlpha = show
      swatch(x, a)
      label(L, name, x, 862, a * 0.85, { size: 18 })
      L.restore()
    })
  }
  const dev = smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 0.4)
  if (dev > 0) g.device(260, 120, 1400, 800, smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 1.2), 'reader', s.u - s.cue(5))
  label(L, 'the reader', 960, 110, window_(s.u, 0, s.cue(5), 0.6, 0.6) * 0.9)
  text(L, v.ref.replace('Genesis', 'Gen.'), 960, 640, { size: 26, alpha: show * 0.6, spacing: 2 })
}

// --- poetry ---------------------------------------------------------------------------------------

const ALEF_BET = 'אבגדהוזחטיכלמנסעפצקרשת'

function music(g, s) {
  const { L } = g
  // the verse split at its main pause
  const v = g.data.verses.lam3_1
  const marked = v.he.replace('׃', '').split(' ')
  const words = marked.map(stripAccents)
  const pause = marked.findIndex((w) => /[֑֔]/.test(w)) // atnah, else zaqef
  const top = window_(s.u, 0, s.cue(2) + 0.2, 0.5, 0.6)
  if (top > 0) {
    const boxes = hebrewWords(L, words, 1420, { size: 64 })
    L.save()
    L.globalAlpha = top
    boxes.forEach((b) => text(L, b.word, b.x1, 420, { font: HEBREW, size: 64, align: 'right', rtl: true, alpha: smooth(s.u, 0.2, 0.9) }))
    if (pause >= 0) {
      const cut = boxes[pause].x0 - 20
      const p = smooth(s.u, s.cue(1) + 0.4, s.cue(1) + 1.6)
      g.tip(ink(L, [Path.line(cut, 330, cut, 460)], p, { color: C.hot }))
      ink(L, [Path.line(boxes[0].x1, 490, cut + 10, 490)], smooth(s.u, s.cue(1) + 1.4, s.cue(1) + 2.4), { width: 2 })
      ink(L, [Path.line(cut - 10, 490, boxes.at(-1).x0, 490)], smooth(s.u, s.cue(1) + 2.0, s.cue(1) + 3.0), { width: 2 })
      text(L, 'טעמי המקרא', 960, 600, { font: HEBREW, size: 30, alpha: smooth(s.u, s.cue(1) + 1, s.cue(1) + 1.6) * 0.8 })
    }
    text(L, v.ref.replace('Lamentations', 'Lam.'), 960, 250, { size: 26, alpha: 0.6, spacing: 2 })
    L.restore()
  }
  // the acrostic: the alphabet, one rung each, right to left
  const acro = window_(s.u, s.cue(2) - 0.2, s.cue(3) + 0.2, 0.4, 0.6)
  if (acro > 0) {
    L.save()
    L.globalAlpha = acro
    const p = smooth(s.u, s.cue(2), s.cue(2) + 3.0)
    const x0 = 1740
    const step = (1740 - 180) / 21
    const ladder = []
    for (let i = 0; i < 22; i++) {
      const x = x0 - i * step
      ladder.push(Path.line(x, 560, x, 610))
      if (i < 21) ladder.push(Path.line(x, 610, x - step, 610))
    }
    g.tip(ink(L, ladder, p))
    const missing = 16 // one letter lost: a broken acrostic
    for (let i = 0; i < 22; i++) {
      const a = clamp(p * 22 - i)
      const lost = smooth(s.u, s.cue(2) + 3.2, s.cue(2) + 3.8)
      text(L, ALEF_BET[i], x0 - i * step, 530, { font: HEBREW, size: 52, alpha: a * (i === missing ? 1 - 0.8 * lost : 1) })
    }
    label(L, 'א – ת', 960, 700, p * 0.8)
    L.restore()
  }
  // three beats, then two: the lament's falling line
  const meter = smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 0.4)
  if (meter > 0) {
    L.save()
    L.globalAlpha = meter
    const beats = []
    const y = 560
    const fall = smooth(s.u, s.cue(4), s.cue(4) + 1.5)
    let x = 480
    for (let i = 0; i < 3; i++) {
      beats.push(Path.quad([x, y], [x + 70, y - 90], [x + 140, y]))
      x += 160
    }
    x += 60
    for (let i = 0; i < 2; i++) {
      const dy = fall * (40 + i * 30)
      beats.push(Path.quad([x, y + dy], [x + 60, y - 60 + dy], [x + 120, y + dy]))
      x += 140
    }
    const p = smooth(s.u, s.cue(3), s.cue(3) + 2.4)
    g.tip(ink(L, beats, p))
    text(L, '3', 720, 700, { size: 64, alpha: smooth(s.u, s.cue(3) + 0.8, s.cue(3) + 1.3) })
    text(L, ':', 900, 700, { size: 64, alpha: smooth(s.u, s.cue(3) + 1.6, s.cue(3) + 2.0) })
    text(L, '2', 1090, 700, { size: 64, alpha: smooth(s.u, s.cue(3) + 2.0, s.cue(3) + 2.5) })
    text(L, 'קינה', 960, 820, { font: HEBREW, size: 44, alpha: fall * 0.9 })
    L.restore()
  }
  label(L, 'the music of the verse', 960, 110, window_(s.u, 0, s.dur, 0.6, 0.6) * 0.9)
}

// --- the hero: people, places, time -------------------------------------------------------------

function people(g, s) {
  const { L } = g
  const { tree, land, chrono } = g.data
  const treeEnd = s.cue(4) - 0.2
  // the tree, right to left: Adam at the right, David at the left
  const T = window_(s.u, -0.4, treeEnd + 0.4, 0.4, 0.8)
  if (T > 0) {
    const n = tree.line.length
    const x0 = 1780
    const x1 = 140
    const y = 520
    const xs = tree.line.map((_, i) => lerp(x0, x1, i / (n - 1)))
    const draw = smooth(s.u, 0.3, s.cue(3) + 1.2)
    const tipX = lerp(x0, x1, draw)
    const zoom = lerp(2.0, 1.0, smooth(s.u, s.cue(2), s.cue(3) + 2.0))
    const camX = lerp(tipX, 960, smooth(s.u, s.cue(2), s.cue(3) + 2.0))
    g.camera(zoom, camX, lerp(y, 540, smooth(s.u, s.cue(2), s.cue(3) + 2)))
    L.save()
    L.globalAlpha = T
    g.tip(ink(L, [Path.line(x0, y, x1, y)], draw))
    const r = rng(3)
    tree.line.forEach((p, i) => {
      const reached = clamp((draw * (n - 1) - i) * 2 + 1)
      if (reached <= 0) return
      const x = xs[i]
      const up = i % 2 === 0
      L.fillStyle = i === 0 || i === n - 1 ? hot(reached) : gold(reached)
      L.beginPath()
      L.arc(x, y, i === 0 || i === n - 1 ? 7 : 4.5, 0, Math.PI * 2)
      L.fill()
      text(L, p.he, x, up ? y - 26 : y + 46, { font: HEBREW, size: i === 0 || i === n - 1 ? 34 : 24, alpha: reached * 0.95 })
      // proof verse under the link that leads here
      const proof = tree.proofs[i - 1]
      if (proof) {
        text(L, proof, (x + xs[i - 1]) / 2, up ? y + 88 : y - 70, { font: HEBREW, size: 13, alpha: reached * 0.55 * smooth(s.u, s.cue(2), s.cue(2) + 1) })
      }
      // children branching off the line: a stem, then their names in a short list
      const kids = tree.branches[i] ?? []
      if (kids.length) {
        const dir = up ? 1 : -1 // children go to the side away from the name
        const stem = 118
        const kq = clamp(reached * 1.5 - 0.5)
        ink(L, [Path.line(x, y + dir * 14, x, y + dir * stem)], kq, { width: 1.2, alpha: 0.6 })
        kids.forEach((k, j) => {
          const ky = y + dir * (stem + 6 + j * 19) + (dir > 0 ? 12 : 0)
          const a = clamp(kq * kids.length - j)
          ink(L, [Path.line(x, ky - 5, x + 8, ky - 5)], a, { width: 1, alpha: 0.5 })
          text(L, k.he, x + 12, ky, { font: HEBREW, size: 15, align: 'left', alpha: a * 0.7 })
          if (tree.conflicts.includes(k.id)) {
            const c = smooth(s.u, s.cue(3), s.cue(3) + 0.8)
            ink(L, [Path.arc(x - 12, ky - 5, 7, 0, Math.PI * 2, 24)], c, { color: C.hot, width: 1.6 })
          }
        })
      }
    })
    const conflict = smooth(s.u, s.cue(3) + 0.4, s.cue(3) + 1.2) * (1 - smooth(s.u, s.cue(4) - 1.2, s.cue(4) - 0.4))
    if (conflict > 0) {
      ink(L, [Path.arc(760, 950, 9, 0, Math.PI * 2, 24)], conflict, { color: C.hot, width: 1.8 })
      label(L, 'two passages disagree', 780, 958, conflict, { size: 18, align: 'left' })
    }
    label(L, 'from Adam to David · מאדם ועד דוד', 960, 900, smooth(s.u, s.cue(1), s.cue(1) + 0.8) * 0.85 * smooth(s.u, s.cue(2), s.cue(3) + 1))
    L.restore()
  }
  // the land
  const mapA = window_(s.u, treeEnd, s.cue(5) + 0.6, 0.6, 0.8)
  if (mapA > 0) {
    g.camera(1)
    const [lo0, la0, lo1, la1] = land.bbox
    const k = 900 / (la1 - la0)
    const kx = k * Math.cos((31.7 * Math.PI) / 180)
    const mx = 960 - ((lo1 - lo0) * kx) / 2
    const proj = ([lo, la]) => [mx + (lo - lo0) * kx, 990 - (la - la0) * k]
    const shapes = once('land-paths', () => land.shapes.map((sh) => ({
      layer: sh.layer, paths: sh.runs.map((r) => Path.poly(r.pts.map(proj), r.closed)),
    })))
    L.save()
    L.globalAlpha = mapA
    L.beginPath()
    L.rect(mx - 40, 70, (lo1 - lo0) * kx + 80, 940)
    L.clip()
    const p = smooth(s.u, treeEnd + 0.2, treeEnd + 3.2)
    const coast = shapes.filter((sh) => sh.layer === 'land').flatMap((sh) => sh.paths)
    g.tip(ink(L, coast, p, { width: 2.4 }))
    for (const sh of shapes.filter((x) => x.layer === 'lakes')) {
      for (const q of sh.paths) {
        ink(L, [q], p, { width: 2 })
        L.fillStyle = gold(0.22 * smooth(s.u, treeEnd + 2.4, treeEnd + 3.4))
        L.beginPath()
        q.trace(L)
        L.fill()
      }
    }
    ink(L, shapes.filter((x) => x.layer === 'rivers').flatMap((x) => x.paths), smooth(s.u, treeEnd + 1, treeEnd + 3.4), { width: 1.4, alpha: 0.7 })
    L.restore()
    // places, the best attested first; the largest named
    const pp = smooth(s.u, treeEnd + 1.6, treeEnd + 4.6)
    L.save()
    L.globalAlpha = mapA
    const named = []
    land.places.forEach((pl, i) => {
      const a = clamp(pp * land.places.length - i)
      if (a <= 0) return
      const [x, y] = proj([pl.lon, pl.lat])
      // the best attested are named, where a name does not crowd another
      const free = i < 30 && named.length < 9 && named.every(([nx, ny]) => Math.abs(nx - x) > 110 || Math.abs(ny - y) > 34)
      if (free) named.push([x, y])
      L.fillStyle = free ? hot(a) : gold(0.7 * a)
      L.beginPath()
      L.arc(x, y, free ? 4.5 : 2.6, 0, Math.PI * 2)
      L.fill()
      if (free) text(L, pl.he, x + 12, y + 7, { font: HEBREW, size: 24, align: 'left', alpha: a * 0.95 })
    })
    // a story crossing the land: I and II Samuel, a point moving from chapter to chapter
    const stops = once('story', () => land.path
      .filter((c) => c.lon >= lo0 && c.lon <= lo1 && c.lat >= la0 && c.lat <= la1)
      .map((c) => proj([c.lon, c.lat])))
    const t0 = s.cue(4) + 1.2
    const f = span(s.u, t0, s.cue(5) + 0.4) * (stops.length - 1)
    if (f > 0) {
      const k = Math.floor(f)
      const at = (j, q) => {
        const a = stops[clamp(j, 0, stops.length - 1)]
        const b = stops[clamp(j + 1, 0, stops.length - 1)]
        return [lerp(a[0], b[0], ease(q)), lerp(a[1], b[1], ease(q))]
      }
      for (let j = Math.max(0, k - 5); j <= k; j++) {
        const a = stops[j]
        const b = j === k ? at(k, f - k) : stops[j + 1]
        ink(L, [Path.line(a[0], a[1], b[0], b[1])], 1, { color: C.hot, width: 2, alpha: 0.2 + 0.8 * (1 - (k - j) / 6) })
      }
      g.tip(at(k, f - k))
    }
    label(L, 'I – II Samuel, chapter by chapter', 960, 1040, smooth(s.u, t0, t0 + 0.7) * 0.7, { size: 18 })
    L.restore()
  }
  // time: the years from Adam, read from the verses
  const timeA = smooth(s.u, s.cue(5) + 0.2, s.cue(5) + 0.9)
  if (timeA > 0) {
    g.camera(1)
    const X0 = 170
    const X1 = 1750
    const y = 600
    const maxY = 2500
    const xOf = (yr) => lerp(X0, X1, yr / maxY)
    L.save()
    L.globalAlpha = timeA
    const axis = smooth(s.u, s.cue(5) + 0.3, s.cue(5) + 2.2)
    g.tip(ink(L, [Path.line(X0, y, X1, y)], axis))
    for (let yr = 0; yr <= maxY; yr += 500) {
      const a = clamp(axis * maxY / 500 - yr / 500)
      ink(L, [Path.line(xOf(yr), y - 10, xOf(yr), y + 10)], a, { width: 1.5 })
      text(L, String(yr), xOf(yr), y + 44, { size: 24, alpha: a * 0.6 })
    }
    const people_ = chrono.events.filter((e) => e.he && !e.conflict)
    people_.forEach((e, i) => {
      const a = clamp(axis * 1.2 - e.year / maxY)
      L.fillStyle = gold(0.8 * a)
      L.beginPath()
      L.arc(xOf(e.year), y, 3, 0, Math.PI * 2)
      L.fill()
      text(L, e.he, xOf(e.year), y - 24 - (i % 3) * 22, { font: HEBREW, size: 16, alpha: a * 0.55 })
    })
    const marks = [
      ['flood', 'המבול', s.cue(6) + 1.2],
      ['abram', 'אברם', s.cue(7) + 0.4],
      ['exodus', 'יציאת מצרים', s.cue(7) + 2.0],
    ]
    for (const [ev, he, t0] of marks) {
      const e = chrono.known.find((k) => k.event === ev)
      const a = smooth(s.u, t0, t0 + 0.7)
      const x = xOf(e.year)
      ink(L, [Path.line(x, y - 20, x, y - 200)], a, { color: C.hot })
      text(L, String(e.year), x, y - 230, { size: 72, weight: 500, alpha: a })
      text(L, he, x, y - 310, { font: HEBREW, size: 34, alpha: a * 0.9 })
      const ok = smooth(s.u, s.cue(8) + 0.4, s.cue(8) + 1.0)
      text(L, e.holds ? '✓' : '✗', x, y + 110, { size: 40, alpha: ok, color: C.hot })
    }
    text(L, 'סדר עולם', 960, y + 210, { font: HEBREW, size: 40, alpha: smooth(s.u, s.cue(8) + 0.2, s.cue(8) + 0.9) })
    label(L, 'years from creation', 960, 960, axis * 0.7)
    L.restore()
  }
}

// --- honest discoveries ---------------------------------------------------------------------------

function findings(g, s) {
  const { L } = g
  const { findings: f } = g.data
  // a claim against its shuffles: the cloud of chance, and the real value apart from it
  const cloud = window_(s.u, 0, s.cue(2) + 0.2, 0.4, 0.6)
  if (cloud > 0) {
    L.save()
    L.globalAlpha = cloud
    const r = rng(11)
    const base = 760
    const counts = new Array(36).fill(0)
    const fall = smooth(s.u, 0.2, s.cue(1) + 1.5)
    const n = 420
    for (let i = 0; i < n; i++) {
      const v = (r() + r() + r() + r() - 2) / 2 // a bell, roughly
      const col = clamp(Math.floor((v + 1) * 18), 0, 35)
      const a = clamp(fall * n - i)
      if (a <= 0) continue
      const h = counts[col]++
      L.fillStyle = gold(0.75 * a)
      L.beginPath()
      L.arc(420 + col * 22, base - h * 14 - (1 - a) * 60, 4.5, 0, Math.PI * 2)
      L.fill()
    }
    ink(L, [Path.line(380, base + 14, 1260, base + 14)], fall, { width: 1.5, alpha: 0.6 })
    label(L, 'shuffled text', 820, base + 64, fall * 0.8)
    const real = smooth(s.u, s.cue(1) + 0.4, s.cue(1) + 1.6)
    g.tip(ink(L, [Path.line(1520, base + 14, 1520, 380)], real, { color: C.hot }))
    label(L, 'the text', 1520, 350, real)
    L.restore()
  }
  // borne out / not borne out
  const cols = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 0.6) * (1 - smooth(s.u, s.cue(6) + 2.4, s.cue(6) + 3.0))
  if (cols > 0) {
    L.save()
    L.globalAlpha = cols
    label(L, 'borne out', 560, 200, 1, { size: 26 })
    label(L, 'not borne out', 1460, 200, 1, { size: 26 })
    ink(L, [Path.line(1010, 180, 1010, 940)], smooth(s.u, s.cue(2), s.cue(2) + 1), { width: 1, alpha: 0.4 })
    // the Elohistic Psalter: Psalms cut in three by the divine names
    const e = smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 2.0)
    const { cut1, cut2, shares } = f.psalms
    const x0 = 200
    const x1 = 920
    const xp = (n) => lerp(x0, x1, (n - 1) / 149)
    ink(L, [Path.line(x0, 330, x1, 330)], e)
    const parts = [[1, cut1 - 1], [cut1, cut2 - 1], [cut2, 150]]
    parts.forEach(([a, b], i) => {
      const q = clamp(e * 3 - i)
      const h = 90 * shares[i]
      L.fillStyle = (i === 1 ? hot : gold)(0.25 * q)
      L.fillRect(xp(a), 330 - h, xp(b) - xp(a), h)
      ink(L, [Path.poly([[xp(a), 330], [xp(a), 330 - h], [xp(b), 330 - h], [xp(b), 330]])], q, { width: 2 })
      text(L, `${Math.round(shares[i] * 100)}%`, (xp(a) + xp(b)) / 2, 330 - h - 14, { size: 24, alpha: q * 0.9 })
    })
    text(L, String(cut1), xp(cut1), 362, { size: 22, alpha: e * 0.8 })
    text(L, String(cut2), xp(cut2), 362, { size: 22, alpha: e * 0.8 })
    label(L, 'the Elohistic Psalter, found', 560, 410, e * 0.85, { size: 18 })
    // the judges' cycle wearing down
    const j = smooth(s.u, s.cue(4) - 0.2, s.cue(4) + 2.0)
    f.judges.forEach((jd, i) => {
      const q = clamp(j * 6 - i)
      const x = 290 + i * 110
      const h = jd.slots * 24
      ink(L, [Path.line(x, 680, x, 680 - h * q)], q, { width: 10 })
      text(L, jd.he, x, 716, { font: HEBREW, size: 22, alpha: q * 0.9 })
      text(L, String(jd.slots), x, 680 - h - 14, { size: 22, alpha: q * 0.8 })
    })
    label(L, "the judges' cycle wears down", 560, 770, j * 0.85, { size: 18 })
    // haftarot
    const h = smooth(s.u, s.cue(5) - 0.2, s.cue(5) + 1.0)
    label(L, 'haftarot sit close to their parashot', 560, 880, h * 0.85, { size: 18 })
    text(L, '✓', 560, 840, { size: 40, alpha: h, color: C.hot })
    // and claims that failed
    const fails = ['doubled psalms swap the divine name', 'retold speech changes more', 'laments turn to praise more than hymns']
    fails.forEach((t, i) => {
      const q = smooth(s.u, s.cue(6) - 0.4 + i * 0.35, s.cue(6) + 0.2 + i * 0.35)
      text(L, '✗', 1460, 320 + i * 170, { size: 40, alpha: q })
      label(L, t, 1460, 370 + i * 170, q * 0.8, { size: 18 })
    })
    L.restore()
  }
  const dev = smooth(s.u, s.cue(6) + 2.4, s.cue(6) + 2.8)
  if (dev > 0) g.device(260, 120, 1400, 800, smooth(s.u, s.cue(6) + 2.4, s.cue(6) + 3.4), 'findings', s.u - s.cue(6) - 2.4)
}

// --- your own questions -------------------------------------------------------------------------

function tools(g, s) {
  const { L } = g
  g.device(260, 120, 1400, 800, smooth(s.u, -0.2, 1.0), 'tools', s.u)
  // the search: a line sweeping across under the frame
  const sweep = span(s.u, s.cue(1), s.cue(1) + 2.2)
  if (sweep > 0 && sweep < 1) {
    ink(L, [Path.line(lerp(260, 1660, sweep) - 120, 960, lerp(260, 1660, sweep), 960)], 1, { color: C.hot })
  }
  const lang = smooth(s.u, s.cue(3) + 2.4, s.cue(3) + 3.0)
  label(L, 'english', 860, 990, 1 - lang * 0.6, { size: 20 })
  text(L, '·', 960, 990, { size: 30, alpha: 0.6 })
  text(L, 'עברית', 1060, 992, { font: HEBREW, size: 26, alpha: 0.4 + lang * 0.6 })
}

// --- the outro: the ring, the name ---------------------------------------------------------------

function outro(g, s) {
  const { L } = g
  g.camera(lerp(1.03, 1, smooth(s.u, 0, 3)))
  const ring = Path.arc(960, 400, 150, -Math.PI / 2, Math.PI * 1.5, 180)
  const p = smooth(s.u, 0, 1.8)
  g.tip(ink(L, [ring], p))
  const fill = smooth(s.u, 1.5, 2.6)
  if (fill > 0) {
    const gr = L.createRadialGradient(930, 360, 10, 960, 400, 150)
    gr.addColorStop(0, `rgba(242,224,174,${0.95 * fill})`)
    gr.addColorStop(0.6, `rgba(221,194,132,${0.85 * fill})`)
    gr.addColorStop(1, `rgba(168,135,78,${0.8 * fill})`)
    L.fillStyle = gr
    L.beginPath()
    L.arc(960, 400, 150, 0, Math.PI * 2)
    L.fill()
  }
  const bet = once('outro-bet', () => glyphs(g.fonts.hebrew, 'ב', 960, 470, 200))
  if (fill > 0.3) {
    L.save()
    L.globalCompositeOperation = 'destination-out'
    L.globalAlpha = smooth(s.u, 2.0, 2.8)
    L.fill(bet.fill)
    L.restore()
  }
  text(L, 'EVERY VERSE, EVERY ECHO', 960, 700, { size: 56, weight: 500, spacing: 12, alpha: smooth(s.u, 2.2, 3.2) })
  const he = once('outro-he', () => glyphs(g.fonts.hebrew, 'כל פסוק, כל הד', 960, 800, 64, { rtl: true }))
  g.tip(traced(L, he, smooth(s.u, 2.8, 5.0), smooth(s.u, 4.6, 5.4)))
  label(L, 'bible-similarity', 960, 900, smooth(s.u, 5.0, 5.8) * 0.75, { font: MONO, weight: 400, size: 20, spacing: 4 })
}

export default {
  hook,
  question,
  lenses,
  'told-twice': toldTwice,
  reader,
  music,
  'people-places-time': people,
  findings,
  tools,
  outro,
  captures: { compare: 1, unit: 1, synopses: 1, reader: 1, findings: 1, tools: 1, 'genealogy-places': 1, poetry: 1 },
}

