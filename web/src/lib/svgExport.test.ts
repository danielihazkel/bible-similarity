// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { asLight, downloadSvg, lightTokens, standaloneSvg, xmlEscape } from './svgExport'

afterEach(() => {
  document.head.innerHTML = ''
  document.body.innerHTML = ''
  document.documentElement.removeAttribute('data-theme')
  vi.unstubAllGlobals()
})

describe('svgExport', () => {
  it('escapes text for markup', () => {
    expect(xmlEscape('a <b> & "c"')).toBe('a &lt;b&gt; &amp; &quot;c&quot;')
  })

  it('runs in the light theme and puts the theme back', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    expect(asLight(() => document.documentElement.getAttribute('data-theme'))).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    document.documentElement.removeAttribute('data-theme')
    asLight(() => 0)
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
  })

  it('makes a drawing standalone: the stylesheet’s look on each element, in the light theme', () => {
    document.head.innerHTML = `<style>
      :root { --ink: #111111 } :root[data-theme='dark'] { --ink: #eeeeee }
      .dot { fill: #aa0000; stroke: #000000; vector-effect: non-scaling-stroke }
      :root[data-theme='dark'] .dot { fill: #00ff00 }
    </style>`
    document.body.innerHTML = `<svg viewBox="0 0 100 50" role="img" aria-label="map" tabindex="0" class="m"><circle class="dot" cx="5" cy="5" r="2"><title>עיר</title></circle></svg>`
    document.documentElement.setAttribute('data-theme', 'dark') // the screen is dark
    const out = standaloneSvg(document.querySelector('svg')!, 'המפה')
    const doc = new DOMParser().parseFromString(out, 'image/svg+xml')
    expect(doc.getElementsByTagName('parsererror')).toHaveLength(0)
    const svg = doc.documentElement
    expect(svg.getAttribute('xmlns')).toBe('http://www.w3.org/2000/svg')
    expect(svg.hasAttribute('class') || svg.hasAttribute('tabindex') || svg.hasAttribute('role')).toBe(false)
    expect(svg.getAttribute('width')).toBe('100')
    expect(svg.firstElementChild!.tagName).toBe('title')
    expect(svg.firstElementChild!.textContent).toBe('המפה')
    const dot = doc.querySelector('circle')!
    expect(dot.hasAttribute('class')).toBe(false)
    expect(dot.getAttribute('style')).toMatch(/fill:\s*(#aa0000|rgb\(170, 0, 0\))/)
    expect(doc.querySelector('circle title')!.textContent).toBe('עיר')
    // a stroke kept thin by the stylesheet stays thin
    expect(dot.getAttribute('style')).toMatch(/vector-effect:\s*non-scaling-stroke/)
    // what the circle inherits as it is is not written again
    expect(dot.getAttribute('style')).not.toMatch(/fill-rule/)
    expect(out.match(/xmlns=/g)).toHaveLength(1)
    expect(lightTokens({ ink: '--ink', none: '--none' })).toEqual({ ink: '#111111' })
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('saves the markup as an SVG file', async () => {
    let blob: Blob | undefined
    vi.stubGlobal('URL', {
      createObjectURL: (b: Blob) => {
        blob = b
        return 'blob:x'
      },
      revokeObjectURL: () => undefined,
    })
    downloadSvg('map.svg', '<svg/>')
    expect(blob!.type).toBe('image/svg+xml;charset=utf-8')
    expect(await blob!.text()).toBe('<svg/>')
  })
})
