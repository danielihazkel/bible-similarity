// Film B, "One GPU, 23,206 verses": one function per scene of video/script/b-dev.yaml.
// Same conventions as scenes-a.js: g.L glows, g.P is plain, s.cue(i) is when line i is spoken.

import {
  C, HEBREW, MONO, Path, clamp, ease, fmt, glyphs, gold, hebrewWords, hot, ink, label, lerp, rng, smooth, span,
  text, traced, window_,
} from './lib.js'

const memo = new Map()
const once = (key, make) => {
  if (!memo.has(key)) memo.set(key, make())
  return memo.get(key)
}
const mono = (L, s, x, y, o = {}) => text(L, s, x, y, { font: MONO, weight: 400, size: 24, ...o })

// --- hook: every verse against every other, on one card --------------------------------------------

function hook(g, s) {
  const { L } = g
  const n = g.data.numbers.rows.verses
  const x0 = 700
  const y0 = 80
  const size = 520
  const k = 12
  const grid = 1 - 0.55 * smooth(s.u, s.cue(1) - 0.3, s.cue(1) + 0.5)
  // the grid, then its tiles filling as the GPU works through them chunk by chunk
  g.tip(ink(L, [Path.rect(x0, y0, size, size, 0)], smooth(s.u, -0.4, 0.9), { alpha: grid }))
  const fill = span(s.u, 0.6, s.cueEnd(0))
  const tiles = Math.floor(fill * k * k)
  L.save()
  L.globalAlpha = grid
  for (let i = 0; i < k * k; i++) {
    const x = x0 + (i % k) * (size / k)
    const y = y0 + Math.floor(i / k) * (size / k)
    if (i < tiles) {
      L.fillStyle = gold(0.13)
      L.fillRect(x + 2, y + 2, size / k - 4, size / k - 4)
    } else if (i === tiles && fill < 1) {
      L.fillStyle = hot(0.75)
      L.fillRect(x + 2, y + 2, size / k - 4, size / k - 4)
    }
  }
  L.restore()
  const pairs = n * n * fill
  text(L, fmt(pairs), 960, 680, { size: 64, alpha: smooth(s.u, 0.4, 1.0), spacing: 2 })
  label(L, 'verse pairs', 960, 718, smooth(s.u, 0.8, 1.4) * 0.8)
  // the card: a GTX 1080 Ti, drawn
  const card = smooth(s.u, s.cue(1) - 0.2, s.cue(1) + 2.4)
  if (card > 0) {
    const cx = 960
    const cy = 860
    const w = 640
    const h = 150
    const paths = [Path.rect(cx - w / 2, cy - h / 2, w, h, 12)]
    for (const fx of [cx - 150, cx + 150]) {
      paths.push(Path.arc(fx, cy, 52, 0, Math.PI * 2, 64))
      for (let b = 0; b < 7; b++) {
        const a = (b / 7) * Math.PI * 2
        paths.push(Path.quad([fx + 10 * Math.cos(a), cy + 10 * Math.sin(a)], [fx + 34 * Math.cos(a + 0.5), cy + 34 * Math.sin(a + 0.5)], [fx + 48 * Math.cos(a + 0.2), cy + 48 * Math.sin(a + 0.2)], 10))
      }
    }
    for (let t = 0; t < 14; t++) paths.push(Path.rect(cx - 210 + t * 22, cy + h / 2, 14, 16, 2))
    g.tip(ink(L, paths, card, { width: 2.2 }))
    mono(L, 'GTX 1080 Ti · 2017 · 11 GB', cx, cy + h / 2 + 60, { size: 22, alpha: smooth(s.u, s.cue(1) + 1.6, s.cue(1) + 2.2) * 0.85 })
  }
  // fp32 only
  const p = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 0.6)
  if (p > 0) {
    mono(L, 'fp32', 1530, 840, { size: 84, alpha: p, color: C.hot })
    mono(L, 'fp16', 1450, 920, { size: 32, alpha: p * 0.6 })
    mono(L, 'bf16', 1610, 920, { size: 32, alpha: p * 0.6 })
    ink(L, [Path.line(1400, 908, 1500, 908), Path.line(1560, 908, 1660, 908)], smooth(s.u, s.cue(2) + 0.6, s.cue(2) + 1.4), { color: C.hot })
    const cloud = [Path.arc(370, 860, 46, Math.PI, Math.PI * 2, 32), Path.arc(440, 840, 60, Math.PI * 1.05, Math.PI * 1.95, 32), Path.arc(505, 860, 44, Math.PI, Math.PI * 2, 32), Path.line(324, 860, 549, 860)]
    ink(L, cloud, smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 0.8), { width: 2, alpha: 0.8 })
    ink(L, [Path.line(320, 900, 560, 780)], smooth(s.u, s.cue(2) + 0.6, s.cue(2) + 1.2), { color: C.hot })
  }
}

// --- data: the sources, one table, one id -------------------------------------------------------

