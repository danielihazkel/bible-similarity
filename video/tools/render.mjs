// Renders a film page frame by frame in the installed Edge, headless, and encodes it with ffmpeg.
//
//   node tools/render.mjs a --stills                 one still per scene → out/a/stills/<scene>.png
//   node tools/render.mjs a --stills --at 3,10.5     stills at these times (seconds)
//   node tools/render.mjs a [--workers 4] [--from S --to S] [--fast] [--burn]
//                                                    the film → out/a/a.mp4 (+ a.en.mp4 / a.he.mp4
//                                                    with burned subtitles with --burn)
//
// The page (film/index.html?film=a) draws any time t through window.renderAt(t) and sets
// window.__ready when its data, fonts and captures are loaded, as in mg-styles-15's harness.

import { spawn } from 'node:child_process'
import { createReadStream, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { dirname, extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const VIDEO = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const FPS = 30
const W = 1920
const H = 1080
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg', '.css': 'text/css' }

function args() {
  const a = process.argv.slice(2)
  const opt = { film: a[0], stills: false, at: null, workers: 4, from: 0, to: null, burn: false, fast: false }
  for (let i = 1; i < a.length; i++) {
    const k = a[i]
    if (k === '--stills') opt.stills = true
    else if (k === '--burn') opt.burn = true
    else if (k === '--fast') opt.fast = true
    else if (k === '--at') opt.at = a[++i].split(',').map(Number)
    else if (k === '--workers') opt.workers = Number(a[++i])
    else if (k === '--from') opt.from = Number(a[++i])
    else if (k === '--to') opt.to = Number(a[++i])
    else throw new Error(`unknown option ${k}`)
  }
  if (!['a', 'b'].includes(opt.film)) throw new Error('usage: render.mjs a|b [--stills] ...')
  return opt
}

// Frames come back from the page as PNG (or JPEG with --fast), encoded by the canvas and POSTed
// to /frame/<worker>: ~0.19 s (0.05 s) a frame against ~1 s for a screenshot in Edge, and raw
// RGBA is slower still to upload. Each worker's frames go to its own ffmpeg, in order.
const sinks = new Map()

function serve() {
  const server = createServer((req, res) => {
    if (req.method === 'POST' && req.url.startsWith('/frame/')) {
      const sink = sinks.get(req.url.slice(7))
      const chunks = []
      req.on('data', (c) => chunks.push(c))
      req.on('end', () => {
        const buf = Buffer.concat(chunks)
        if (sink.write(buf)) res.writeHead(204).end()
        else sink.once('drain', () => res.writeHead(204).end())
      })
      return
    }
    const path = normalize(join(VIDEO, decodeURIComponent(new URL(req.url, 'http://x').pathname)))
    if (!path.startsWith(VIDEO) || !existsSync(path) || statSync(path).isDirectory()) {
      res.writeHead(404).end()
      return
    }
    res.writeHead(200, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' })
    createReadStream(path).pipe(res)
  })
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)))
}

async function openPage(browser, port, film) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  page.on('console', (m) => {
    // a capture not made yet is a 404 the page expects
    if (m.type() === 'error' && !m.text().includes('404')) console.error(`page: ${m.text()}`)
  })
  // an error before the page is ready ends the render at once
  const failed = new Promise((_, fail) => page.on('pageerror', (e) => fail(new Error(`page error: ${e.message}`))))
  await page.goto(`http://127.0.0.1:${port}/film/index.html?film=${film}`)
  await Promise.race([page.waitForFunction(() => window.__ready === true, null, { timeout: 120_000 }), failed])
  return page
}

async function frame(page, t) {
  await page.evaluate((t) => window.renderAt(t), t)
  return page.screenshot({ clip: { x: 0, y: 0, width: W, height: H }, type: 'png' })
}

function ffmpeg(argv) {
  const p = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...argv], { stdio: ['pipe', 'inherit', 'inherit'] })
  const done = new Promise((ok, fail) => p.on('close', (c) => (c === 0 ? ok() : fail(new Error(`ffmpeg exited ${c}`)))))
  return { stdin: p.stdin, done }
}

async function stills(browser, port, opt, timing, out) {
  const page = await openPage(browser, port, opt.film)
  const dir = join(out, 'stills')
  mkdirSync(dir, { recursive: true })
  // by default the moment each scene is most complete: just before its last line ends
  const shots = opt.at
    ? opt.at.map((t) => [`t${t.toFixed(2)}`, t])
    : timing.scenes.map((s) => [s.id, s.lines.at(-1).end - 0.3])
  for (const [name, t] of shots) {
    writeFileSync(join(dir, `${name}.png`), await frame(page, t))
    console.log(`${join(dir, `${name}.png`)}  (t = ${t.toFixed(2)})`)
  }
}

