// The film page: window.renderAt(t) draws the frame at time t (seconds) as a pure function of t.
// Scenes come from scenes-<film>.js, keyed by the scene ids of the script; each draws while its
// narration plays, from video/out/<film>/timing.json, and fades into the next.

import { C, H, W, clamp, gold, ink, label, MONO, Path, rng, smooth, text } from './lib.js'

const film = new URLSearchParams(location.search).get('film') ?? 'a'
const json = (p) => fetch(p).then((r) => {
  if (!r.ok) throw new Error(`${p}: ${r.status}`)
  return r.json()
})

const canvas = document.getElementById('film')
const M = canvas.getContext('2d')
const layer = () => {
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  return c
}
// two scenes can be on screen at once (a crossfade): each gets a line layer and a plain layer
const pool = [0, 1].map(() => ({ lines: layer(), plain: layer() }))
const glowSmall = Object.assign(document.createElement('canvas'), { width: W / 2, height: H / 2 })

// --- background ------------------------------------------------------------------------------

function staticBackground() {
  const c = layer()
  const g = c.getContext('2d')
  g.fillStyle = C.ground
  g.fillRect(0, 0, W, H)
  const light = g.createRadialGradient(W * 0.5, H * 0.38, 40, W * 0.5, H * 0.45, W * 0.62)
  light.addColorStop(0, 'rgba(26,40,62,0.75)')
  light.addColorStop(1, 'rgba(26,40,62,0)')
  g.fillStyle = light
  g.fillRect(0, 0, W, H)
  g.fillStyle = 'rgba(233,215,165,0.045)'
  for (let y = 24; y < H; y += 48) {
    for (let x = 24; x < W; x += 48) g.fillRect(x - 1, y - 1, 2, 2)
  }
  return c
}

function vignette() {
  const c = layer()
  const g = c.getContext('2d')
  const v = g.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, W * 0.75)
  v.addColorStop(0, 'rgba(0,0,0,0)')
  v.addColorStop(1, 'rgba(0,0,0,0.5)')
  g.fillStyle = v
  g.fillRect(0, 0, W, H)
  return c
}

function grains() {
  const r = rng(99)
  return [0, 1, 2, 3].map(() => {
    const c = layer()
    const g = c.getContext('2d')
    const img = g.createImageData(W, H)
    for (let i = 0; i < img.data.length; i += 4) {
      const v = (r() * 255) | 0
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v
      img.data[i + 3] = 255
    }
    g.putImageData(img, 0, 0)
    return c
  })
}

const motes = (() => {
  const r = rng(5)
  return Array.from({ length: 70 }, () => ({
    x: r() * W, y: r() * H, vx: (r() - 0.5) * 6, vy: -2 - r() * 5, s: 1 + r() * 2.2, a: 0.08 + r() * 0.22, ph: r() * 6.28,
  }))
})()

function drawMotes(t) {
  M.save()
  M.globalCompositeOperation = 'screen'
  for (const m of motes) {
    const x = (((m.x + m.vx * t) % W) + W) % W
    const y = (((m.y + m.vy * t) % H) + H) % H
    const a = m.a * (0.6 + 0.4 * Math.sin(m.ph + t * 0.7))
    const g = M.createRadialGradient(x, y, 0, x, y, m.s * 4)
    g.addColorStop(0, `rgba(233,200,138,${a})`)
    g.addColorStop(1, 'rgba(233,200,138,0)')
    M.fillStyle = g
    M.fillRect(x - m.s * 4, y - m.s * 4, m.s * 8, m.s * 8)
  }
  M.restore()
}

// --- captures (screen recordings of the viewer, as numbered JPEGs) ----------------------------

const captures = {}
const frameCache = new Map()

async function loadCaptures(ids) {
  for (const id of ids) {
    try {
      captures[id] = await json(`../out/captures/${id}/info.json`)
    } catch {
      captures[id] = null // not captured yet: the frame shows a placeholder
    }
  }
}

