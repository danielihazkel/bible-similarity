// Drawings saved as SVG files (DESIGN.md §11.1, print and export): a drawing on the page made
// standalone (its stylesheet's look written onto each element, in the light theme, for paper),
// and the text escaped for drawings written as markup (the family tree's poster).
import { downloadText } from './csv'

export const SVG_NS = 'http://www.w3.org/2000/svg'

/** Text and attribute values for SVG markup. */
export const xmlEscape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

/** The look an element takes from the stylesheet, written onto its copy: these are inherited, so
 * an element gets only those that differ from its parent's (the drawing's root gets them all). */
const LOOK = [
  'fill',
  'fill-opacity',
  'fill-rule',
  'stroke',
  'stroke-width',
  'stroke-opacity',
  'stroke-dasharray',
  'stroke-linecap',
  'stroke-linejoin',
  'font-family',
  'font-size',
  'font-weight',
  'font-style',
  'text-anchor',
  'dominant-baseline',
  'paint-order',
  'visibility',
]

/** Run with the light theme's tokens (the stylesheet's dark tokens apply only under
 * `data-theme="dark"`, lib/theme.ts): what is saved or printed is for paper. Synchronous, so
 * nothing repaints, and the theme in use is put back. */
export function asLight<T>(f: () => T): T {
  const root = document.documentElement
  const was = root.getAttribute('data-theme')
  root.setAttribute('data-theme', 'light')
  try {
    return f()
  } finally {
    if (was === null) root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', was)
  }
}

/** A drawing on the page as a file of its own: each element's look from the stylesheet written on
 * it (in the light theme), classes, focus and handlers dropped, a title, a size in pixels as drawn. */
export function standaloneSvg(svg: SVGSVGElement, title: string): string {
  return asLight(() => {
    const copy = svg.cloneNode(true) as SVGSVGElement
    const from = [svg, ...svg.querySelectorAll<SVGElement>('*')]
    const to = [copy, ...copy.querySelectorAll<SVGElement>('*')]
    const seen = new Map<Element, CSSStyleDeclaration>()
    from.forEach((el, i) => {
      const cs = getComputedStyle(el)
      seen.set(el, cs)
      const up = el === svg ? undefined : seen.get(el.parentElement!)
      const look = LOOK.map((p) => [p, cs.getPropertyValue(p)] as const).filter(([p, v]) => v && !v.startsWith('depends') && v !== up?.getPropertyValue(p))
      // not inherited: an element's own opacity, a stroke kept thin however far the map is zoomed
      // (in map units it would cover the map), and those not shown
      if (cs.opacity && cs.opacity !== '1') look.push(['opacity', cs.opacity])
      const ve = cs.getPropertyValue('vector-effect')
      if (ve && ve !== 'none') look.push(['vector-effect', ve])
      if (cs.display === 'none') look.push(['display', 'none'])
      const out = to[i]
      out.removeAttribute('class')
      out.removeAttribute('tabindex')
      if (look.length) out.setAttribute('style', look.map(([p, v]) => `${p}:${v}`).join(';'))
      else out.removeAttribute('style')
    })
    copy.removeAttribute('role')
    copy.removeAttribute('aria-label')
    const r = svg.getBoundingClientRect()
    const vb = svg.viewBox?.baseVal
    const w = r.width || vb?.width || 0
    const h = r.height || vb?.height || 0
    if (w && h) {
      copy.setAttribute('width', String(Math.round(w)))
      copy.setAttribute('height', String(Math.round(h)))
    }
    const t = document.createElementNS(SVG_NS, 'title')
    t.textContent = title
    copy.insertBefore(t, copy.firstChild)
    return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(copy)}\n`
  })
}

/** Save SVG markup as a file. */
export function downloadSvg(filename: string, markup: string): void {
  downloadText(filename, [markup], 'image/svg+xml;charset=utf-8')
}

/** Tokens of the stylesheet in the light theme, by key (those not set, as where the stylesheet is
 * not loaded, left out). */
export function lightTokens<K extends string>(tokens: Partial<Record<K, string>>): Partial<Record<K, string>> {
  return asLight(() => {
    const cs = getComputedStyle(document.documentElement)
    const out: Partial<Record<K, string>> = {}
    for (const [k, name] of Object.entries(tokens) as [K, string][]) {
      const v = cs.getPropertyValue(name).trim()
      if (v) out[k] = v
    }
    return out
  })
}