function data(g, s) {
  const { L } = g
  const sources = [
    ['OSHB', 'lemmas · morphology', 1],
    ['Sefaria · MAM', 'the text on screen', 2],
    ['Sefaria · links', 'cross-references → gold', 4],
    ['ETCBC · BHSA', 'clauses · phrases', 5],
    ['SDBH', 'word senses · domains', 5.4],
  ]
  const top = window_(s.u, -0.3, s.cue(6) + 0.2, 0.3, 0.6)
  const tableY = 470
  sources.forEach(([name, sub, c], i) => {
    const x = 270 + i * 345
    // all five drawn while "open sources" is said; each lit and joined to the table on its own line
    const t0 = c === 5.4 ? s.cue(5) + 1.2 : s.cue(c)
    const p = smooth(s.u, s.cue(0) - 0.3 + i * 0.35, s.cue(0) + 0.8 + i * 0.35)
    const lit = window_(s.u, t0 - 0.2, t0 + 3.0, 0.4, 0.8)
    L.save()
    L.globalAlpha = top
    g.tip(ink(L, [Path.rect(x - 150, 170, 300, 100, 10)], p))
    ink(L, [Path.rect(x - 150, 170, 300, 100, 10)], lit, { color: C.hot, width: 3.5 })
    mono(L, name, x, 222, { size: 26, alpha: p, color: lit > 0.5 ? C.hot : C.gold })
    label(L, sub, x, 252, p * 0.7, { size: 15, spacing: 3 })
    ink(L, [Path.cubic([x, 270], [x, 370], [960, 360], [960, tableY])], smooth(s.u, t0 + 0.2, t0 + 1.2), { width: 1.3, alpha: 0.55 })
    L.restore()
  })
  const tab = smooth(s.u, s.cue(1), s.cue(1) + 1.2)
  ink(L, [Path.rect(620, tableY, 680, 200, 12)], tab)
  mono(L, 'verses · words · units', 960, tableY + 50, { size: 24, alpha: tab * 0.9 })
  const words = g.data.dev.words
  const al = smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 1.6)
  // one rule: the verse's place in the canon is its row everywhere
  const rule = smooth(s.u, s.cue(6) - 0.1, s.cue(6) + 1.6)
  const count = 1 - smooth(s.u, s.cue(6) - 0.4, s.cue(6) + 0.1)
  text(L, fmt(words * al), 960, tableY + 130, { size: 60, alpha: smooth(s.u, s.cue(3) - 0.2, s.cue(3) + 0.3) * count })
  label(L, 'words · 99.96 % aligned', 960, tableY + 170, al * 0.85 * count, { size: 18 })
  if (rule > 0) {
    L.save()
    L.strokeStyle = hot(0.9 * rule)
    L.lineWidth = 2
    L.strokeRect(640, tableY + 70, 640, 34)
    L.restore()
    mono(L, 'verse_id 0 · בראשית א א', 960, tableY + 96, { size: 20, alpha: rule, color: C.hot })
    const rows = []
    for (let r = 0; r < 26; r++) rows.push(Path.line(1420, 400 + r * 16, 1780, 400 + r * 16))
    ink(L, rows, rule, { width: 1, alpha: 0.45 })
    ink(L, [Path.line(1420, 400, 1780, 400)], rule, { color: C.hot, width: 4 })
    label(L, 'embedding row 0', 1600, 380, rule, { size: 16 })
    ink(L, [Path.cubic([1280, tableY + 87], [1350, tableY + 87], [1350, 400], [1415, 400])], rule, { color: C.hot, width: 2 })
    for (let r = 0; r < 26; r++) ink(L, [Path.line(140, 400 + r * 16, 500, 400 + r * 16)], rule, { width: 1, alpha: 0.45 })
    ink(L, [Path.line(140, 400, 500, 400)], rule, { color: C.hot, width: 4 })
    label(L, 'every result table', 320, 380, rule, { size: 16 })
    ink(L, [Path.cubic([640, tableY + 87], [570, tableY + 87], [570, 400], [505, 400])], rule, { color: C.hot, width: 2 })
    mono(L, 'verse_id = canon order = row', 960, 900, { size: 38, alpha: smooth(s.u, s.cue(6) + 1.2, s.cue(6) + 2.0) })
  }
}

// --- lexical: lemmas, bigrams, formulas weighted down ------------------------------------------------

