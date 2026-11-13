// Screenshots of every fixture route, for a change of look that is checked by eye (M176):
//
//   uv run bsim fixture-serve --port 8778        (the built viewer: `npm run build` first)
//   node scripts/shots.mjs take <dir>            every route, English and Hebrew, light and dark
//   node scripts/shots.mjs compare <before> <after> <out>
//
// `take` writes one PNG per route, language and theme (1366 px wide, the page's height up to
// MAX_H) and `shots.json` with what was measured (the page's height, the top bar's, a sideways
// overflow, whether the heading was there before the data). `compare` writes `report.json` (the
// share of pixels that changed, the change of height) and, for each pair that differs, the two
// side by side in <out>. The routes are the fixture e2e's own list (`PAGES` of
// e2e/fixture.spec.ts). Options: `--base=URL`, `--langs=en,he`, `--themes=light,dark`,
// `--only=text` (routes holding the text), `--width=1366`. Runs in the installed Edge, as the
// e2e tests do (Playwright's Chromium on CI).
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const MAX_H = 2600
const WORKERS = 4

const args = process.argv.slice(2)
const flags = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')))
const [command, ...dirs] = args.filter((a) => !a.startsWith('--'))
const launch = () => chromium.launch({ channel: process.env.CI ? undefined : 'msedge' })

/** The routes of the fixture e2e, read from its source. */
function routes() {
  const src = readFileSync(join(web, 'e2e/fixture.spec.ts'), 'utf8').replaceAll('\r\n', '\n')
  const list = src.slice(src.indexOf('const PAGES = ['), src.indexOf('\n]', src.indexOf('const PAGES = [')))
  return [...list.matchAll(/^\s*'([^']+)',/gm)].map((m) => m[1])
}

/** A file name for a route: its path and query, with what a file system refuses replaced. */
const slug = (route) => (route === '/' ? 'home' : decodeURIComponent(route).replace(/^\//, '').replace(/[^\p{L}\p{N}.=-]+/gu, '_')).slice(0, 90)

async function take(out) {
  const base = flags.base ?? 'http://127.0.0.1:8778'
  const width = Number(flags.width ?? 1366)
  const langs = (flags.langs ?? 'en,he').split(',')
  const themes = (flags.themes ?? 'light,dark').split(',')
  mkdirSync(out, { recursive: true })
  const jobs = []
  for (const route of routes()) {
    if (flags.only && !route.includes(flags.only)) continue
    for (const lang of langs) for (const theme of themes) jobs.push({ route, lang, theme, name: `${slug(route)}.${lang}.${theme}` })
  }
  const names = new Set()
  for (const job of jobs) {
    // two routes that differ only past the name's length
    while (names.has(job.name)) job.name += '_'
    names.add(job.name)
  }
  const browser = await launch()
  const measured = {}
  let next = 0
  async function worker() {
    while (next < jobs.length) {
      const job = jobs[next++]
      const context = await browser.newContext({ viewport: { width, height: 860 }, serviceWorkers: 'block', reducedMotion: 'reduce' })
      await context.addInitScript(
        ([lang, theme]) => {
          localStorage.setItem('bsim.locale', lang)
          localStorage.setItem('bsim.theme', theme)
          // was the page's heading on screen while its data was still loading?
          window.__headingFirst = null
          const seen = () => {
            if (window.__headingFirst !== null) return
            const main = document.querySelector('main')
            if (!main) return
            const loading = main.querySelector('.status[role="status"], .list-placeholder')
            if (main.querySelector('h1') && loading) window.__headingFirst = true
            else if (loading) window.__loadingAlone = true
            else if (main.querySelector('h1')) window.__headingFirst = !window.__loadingAlone
          }
          new MutationObserver(seen).observe(document, { childList: true, subtree: true })
        },
        [job.lang, job.theme],
      )
      const page = await context.newPage()
      const errors = []
      page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)))
      try {
        await page.goto(base + job.route, { waitUntil: 'networkidle', timeout: 45_000 })
        await page.locator('main h1').first().waitFor({ timeout: 15_000 }).catch(() => errors.push('no h1'))
        await page.waitForFunction(() => !document.querySelector('main .status[role="status"], main .list-placeholder'), null, { timeout: 15_000 }).catch(() => errors.push('still loading'))
        await page.evaluate(() => document.fonts.ready)
        await page.waitForTimeout(250)
        const m = await page.evaluate(() => ({
          height: document.documentElement.scrollHeight,
          bar: Math.round(document.querySelector('.topbar')?.getBoundingClientRect().height ?? 0),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          headingFirst: window.__headingFirst,
        }))
        await page.screenshot({ path: join(out, `${job.name}.png`), fullPage: true, clip: { x: 0, y: 0, width, height: Math.min(m.height, MAX_H) } })
        measured[job.name] = { route: job.route, ...m, ...(errors.length ? { errors } : {}) }
      } catch (e) {
        measured[job.name] = { route: job.route, errors: [...errors, String(e).slice(0, 200)] }
      }
      await context.close()
      if (next % 50 === 0) console.log(`${next} / ${jobs.length}`)
    }
  }
  await Promise.all(Array.from({ length: WORKERS }, worker))
  await browser.close()
  writeFileSync(join(out, 'shots.json'), JSON.stringify(measured, null, 1))
  const bad = Object.entries(measured).filter(([, m]) => m.errors)
  console.log(`${jobs.length} shots in ${out}; ${bad.length} with a fault`)
  for (const [name, m] of bad) console.log(' ', name, m.errors.join(' | '))
}