async function renderRange(browser, port, film, f0, f1, file, label, fast) {
  const page = await openPage(browser, port, film)
  const [type, codec] = fast ? ['image/jpeg', 'mjpeg'] : ['image/png', 'png']
  const enc = ffmpeg(['-f', 'image2pipe', '-c:v', codec, '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709',
    '-color_trc', 'bt709', '-colorspace', 'bt709', file])
  sinks.set(label, enc.stdin)
  const url = `/frame/${label}`
  const t0 = Date.now()
  for (let f = f0; f < f1; f++) {
    await page.evaluate(async ({ t, url, type }) => {
      await window.renderAt(t)
      const blob = await new Promise((ok) => document.getElementById('film').toBlob(ok, type, 0.95))
      const r = await fetch(url, { method: 'POST', body: blob })
      if (!r.ok) throw new Error(`frame upload: ${r.status}`)
    }, { t: f / FPS, url, type })
    if ((f - f0) % 300 === 0) {
      const rate = (f - f0) / ((Date.now() - t0) / 1000 || 1)
      console.log(`${label}: frame ${f - f0} / ${f1 - f0} (${rate.toFixed(1)} fps)`)
    }
  }
  enc.stdin.end()
  await enc.done
  await page.close()
}

async function film(browser, port, opt, timing, out) {
  const last = Math.round((opt.to ?? timing.duration) * FPS)
  const first = Math.round(opt.from * FPS)
  const n = last - first
  const per = Math.ceil(n / opt.workers)
  const parts = []
  const segDir = join(out, 'segments')
  mkdirSync(segDir, { recursive: true })
  const jobs = []
  for (let w = 0; w < opt.workers; w++) {
    const f0 = first + w * per
    const f1 = Math.min(last, f0 + per)
    if (f0 >= f1) break
    const file = join(segDir, `part${w}.mp4`)
    parts.push(file)
    jobs.push(renderRange(browser, port, opt.film, f0, f1, file, `worker${w}`, opt.fast))
  }
  await Promise.all(jobs)
  const list = join(segDir, 'list.txt')
  writeFileSync(list, parts.map((p) => `file '${p.replaceAll('\\', '/')}'`).join('\n'))
  const audio = join(out, 'mix.wav')
  const mp4 = join(out, `${opt.film}.mp4`)
  const ss = opt.from ? ['-ss', String(opt.from)] : []
  await ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, ...ss, '-i', audio,
    '-i', join(out, `${opt.film}.en.srt`), '-i', join(out, `${opt.film}.he.srt`),
    '-map', '0:v', '-map', '1:a', '-map', '2', '-map', '3', '-c:v', 'copy',
    '-c:a', 'aac', '-b:a', '256k', '-c:s', 'mov_text',
    '-metadata:s:s:0', 'language=eng', '-metadata:s:s:1', 'language=heb',
    // the film's own length: -shortest would also stop at the last subtitle, before the outro's hold
    '-t', String(last / FPS - opt.from), '-movflags', '+faststart', mp4]).done
  console.log(mp4)
  if (opt.burn) {
    const fonts = join(VIDEO, 'out', 'assets').replaceAll('\\', '/').replace(':', '\\:')
    for (const lang of ['en', 'he']) {
      const srt = join(out, `${opt.film}.${lang}.srt`).replaceAll('\\', '/').replace(':', '\\:')
      const font = lang === 'he' ? 'Frank Ruhl Libre' : 'Cormorant Garamond'
      const style = `FontName=${font},FontSize=26,PrimaryColour=&H00A5D7E9,OutlineColour=&H00201300,BorderStyle=1,Outline=1.2,Shadow=0,MarginV=48`
      const burned = join(out, `${opt.film}.${lang}.mp4`)
      await ffmpeg(['-i', mp4, '-map', '0:v', '-map', '0:a',
        '-vf', `subtitles='${srt}':fontsdir='${fonts}':force_style='${style}'`,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-c:a', 'copy', '-movflags', '+faststart', burned]).done
      console.log(burned)
    }
  }
  rmSync(segDir, { recursive: true, force: true })
}

async function main() {
  const opt = args()
  const out = join(VIDEO, 'out', opt.film)
  const timing = JSON.parse(readFileSync(join(out, 'timing.json'), 'utf8'))
  const server = await serve()
  const browser = await chromium.launch({ channel: 'msedge', args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] })
  try {
    if (opt.stills) await stills(browser, server.address().port, opt, timing, out)
    else await film(browser, server.address().port, opt, timing, out)
  } finally {
    await browser.close()
    server.close()
  }
}

main().catch((e) => { console.error(e); process.exit(1) })