function lexical(g, s) {
  const { L } = g
  const v = g.data.verses.gen1_1_plain
  const words = v.he.replace('׃', '').split(' ')
  const a1 = window_(s.u, -0.3, s.cue(1) + 0.4, 0.4, 0.6)
  if (a1 > 0) {
    const boxes = hebrewWords(L, words, 1500, { size: 60 })
    const shift = (1500 - 420 - (boxes[0].x1 - boxes.at(-1).x0)) / 2
    L.save()
    L.globalAlpha = a1
    L.translate(-shift, 0)
    boxes.forEach((b, i) => {
      text(L, b.word, b.x1, 360, { font: HEBREW, size: 60, align: 'right', rtl: true, alpha: smooth(s.u, i * 0.1, 0.5 + i * 0.1) })
      const cx = (b.x0 + b.x1) / 2
      const p = smooth(s.u, 0.8 + i * 0.12, 1.4 + i * 0.12)
      ink(L, [Path.line(cx, 390, cx, 470)], p, { width: 1.2, alpha: 0.5 })
      ink(L, [Path.rect(cx - 40, 480, 80, 44, 8)], p)
      if (i < boxes.length - 1) {
        const nx = (boxes[i + 1].x0 + boxes[i + 1].x1) / 2
        ink(L, [Path.quad([cx, 530], [(cx + nx) / 2, 610], [nx, 530])], smooth(s.u, 2.2 + i * 0.15, 2.8 + i * 0.15), { width: 1.6, color: C.hot })
      }
    })
    L.restore()
    label(L, 'lemmas', 960, 700, smooth(s.u, 1.2, 1.8) * a1 * 0.85)
    label(L, 'lemma bigrams', 960, 740, smooth(s.u, 2.4, 3.0) * a1 * 0.85)
    mono(L, 'BM25', 960, 220, { size: 44, alpha: a1 * smooth(s.u, 0, 0.6) })
  }
  // a formula, said again and again, counted at a fifth
  const a2 = window_(s.u, s.cue(1) + 0.2, s.cue(3) + 0.3, 0.5, 0.6)
  if (a2 > 0) {
    L.save()
    L.globalAlpha = a2
    text(L, 'וידבר יהוה אל משה לאמר', 960, 360, { font: HEBREW, size: 64, rtl: true, alpha: smooth(s.u, s.cue(1) + 0.3, s.cue(1) + 1.0) })
    const reps = smooth(s.u, s.cue(1) + 0.8, s.cue(1) + 2.6)
    const r = rng(4)
    for (let i = 0; i < 40; i++) {
      const a = clamp(reps * 40 - i)
      L.fillStyle = gold(0.6 * a)
      L.fillRect(560 + r() * 800, 430 + r() * 70, 18, 3)
    }
    label(L, 'the same words, hundreds of times', 960, 550, reps * 0.75, { size: 18 })
    const w = lerp(1, 0.2, smooth(s.u, s.cue(2) + 0.2, s.cue(2) + 2.0))
    ink(L, [Path.line(560, 650, 1360, 650)], 1, { width: 1, alpha: 0.35 })
    ink(L, [Path.line(560, 650, 560 + 800 * w, 650)], smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 0.4), { width: 10, color: C.hot })
    mono(L, `weight × ${w.toFixed(1)}`, 960, 720, { size: 30, alpha: smooth(s.u, s.cue(2), s.cue(2) + 0.5) })
    L.restore()
  }
  // chapters and passages as bags of lemmas
  const a3 = window_(s.u, s.cue(3) - 0.1, s.cue(4) + 0.3, 0.5, 0.5)
  if (a3 > 0) {
    const r = rng(8)
    ;[640, 960, 1280].forEach((x, k) => {
      const p = smooth(s.u, s.cue(3) + k * 0.4, s.cue(3) + 1 + k * 0.4)
      L.save()
      L.globalAlpha = a3
      ink(L, [Path.arc(x, 450, 110, 0, Math.PI * 2, 80)], p)
      for (let i = 0; i < 26; i++) {
        const a = r() * Math.PI * 2
        const d = Math.sqrt(r()) * 90
        L.fillStyle = gold(0.8 * p)
        L.fillRect(x + d * Math.cos(a) - 2, 450 + d * Math.sin(a) - 2, 4, 4)
      }
      L.restore()
    })
    mono(L, 'TF-IDF', 960, 660, { size: 40, alpha: a3 * smooth(s.u, s.cue(3) + 0.4, s.cue(3) + 1) })
    label(L, 'chapters · passages · parashot', 960, 710, a3 * 0.8, { size: 18 })
  }
  // every pair at once: one sparse product
  const a4 = smooth(s.u, s.cue(4) - 0.1, s.cue(4) + 0.4)
  if (a4 > 0) {
    const x0 = 710
    const y0 = 180
    const size = 500
    ink(L, [Path.rect(x0, y0, size, size, 0)], smooth(s.u, s.cue(4) - 0.1, s.cue(4) + 0.8))
    const r = rng(21)
    const k = Math.floor(smooth(s.u, s.cue(4) + 0.5, s.cue(4) + 2.5) * 1400)
    L.fillStyle = gold(0.75)
    for (let i = 0; i < k; i++) {
      const a = r()
      const b = Math.min(1, Math.max(0, a + (r() - 0.5) * (r() < 0.7 ? 0.08 : 1)))
      L.fillRect(x0 + a * size, y0 + b * size, 2.4, 2.4)
    }
    mono(L, 'sparse · all pairs · seconds', 960, 760, { size: 26, alpha: smooth(s.u, s.cue(4) + 1.4, s.cue(4) + 2.0) })
  }
}

// --- semantic: BEREL, trained twice, then corrected for hubs ----------------------------------------