function loadImage(src) {
  if (frameCache.has(src)) return frameCache.get(src)
  const p = new Promise((ok, fail) => {
    const img = new Image()
    img.onload = () => ok(img)
    img.onerror = fail
    img.src = src
  })
  frameCache.set(src, p)
  if (frameCache.size > 90) frameCache.delete(frameCache.keys().next().value)
  return p
}

// --- the frame ---------------------------------------------------------------------------------

let BG
let VIG
let GRAIN
let scenes
let timing
let data
const fonts = {}

function sceneWindows() {
  return timing.scenes.map((s, i) => {
    const next = timing.scenes[i + 1]
    const end = next ? next.start + 0.6 : timing.duration + 1
    return { ...s, i, from: i === 0 ? -1 : s.start - 0.35, to: end }
  })
}
let windows

async function renderAt(t) {
  M.globalAlpha = 1
  M.filter = 'none'
  M.globalCompositeOperation = 'source-over'
  M.drawImage(BG, 0, 0)
  drawMotes(t)
  const active = windows.filter((w) => t >= w.from && t < w.to).slice(-2)
  const tips = []
  const drawn = []
  for (const [k, w] of active.entries()) {
    const set = pool[k]
    const L = set.lines.getContext('2d')
    const P = set.plain.getContext('2d')
    L.setTransform(1, 0, 0, 1, 0, 0)
    P.setTransform(1, 0, 0, 1, 0, 0)
    L.clearRect(0, 0, W, H)
    P.clearRect(0, 0, W, H)
    const alpha = smooth(t, w.from, w.from + 0.6) * (1 - smooth(t, w.to - 0.95, w.to))
    const s = {
      id: w.id, t0: w.start, t1: w.end, u: t - w.start, dur: w.end - w.start, t,
      cue: (i) => (w.lines[clamp(i, 0, w.lines.length - 1)]?.start ?? w.start) - w.start,
      cueEnd: (i) => (w.lines[clamp(i, 0, w.lines.length - 1)]?.end ?? w.end) - w.start,
      lines: w.lines,
    }
    const g = {
      L, P, data, fonts, film, timing, s,
      tip: (pt) => {
        if (!pt) return
        const p = L.getTransform().transformPoint(new DOMPoint(pt[0], pt[1]))
        tips.push([p.x, p.y, alpha])
      },
      camera: (scale, cx = W / 2, cy = H / 2) => {
        for (const c of [L, P]) c.setTransform(scale, 0, 0, scale, W / 2 - cx * scale, H / 2 - cy * scale)
      },
      device: (x, y, w_, h, p, id, local) => device(g, x, y, w_, h, p, id, local),
    }
    // a slow push-in on every scene, which a scene may replace with its own camera
    g.camera(1 + 0.02 * clamp(s.u / Math.max(1, s.dur)))
    await scenes[w.id]?.(g, s)
    drawn.push([set, alpha])
  }
  // plain layers (captures) under the glowing line work
  for (const [set, alpha] of drawn) {
    M.globalAlpha = alpha
    M.drawImage(set.plain, 0, 0)
  }
  for (const [set, alpha] of drawn) composite(set.lines, alpha)
  M.globalAlpha = 1
  for (const [x, y, a] of tips) penTip(x, y, a)
  M.globalCompositeOperation = 'source-over'
  M.drawImage(VIG, 0, 0)
  M.globalCompositeOperation = 'overlay'
  M.globalAlpha = 0.07
  M.drawImage(GRAIN[Math.floor(t * 30) % GRAIN.length], 0, 0)
  M.globalAlpha = 1
  M.globalCompositeOperation = 'source-over'
}

// glow: a wide soft bloom (blurred at half size), a tight halo, then the sharp line
function composite(lines, alpha) {
  const gs = glowSmall.getContext('2d')
  gs.clearRect(0, 0, W / 2, H / 2)
  gs.filter = 'blur(9px)'
  gs.drawImage(lines, 0, 0, W / 2, H / 2)
  gs.filter = 'none'
  M.save()
  M.globalCompositeOperation = 'screen'
  M.globalAlpha = 0.55 * alpha
  M.drawImage(glowSmall, 0, 0, W, H)
  M.filter = 'blur(3px)'
  M.globalAlpha = 0.35 * alpha
  M.drawImage(lines, 0, 0)
  M.restore()
  M.globalAlpha = alpha
  M.drawImage(lines, 0, 0)
  M.globalAlpha = 1
}