async function compare(before, after, out) {
  mkdirSync(out, { recursive: true })
  const a = JSON.parse(readFileSync(join(before, 'shots.json'), 'utf8'))
  const b = JSON.parse(readFileSync(join(after, 'shots.json'), 'utf8'))
  const files = readdirSync(before).filter((f) => f.endsWith('.png'))
  const browser = await launch()
  const page = await browser.newPage()
  const report = []
  for (const file of files) {
    const name = file.slice(0, -4)
    let other
    try {
      other = readFileSync(join(after, file))
    } catch {
      report.push({ name, missing: true })
      continue
    }
    const urls = [readFileSync(join(before, file)), other].map((buf) => `data:image/png;base64,${buf.toString('base64')}`)
    // the two side by side on one canvas, and the share of the pixels that differ
    const r = await page.evaluate(async (urls) => {
      const [x, y] = await Promise.all(
        urls.map(async (u) => {
          const img = new Image()
          img.src = u
          await img.decode()
          return img
        }),
      )
      const w = Math.max(x.width, y.width)
      const h = Math.max(x.height, y.height)
      const data = [x, y].map((img) => {
        const c = new OffscreenCanvas(w, h)
        const g = c.getContext('2d', { willReadFrequently: true })
        g.drawImage(img, 0, 0)
        return g.getImageData(0, 0, w, h).data
      })
      let changed = 0
      for (let i = 0; i < data[0].length; i += 4) {
        if (Math.abs(data[0][i] - data[1][i]) + Math.abs(data[0][i + 1] - data[1][i + 1]) + Math.abs(data[0][i + 2] - data[1][i + 2]) > 24) changed++
      }
      const both = document.createElement('canvas')
      both.width = 2 * w + 12
      both.height = h
      const g = both.getContext('2d')
      g.fillStyle = '#d0006f'
      g.fillRect(0, 0, both.width, h)
      g.drawImage(x, 0, 0)
      g.drawImage(y, w + 12, 0)
      return { share: changed / (w * h), png: changed ? both.toDataURL('image/png').split(',')[1] : null }
    }, urls)
    const row = { name, changed: Number((100 * r.share).toFixed(2)), height: [a[name]?.height, b[name]?.height], bar: [a[name]?.bar, b[name]?.bar], overflow: b[name]?.overflow, headingFirst: b[name]?.headingFirst }
    report.push(row)
    if (r.png) writeFileSync(join(out, file), Buffer.from(r.png, 'base64'))
  }
  await browser.close()
  report.sort((p, q) => (q.changed ?? 100) - (p.changed ?? 100))
  writeFileSync(join(out, 'report.json'), JSON.stringify(report, null, 1))
  const same = report.filter((r) => r.changed === 0).length
  console.log(`${report.length} pairs: ${same} the same, ${report.length - same} differ (side by side in ${out})`)
  for (const r of report.filter((r) => r.missing || r.overflow > 0 || r.bar?.[0] !== r.bar?.[1])) console.log(' ', JSON.stringify(r))
}

if (command === 'take' && dirs.length === 1) await take(resolve(dirs[0]))
else if (command === 'compare' && dirs.length === 3) await compare(...dirs.map((d) => resolve(d)))
else {
  console.error('usage: node scripts/shots.mjs take <dir> | compare <before> <after> <out>')
  process.exit(2)
}