function semantic(g, s) {
  const { L } = g
  const dv = g.data.dev.dev_verse
  const space = window_(s.u, -0.3, s.cue(6) + 0.2, 0.3, 0.6)
  // the encoder: twelve layers
  if (space > 0) {
    L.save()
    L.globalAlpha = space
    const layers = []
    for (let i = 0; i < 12; i++) layers.push(Path.rect(200, 760 - i * 44, 300, 32, 6))
    g.tip(ink(L, layers, smooth(s.u, -0.2, s.cue(0) + 2.4), { width: 2 }))
    mono(L, 'BEREL 3.0', 350, 220, { size: 34, alpha: smooth(s.u, 0.4, 1.0) })
    label(L, 'BERT · rabbinic Hebrew', 350, 830, smooth(s.u, 0.8, 1.4) * 0.8, { size: 16 })
    L.restore()
  }
  // the space: verses as points; pairs pulled together, hard negatives pushed off
  const pts = once('sem-points', () => {
    const r = rng(17)
    return Array.from({ length: 70 }, () => [760 + r() * 900, 220 + r() * 520, r() * 6.28])
  })
  const pairsIdx = [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]
  if (space > 0) {
    L.save()
    L.globalAlpha = space
    const pull = smooth(s.u, s.cue(2) + 0.4, s.cue(2) + 2.4)
    const push = smooth(s.u, s.cue(3) + 0.3, s.cue(3) + 2.0)
    const twin = window_(s.u, s.cue(1) - 0.2, s.cue(2) + 0.2, 0.4, 0.6)
    const pos = pts.map((p) => [p[0], p[1]])
    for (const [a, b] of pairsIdx) {
      const mx = (pts[a][0] + pts[b][0]) / 2
      const my = (pts[a][1] + pts[b][1]) / 2
      pos[a] = [lerp(pts[a][0], mx - 16, pull), lerp(pts[a][1], my, pull)]
      pos[b] = [lerp(pts[b][0], mx + 16, pull), lerp(pts[b][1], my, pull)]
    }
    pos.forEach(([x, y], i) => {
      const isPair = i < 12
      const isNeg = i >= 12 && i < 18
      let px = x
      let py = y
      if (isNeg) {
        const [ax, ay] = pos[(i - 12) * 2]
        const dx = x - ax
        const dy = y - ay
        const d = Math.hypot(dx, dy) || 1
        px = x + (dx / d) * 90 * push
        py = y + (dy / d) * 90 * push
      }
      const a = smooth(s.u, 0.5 + i * 0.02, 1.0 + i * 0.02)
      L.beginPath()
      L.arc(px, py, isPair ? 6 : 4, 0, Math.PI * 2)
      if (isNeg && push > 0) {
        L.strokeStyle = hot(a)
        L.lineWidth = 2
        L.stroke()
      } else {
        L.fillStyle = (isPair && pull > 0 ? hot : gold)(0.85 * a)
        L.fill()
      }
      if (twin > 0) {
        // SimCSE: the same verse twice, under dropout, drawn together
        const off = 14 * (1 - smooth(s.u, s.cue(1) + 0.5, s.cue(1) + 2.0))
        L.fillStyle = gold(0.45 * twin)
        L.fillRect(px + off * Math.cos(pts[i][2]) - 2, py + off * Math.sin(pts[i][2]) - 2, 4, 4)
      }
    })
    for (const [a, b] of pairsIdx) {
      ink(L, [Path.line(pos[a][0], pos[a][1], pos[b][0], pos[b][1])], smooth(s.u, s.cue(2), s.cue(2) + 0.8), { width: 1.4, color: C.hot })
    }
    label(L, 'SimCSE', 1210, 820, window_(s.u, s.cue(1), s.cue(2), 0.4, 0.4), { size: 18 })
    label(L, 'Sefaria pairs · cached MNRL', 1210, 820, window_(s.u, s.cue(2), s.cue(3), 0.4, 0.4), { size: 18 })
    label(L, 'hard negatives from BM25', 1210, 820, window_(s.u, s.cue(3), s.cue(4), 0.4, 0.4), { size: 18 })
    // hubness: one verse everyone's neighbour, until CSLS
    const hub = smooth(s.u, s.cue(5) - 0.2, s.cue(5) + 0.8)
    if (hub > 0) {
      const [hx, hy] = pos[40]
      const cut = smooth(s.u, s.cue(5) + 1.6, s.cue(5) + 3.0)
      pos.slice(20, 34).forEach(([x, y], j) => {
        ink(L, [Path.line(hx, hy, x, y)], hub, { width: 1, alpha: j < 3 ? 0.7 : 0.6 * (1 - cut) })
      })
      label(L, 'CSLS', 1210, 820, window_(s.u, s.cue(5), s.cue(6), 0.4, 0.4), { size: 18 })
    }
    L.restore()
  }
  // memory
  const vram = window_(s.u, s.cue(4) - 0.2, s.cue(5) + 0.3, 0.4, 0.5)
  if (vram > 0) {
    ink(L, [Path.rect(760, 900, 900, 30, 6)], vram, { width: 2 })
    L.fillStyle = hot(0.8 * vram)
    L.fillRect(764, 904, (892 * 3.8 * smooth(s.u, s.cue(4) + 0.6, s.cue(4) + 2.2)) / 11, 22)
    mono(L, '3.8 / 11 GB', 1210, 980, { size: 26, alpha: vram })
  }
  // the gain, step by step, on dev
  const bars = smooth(s.u, s.cue(6) - 0.2, s.cue(6) + 0.4)
  if (bars > 0) {
    const steps = [['raw BEREL', dv.berel_mean], ['+ SimCSE', dv.berel_simcse], ['supervised', dv.berel_sup], ['+ CSLS', dv.berel_sup_csls]]
    steps.forEach(([name, val], i) => {
      const x = 600 + i * 240
      const q = smooth(s.u, s.cue(6) + i * 0.5, s.cue(6) + 0.8 + i * 0.5)
      const h = val * 3000 * q
      ink(L, [Path.line(x, 780, x, 780 - h)], q > 0 ? 1 : 0, { width: 34, color: i === 3 ? C.hot : C.gold })
      mono(L, val.toFixed(3), x, 760 - h - 20, { size: 26, alpha: q })
      label(L, name, x, 830, q * 0.85, { size: 17 })
    })
    label(L, 'dev nDCG@10, verses', 960, 900, bars * 0.75, { size: 18 })
  }
}

// --- fusion: two ranked lists, one ---------------------------------------------------------------------

