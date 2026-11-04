// Renders the app's PNG icons (`node scripts/icons.mjs`) into public/, for the manifest of the
// offline app (vite.config.ts): the favicon's design (an aleph on the brown tile of
// public/favicon.svg) at 192 and 512 px, and a maskable 512 px one whose letter sits inside the
// safe zone (the middle 80%) on a full-bleed tile. The letter is the viewer's own Noto Serif
// Hebrew. Drawn in the installed Edge (as the e2e tests; Playwright's Chromium on CI).
import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const font = readFileSync(join(web, 'node_modules/@fontsource/noto-serif-hebrew/files/noto-serif-hebrew-hebrew-600-normal.woff2'))
const TILE = '#6b4f2a'
const INK = '#fdf8ef'

/** An icon `size` px square: the tile with rounded corners (`radius`, a share of the size) and
 * the letter at `scale` of the size. */
const page = (size, radius, scale) => `<!doctype html><html><head><style>
@font-face { font-family: icon; src: url(data:font/woff2;base64,${font.toString('base64')}) format('woff2'); }
html, body { margin: 0; background: transparent; }
div { width: ${size}px; height: ${size}px; border-radius: ${radius * size}px; background: ${TILE};
  color: ${INK}; font: 600 ${scale * size}px/1 icon; display: flex; align-items: center; justify-content: center; }
span { transform: translateY(3%); }
</style></head><body><div><span>א</span></div></body></html>`

const ICONS = [
  ['icon-192.png', 192, 7 / 32, 0.8],
  ['icon-512.png', 512, 7 / 32, 0.8],
  ['icon-maskable-512.png', 512, 0, 0.6],
]

const browser = await chromium.launch({ channel: process.env.CI ? undefined : 'msedge' })
for (const [name, size, radius, scale] of ICONS) {
  const p = await browser.newPage({ viewport: { width: size, height: size } })
  await p.setContent(page(size, radius, scale))
  await p.evaluate(() => document.fonts.ready)
  await p.locator('div').screenshot({ path: join(web, 'public', name), omitBackground: true })
  await p.close()
  console.log(`public/${name}`)
}
await browser.close()