function penTip(x, y, a) {
  M.save()
  M.globalCompositeOperation = 'lighter'
  const g = M.createRadialGradient(x, y, 0, x, y, 30)
  g.addColorStop(0, `rgba(255,246,220,${0.9 * a})`)
  g.addColorStop(0.25, `rgba(255,236,190,${0.35 * a})`)
  g.addColorStop(1, 'rgba(232,200,138,0)')
  M.fillStyle = g
  M.fillRect(x - 30, y - 30, 60, 60)
  M.restore()
}

// A capture of the viewer inside a frame drawn by the pen: the frame first, then the picture.
async function device(g, x, y, w, h, p, id, local) {
  const { L, P } = g
  const frame = Path.rect(x, y, w, h, 14)
  g.tip(ink(L, [frame], p))
  const bar = Path.line(x + 14, y + 38, x + w - 14, y + 38)
  ink(L, [bar], clamp((p - 0.85) / 0.15), { width: 1.5, alpha: 0.6 })
  const show = clamp((p - 0.7) / 0.3)
  if (show <= 0) return
  for (let i = 0; i < 3; i++) {
    L.save()
    L.globalAlpha *= show * 0.7
    L.fillStyle = gold(0.8)
    L.beginPath()
    L.arc(x + 26 + i * 18, y + 19, 4, 0, Math.PI * 2)
    L.fill()
    L.restore()
  }
  const inner = { x: x + 6, y: y + 44, w: w - 12, h: h - 50 }
  const cap = captures[id]
  if (!cap) {
    label(L, `capture · ${id}`, x + w / 2, y + h / 2 + 8, show * 0.55, { font: MONO, size: 20, spacing: 4, weight: 400 })
    return
  }
  const n = Math.min(cap.frames - 1, Math.max(0, Math.floor(local * cap.fps)))
  const img = await loadImage(`../out/captures/${id}/${String(n + 1).padStart(5, '0')}.jpg`)
  P.save()
  P.globalAlpha *= show
  P.beginPath()
  P.rect(inner.x, inner.y, inner.w, inner.h)
  P.clip()
  // fit by width, top aligned: the viewer's header stays in view
  const k = inner.w / img.width
  P.drawImage(img, inner.x, inner.y, img.width * k, img.height * k)
  P.restore()
}

// --- boot ----------------------------------------------------------------------------------

async function boot() {
  timing = await json(`../out/${film}/timing.json`)
  const names = ['field', 'pairs', 'verses', 'tree', 'land', 'chrono', 'lists', 'stages', 'numbers', 'retold', 'findings', 'dev']
  data = Object.fromEntries(await Promise.all(names.map(async (n) => [n, await json(`../out/data/${n}.json`)])))
  for (const [key, file] of [['serif', 'CormorantGaramond'], ['hebrew', 'FrankRuhlLibre'], ['mono', 'JetBrainsMono']]) {
    const buf = await fetch(`../out/assets/${file}.ttf`).then((r) => r.arrayBuffer())
    fonts[key] = window.opentype.parse(buf)
  }
  await Promise.all([
    document.fonts.load('500 40px "Cormorant Garamond"'),
    document.fonts.load('600 40px "Cormorant Garamond"'),
    document.fonts.load('400 40px "Frank Ruhl Libre"'),
    document.fonts.load('400 40px "JetBrains Mono"'),
  ])
  await document.fonts.ready
  scenes = (await import(`./scenes-${film}.js`)).default
  await loadCaptures(Object.keys(scenes.captures ?? {}))
  BG = staticBackground()
  VIG = vignette()
  GRAIN = grains()
  windows = sceneWindows()
  window.DEMO = { width: W, height: H, fps: 30, duration: timing.duration }
  window.renderAt = renderAt
  await renderAt(0)
  window.__ready = true
}

boot().catch((e) => {
  console.error(e.stack ?? e)
  text(M, String(e), W / 2, H / 2, { font: MONO, size: 24, color: '#f88' })
})