function fusion(g, s) {
  const { L } = g
  const { lists, dev } = g.data
  const listA = window_(s.u, -0.3, s.cue(2) + 0.2, 0.4, 0.6)
  if (listA > 0) {
    const short = (r) => r.replace('Psalms', 'Ps').replace('Genesis', 'Gen')
    L.save()
    L.globalAlpha = listA
    const cols = [['words', lists.lexical, 420], ['meaning', lists.semantic, 1500]]
    for (const [name, rows, x] of cols) {
      label(L, name, x, 250, smooth(s.u, 0, 0.6))
      rows.slice(0, 6).forEach((r, i) => {
        mono(L, short(r.ref), x, 320 + i * 64, { size: 26, alpha: smooth(s.u, 0.2 + i * 0.1, 0.7 + i * 0.1) })
      })
    }
    const best = smooth(s.u, s.cue(0) + 1.8, s.cue(0) + 2.6)
    mono(L, `BM25 ${dev.dev_verse.bm25_lemma.toFixed(3)}`, 420, 760, { size: 26, alpha: best, color: C.hot })
    mono(L, `BEREL ${dev.dev_verse.berel_sup_csls.toFixed(3)}`, 1500, 760, { size: 26, alpha: best })
    label(L, 'dev nDCG@10', 960, 760, best * 0.7, { size: 16 })
    // reciprocal rank fusion
    const p = smooth(s.u, s.cue(1) - 0.2, s.cue(1) + 2.2)
    label(L, 'fused', 960, 250, p)
    lists.fused.slice(0, 6).forEach((r, i) => {
      const y = 320 + i * 64
      const la = lists.lexical.findIndex((x) => x.ref === r.ref)
      const se = lists.semantic.findIndex((x) => x.ref === r.ref)
      const q = clamp(p * 6 - i)
      if (la >= 0 && la < 6) ink(L, [Path.cubic([560, 312 + la * 64], [700, 312 + la * 64], [700, y - 8], [820, y - 8])], q, { width: 1.4, alpha: 0.8 })
      if (se >= 0 && se < 6) ink(L, [Path.cubic([1360, 312 + se * 64], [1220, 312 + se * 64], [1220, y - 8], [1100, y - 8])], q, { width: 1.4, alpha: 0.8 })
      mono(L, short(r.ref), 960, y, { size: 26, alpha: q, color: C.hot })
    })
    mono(L, 'score = Σ  1 / (60 + rank)', 960, 880, { size: 30, alpha: smooth(s.u, s.cue(1) + 1.6, s.cue(1) + 2.3) })
    L.restore()
  }
  // on the test books: fusion first at every level
  const bars = smooth(s.u, s.cue(2) - 0.1, s.cue(2) + 0.5)
  if (bars > 0) {
    const levels = ['verse', 'chapter', 'pericope']
    levels.forEach((lv, i) => {
      const x0 = 420 + i * 420
      const row = dev.test[lv]
      ;[['lexical', row.lexical], ['semantic', row.semantic], ['fused', row.fused]].forEach(([name, val], j) => {
        const q = smooth(s.u, s.cue(2) + i * 0.4 + j * 0.15, s.cue(2) + 0.8 + i * 0.4 + j * 0.15)
        const x = x0 + j * 80
        const h = val * 2400 * q
        ink(L, [Path.line(x, 760, x, 760 - h)], q > 0 ? 1 : 0, { width: 40, color: name === 'fused' ? C.hot : C.gold, alpha: name === 'fused' ? 1 : 0.55 })
        mono(L, val.toFixed(3), x, 740 - h - 14, { size: 20, alpha: q * (name === 'fused' ? 1 : 0.7) })
      })
      label(L, lv, x0 + 80, 810, bars * 0.85, { size: 20 })
    })
    label(L, 'test nDCG@10 · words · meaning · fused', 960, 880, smooth(s.u, s.cue(3), s.cue(3) + 0.6) * 0.8, { size: 18 })
  }
}

// --- the hero: evaluation discipline ---------------------------------------------------------------

function discipline(g, s) {
  const { L } = g
  const { dev } = g.data
  const books = dev.books
  const maxV = Math.max(...books.map((b) => b.verses))
  const groups = { train: [], dev: [], test: [] }
  books.forEach((b, i) => groups[b.split].push(i))
  const gx = { train: 150, dev: 1030, test: 1330 }
  const step = 22
  const sort = smooth(s.u, s.cue(1), s.cue(1) + 2.2)
  const fade = (1 - 0.75 * smooth(s.u, s.cue(3) - 0.3, s.cue(3) + 0.6)) * (1 - smooth(s.u, s.cue(4) - 0.4, s.cue(4) + 0.3))
  const base = lerp(760, 930, smooth(s.u, s.cue(3) - 0.3, s.cue(3) + 0.6))
  const scaleH = lerp(1, 0.45, smooth(s.u, s.cue(3) - 0.3, s.cue(3) + 0.6))
  L.save()
  L.globalAlpha = fade
  books.forEach((b, i) => {
    const canonX = 150 + i * 42
    const k = groups[b.split].indexOf(i)
    const groupX = gx[b.split] + k * step
    const x = lerp(canonX, groupX, ease(sort))
    const h = (b.verses / maxV) * 320 * scaleH
    const q = smooth(s.u, -0.2 + i * 0.03, 0.5 + i * 0.03)
    ink(L, [Path.line(x, base, x, base - h * q)], q > 0 ? 1 : 0, { width: 10, color: b.split === 'test' ? C.hot : C.gold, alpha: b.split === 'train' ? 0.65 : 1 })
  })
  const lab = smooth(s.u, s.cue(1) + 1.6, s.cue(1) + 2.4)
  const center = (name) => gx[name] + ((groups[name].length - 1) * step) / 2
  for (const [name, n] of [['train', groups.train.length], ['dev', groups.dev.length], ['test', groups.test.length]]) {
    label(L, `${name} · ${n} books`, center(name), base + 50, lab, { size: 20 })
  }
  // the test books sealed, run once; every choice made on dev
  const seal = smooth(s.u, s.cue(2) + 1.4, s.cue(2) + 2.8)
  const tx = gx.test - 26
  const tw = (groups.test.length - 1) * step + 52
  ink(L, [Path.rect(tx, base - 360 * scaleH, tw, 360 * scaleH + 20, 14)], seal, { color: C.hot })
  label(L, 'run once', tx + tw / 2, base - 380 * scaleH, seal, { size: 20 })
  const devBox = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 1.2)
  const dx = gx.dev - 26
  const dw = (groups.dev.length - 1) * step + 52
  ink(L, [Path.rect(dx, base - 360 * scaleH, dw, 360 * scaleH + 20, 14)], devBox)
  label(L, 'every choice', dx + dw / 2, base - 380 * scaleH, devBox, { size: 20 })
  L.restore()
  // three gold sets
  const threads = window_(s.u, s.cue(3) - 0.1, s.cue(4) + 0.2, 0.4, 0.6)
  if (threads > 0) {
    ;['Sefaria', 'OpenBible', 'ETCBC'].forEach((name, i) => {
      const y = 300 + i * 120
      g.tip(ink(L, [Path.wave(380, 1540, y, 10, 4, i)], smooth(s.u, s.cue(3) + i * 0.6, s.cue(3) + 1.6 + i * 0.6), { alpha: threads, color: i === 0 ? C.hot : C.gold }))
      label(L, name, 280, y + 8, smooth(s.u, s.cue(3) + i * 0.6, s.cue(3) + 0.8 + i * 0.6) * threads, { align: 'right', size: 22 })
    })
    label(L, 'three gold sets', 960, 200, threads * 0.85)
  }
  // paired bootstrap: the change and its interval, against zero
  const ci = smooth(s.u, s.cue(4), s.cue(4) + 0.6)
  if (ci > 0) {
    const lo = -0.055
    const hi = 0.02
    const X0 = 520
    const X1 = 1700
    const xOf = (v) => lerp(X0, X1, (v - lo) / (hi - lo))
    const y0 = 200
    L.save()
    ink(L, [Path.line(xOf(0), y0 - 30, xOf(0), 720)], ci, { color: C.hot, width: 2 })
    mono(L, '0', xOf(0), y0 - 44, { size: 22, alpha: ci })
    label(L, 'paired bootstrap · dev nDCG@10 change', 960, 120, ci * 0.85, { size: 18 })
    // the cross-encoder: +0.0042 [-0.0007, +0.0092]
    const [d, a, b] = dev.rerank
    const r1 = smooth(s.u, s.cue(5) - 0.2, s.cue(5) + 1.0)
    const y1 = 290
    ink(L, [Path.line(xOf(a), y1, xOf(b), y1), Path.line(xOf(a), y1 - 12, xOf(a), y1 + 12), Path.line(xOf(b), y1 - 12, xOf(b), y1 + 12)], r1, { width: 2 })
    L.fillStyle = gold(r1)
    L.beginPath()
    L.arc(xOf(d), y1, 7, 0, Math.PI * 2)
    L.fill()
    label(L, 'cross-encoder reranker', X0 - 30, y1 + 7, r1, { align: 'right', size: 18 })
    mono(L, `+${d.toFixed(4)}`, xOf(b) + 70, y1 + 8, { size: 20, alpha: r1 })
    label(L, 'rejected', xOf(b) + 190, y1 + 7, smooth(s.u, s.cue(5) + 2.4, s.cue(5) + 3.0), { align: 'left', size: 18, color: C.hot })
    // newer encoders, against BEREL
    Object.entries(dev.encoders).forEach(([name, delta], i) => {
      const y = 400 + i * 80
      const q = smooth(s.u, s.cue(6) - 0.2 + i * 0.35, s.cue(6) + 0.6 + i * 0.35)
      ink(L, [Path.line(xOf(0), y, xOf(delta), y)], q, { width: 2, alpha: 0.6 })
      L.fillStyle = gold(q * 0.9)
      L.beginPath()
      L.arc(xOf(delta), y, 6, 0, Math.PI * 2)
      L.fill()
      const shown = name === 'large' ? 'DictaBERT large' : name
      label(L, shown, X0 - 30, y + 7, q, { align: 'right', size: 18 })
      mono(L, delta.toFixed(4), xOf(delta) - 70, y + 8, { size: 20, alpha: q * 0.8 })
    })
    const stays = smooth(s.u, s.cue(6) + 2.0, s.cue(6) + 2.6)
    label(L, 'BEREL stays', xOf(0) + 30, 760, stays, { align: 'left', size: 22, color: C.hot })
    const kept = smooth(s.u, s.cue(7), s.cue(7) + 0.8)
    label(L, 'kept in the record, next to what worked', 960, 860, kept * 0.85, { size: 20 })
    L.restore()
  }
}

// --- analyses: sixty-seven stages, each a test ----------------------------------------------------------

function analyses(g, s) {
  const { L } = g
  const { stages, dev } = g.data
  const graph = window_(s.u, -0.3, s.cue(2) + 0.2, 0.3, 0.6)
  if (graph > 0) {
    const n = stages.order.length
    const perRow = 12
    const pts = stages.order.map((_, i) => {
      const row = Math.floor(i / perRow)
      const col = i % perRow
      const x = 240 + (row % 2 ? perRow - 1 - col : col) * 131
      return [x, 230 + row * 110]
    })
    L.save()
    L.globalAlpha = graph
    const line = Path.poly(pts)
    const p = smooth(s.u, -0.2, s.cue(0) + 3.4)
    g.tip(ink(L, [line], p))
    pts.forEach(([x, y], i) => {
      const a = clamp((p * (n - 1) - i) * 2 + 1)
      L.fillStyle = (i === 0 || i === n - 1 ? hot : gold)(a)
      L.beginPath()
      L.arc(x, y, 6, 0, Math.PI * 2)
      L.fill()
      const name = stages.order[i]
      if (['download', 'train-sup', 'fuse', 'evaluate', 'genealogy', 'pentateuch', 'psalms', 'build-db'].includes(name)) {
        mono(L, name, x, y + 34, { size: 16, alpha: a * 0.8 })
      }
    })
    text(L, String(Math.round(clamp(p) * n)), 960, 1000, { size: 56, alpha: smooth(s.u, 0, 0.6) })
    label(L, 'stages', 960, 1040, smooth(s.u, 0.3, 0.9) * 0.8, { size: 18 })
    // each analysis against its shuffles
    const sh = smooth(s.u, s.cue(1) + 0.3, s.cue(1) + 1.6)
    if (sh > 0) {
      const r = rng(3)
      pts.forEach(([x, y], i) => {
        if (i < 18 || i > 64) return // the analyses, after the retrieval stages
        for (let k = 0; k < 6; k++) {
          L.fillStyle = gold(0.35 * sh)
          L.fillRect(x - 16 + r() * 32, y - 26 - r() * 10, 2, 2)
        }
        ink(L, [Path.line(x + 18, y - 34, x + 18, y - 14)], sh, { width: 2, color: C.hot })
      })
    }
    L.restore()
  }
  // Genesis–Numbers: the split found, against the critics' Priestly source
  const strip = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 0.6) * (1 - smooth(s.u, s.cue(4) - 0.3, s.cue(4) + 0.3))
  if (strip > 0) {
    L.save()
    L.globalAlpha = strip
    const X0 = 210
    const W_ = 1500
    const bw = W_ / dev.strip.length
    const draw = smooth(s.u, s.cue(2), s.cue(2) + 2.4)
    dev.strip.forEach(([found, ref], i) => {
      const a = clamp(draw * dev.strip.length - i)
      if (a <= 0) return
      L.fillStyle = hot(found * 0.9 * a)
      L.fillRect(X0 + i * bw, 380, bw + 0.5, 70)
      L.fillStyle = gold(ref * 0.9 * a)
      L.fillRect(X0 + i * bw, 500, bw + 0.5, 70)
    })
    label(L, 'found · function words and synonyms · no divine names', 960, 350, draw, { size: 18 })
    label(L, "the critics' P", 960, 610, draw, { size: 18 })
    label(L, 'Genesis', X0, 660, draw * 0.7, { align: 'left', size: 16 })
    label(L, 'Numbers', X0 + W_, 660, draw * 0.7, { align: 'right', size: 16 })
    const k = smooth(s.u, s.cue(3), s.cue(3) + 0.8)
    mono(L, `κ ${dev.kappa.observed.toFixed(3)}`, 760, 800, { size: 56, alpha: k, color: C.hot })
    mono(L, `κ ${dev.kappa.null.toFixed(3)} shifted`, 1180, 800, { size: 34, alpha: smooth(s.u, s.cue(3) + 1.4, s.cue(3) + 2.0) * 0.8 })
    L.restore()
  }
  // psalm genres from their form alone
  const nmi = smooth(s.u, s.cue(4) - 0.1, s.cue(4) + 0.6)
  if (nmi > 0) {
    const vals = [['form alone', dev.nmi.nmi, C.hot], ['shuffled', dev.nmi.null, C.gold]]
    vals.forEach(([name, v, color], i) => {
      const x = 820 + i * 280
      const q = smooth(s.u, s.cue(4) + i * 0.6, s.cue(4) + 1 + i * 0.6)
      const h = v * 1300 * q
      ink(L, [Path.line(x, 700, x, 700 - h)], q > 0 ? 1 : 0, { width: 60, color, alpha: i ? 0.6 : 1 })
      mono(L, v.toFixed(3), x, 680 - h - 10, { size: 28, alpha: q })
      label(L, name, x, 750, q * 0.85, { size: 18 })
    })
    label(L, "psalm genres against Gunkel's · NMI", 960, 220, nmi * 0.85, { size: 20 })
    const fail = smooth(s.u, s.cue(5), s.cue(5) + 0.7)
    mono(L, '✗', 960, 870, { size: 44, alpha: fail, color: C.hot })
    label(L, 'claims that fail are reported as failures', 960, 920, fail * 0.85, { size: 18 })
  }
}

// --- engineering: one command, a database, a viewer ------------------------------------------------------

function engineering(g, s) {
  const { L } = g
  const { dev, stages } = g.data
  const term = window_(s.u, -0.3, s.cue(3) + 0.2, 0.3, 0.6)
  if (term > 0) {
    L.save()
    L.globalAlpha = term
    g.tip(ink(L, [Path.rect(360, 150, 1200, 360, 14)], smooth(s.u, -0.3, 0.9)))
    const cmd = '$ uv run bsim all'
    const typed = Math.floor(smooth(s.u, 0.6, 1.8) * cmd.length)
    mono(L, cmd.slice(0, typed), 420, 230, { size: 34, align: 'left' })
    const t1 = smooth(s.u, s.cue(1) - 0.3, s.cue(1) + 1.6)
    const secs = Math.round(t1 * (38 * 60 + 28))
    mono(L, `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}  from an empty clone`, 420, 300, { size: 28, align: 'left', alpha: t1 > 0 ? 1 : 0 })
    const t2 = smooth(s.u, s.cue(1) + 2.2, s.cue(1) + 2.8)
    mono(L, cmd, 420, 380, { size: 34, align: 'left', alpha: t2 })
    mono(L, '2.3 s  nothing changed', 420, 440, { size: 28, align: 'left', alpha: smooth(s.u, s.cue(1) + 2.8, s.cue(1) + 3.4), color: C.hot })
    L.restore()
    // a stage reruns, and what reads it; the rest are skipped
    const chain = smooth(s.u, s.cue(2) - 0.2, s.cue(2) + 2.0)
    if (chain > 0) {
      const i = stages.order.indexOf('mirrors')
      const names = [...stages.order.slice(i - 2, i + 3), 'build-db']
      L.save()
      L.globalAlpha = term
      names.forEach((name, k) => {
        const x = 330 + k * 252
        const run = name === 'mirrors' || name === 'build-db'
        const q = clamp(chain * names.length - k)
        ink(L, [Path.rect(x - 110, 600, 220, 60, 10)], q, { color: run ? C.hot : C.gold, width: run ? 3 : 1.5, alpha: run ? 1 : 0.5 })
        mono(L, name, x, 638, { size: 20, alpha: q * (run ? 1 : 0.55), color: run ? C.hot : C.gold })
        label(L, run ? 'runs' : 'skipped', x, 700, q * 0.75, { size: 15 })
        if (k < names.length - 1) ink(L, [Path.line(x + 112, 630, x + 140, 630)], q, { width: 1.2, alpha: 0.5 })
      })
      label(L, 'code · config keys · input hashes', 960, 780, chain * 0.8, { size: 18 })
      L.restore()
    }
  }
  // the database, and one lookup
  const db = window_(s.u, s.cue(3) - 0.1, s.cue(5) + 0.2, 0.4, 0.6)
  if (db > 0) {
    L.save()
    L.globalAlpha = db
    const cx = 960
    const p = smooth(s.u, s.cue(3) - 0.1, s.cue(3) + 1.5)
    const ellipse = (y, a0, a1) => {
      const pts = []
      for (let i = 0; i <= 64; i++) {
        const a = lerp(a0, a1, i / 64)
        pts.push([cx + 220 * Math.cos(a), y + 48 * Math.sin(a)])
      }
      return Path.poly(pts)
    }
    const rings = [1, 2, 3].map((i) => ellipse(330 + i * 90, 0, Math.PI))
    g.tip(ink(L, [ellipse(330, Math.PI, Math.PI * 3), ...rings, Path.line(cx - 220, 330, cx - 220, 600), Path.line(cx + 220, 330, cx + 220, 600)], p, { width: 2.2 }))
    text(L, fmt(dev.matches * smooth(s.u, s.cue(3) + 0.5, s.cue(3) + 2.2)), cx, 760, { size: 64, alpha: smooth(s.u, s.cue(3) + 0.3, s.cue(3) + 0.8) })
    label(L, 'precomputed matches · SQLite', cx, 800, smooth(s.u, s.cue(3) + 0.8, s.cue(3) + 1.4) * 0.85, { size: 18 })
    const q = span(s.u, s.cue(4), s.cue(4) + 1.6)
    if (q > 0 && q < 1) {
      const path = Path.quad([1700, 200], [1300, 120], [cx + 40, 420])
      const back = Path.quad([cx + 40, 420], [1350, 250], [1700, 260])
      g.tip(ink(L, [path, back], q, { color: C.hot }))
    }
    mono(L, `${dev.similar_ms.toFixed(2)} ms median`, 1600, 330, { size: 28, alpha: smooth(s.u, s.cue(4) + 1.0, s.cue(4) + 1.6), color: C.hot })
    L.restore()
  }
  const dev_ = smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 0.4)
  if (dev_ > 0) {
    g.device(260, 100, 1400, 760, smooth(s.u, s.cue(5) - 0.1, s.cue(5) + 1.2), 'tools', s.u - s.cue(5))
    const tags = ['OpenAPI → TypeScript', 'Playwright · axe', 'English · עברית']
    tags.forEach((t, i) => label(L, t, 560 + i * 400, 960, smooth(s.u, s.cue(5) + 0.8 + i * 0.6, s.cue(5) + 1.4 + i * 0.6) * 0.85, { size: 18 }))
  }
}

// --- outro ----------------------------------------------------------------------------------------

function outro(g, s) {
  const { L } = g
  g.camera(lerp(1.03, 1, smooth(s.u, 0, 3)))
  const ring = Path.arc(960, 380, 140, -Math.PI / 2, Math.PI * 1.5, 180)
  g.tip(ink(L, [ring], smooth(s.u, -0.2, 1.6)))
  const fill = smooth(s.u, 1.3, 2.4)
  if (fill > 0) {
    const gr = L.createRadialGradient(930, 340, 10, 960, 380, 140)
    gr.addColorStop(0, `rgba(242,224,174,${0.95 * fill})`)
    gr.addColorStop(0.6, `rgba(221,194,132,${0.85 * fill})`)
    gr.addColorStop(1, `rgba(168,135,78,${0.8 * fill})`)
    L.fillStyle = gr
    L.beginPath()
    L.arc(960, 380, 140, 0, Math.PI * 2)
    L.fill()
    const bet = once('b-bet', () => glyphs(g.fonts.hebrew, 'ב', 960, 445, 190))
    L.save()
    L.globalCompositeOperation = 'destination-out'
    L.globalAlpha = smooth(s.u, 1.8, 2.6)
    L.fill(bet.fill)
    L.restore()
  }
  text(L, 'ONE GPU, 23,206 VERSES', 960, 670, { size: 54, weight: 500, spacing: 10, alpha: smooth(s.u, 2.0, 3.0) })
  const he = once('b-he', () => glyphs(g.fonts.hebrew, 'כרטיס גרפי אחד', 960, 770, 58, { rtl: true }))
  g.tip(traced(L, he, smooth(s.u, 2.4, 4.6), smooth(s.u, 4.2, 5.0)))
  mono(L, '$ uv run bsim all', 960, 870, { size: 30, alpha: smooth(s.u, 4.4, 5.2) })
  label(L, 'bible-similarity', 960, 930, smooth(s.u, 4.8, 5.6) * 0.75, { font: MONO, weight: 400, size: 20, spacing: 4 })
}

export default {
  hook,
  data,
  lexical,
  semantic,
  fusion,
  discipline,
  analyses,
  engineering,
  outro,
  captures: { tools: 1 },
}
