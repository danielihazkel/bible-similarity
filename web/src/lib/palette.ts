import { useMemo } from 'react'
import { useTheme } from '../context/themeContext'

// The colours of the charts that colour by a category (M176): tokens of global.css, each with its
// dark value there, never a colour written in a page's module.
//   --sec-0 … 2    the canon's three sections (checked for colour blindness, any pair, both themes)
//   --cl-0 … 11    the map's clusters, in turn
//   --dist-0 … 11  the districts of a place list, in turn
//   --seq-lo / hi  one hue from little to much (the share of a passage in a list)
// An SVG mark or a swatch takes the token itself (`sectionColour`, `districtColour`); a canvas
// takes no `var()`, so its page reads the values of the theme on screen (`usePalette`).

/** The canon's sections, in the order of their colours. */
export const SECTIONS = ['Torah', 'Prophets', 'Writings']
const CYCLE = 12

/** A section's place in the palette (an unknown one counts as the first). */
export const sectionIndex = (section: string | undefined) => Math.max(0, SECTIONS.indexOf(section ?? SECTIONS[0]))

/** The colour of the canon's section `i`, for a style. */
export const sectionColour = (i: number) => `var(--sec-${Math.min(Math.max(i, 0), SECTIONS.length - 1)})`

/** The colour of district `d` (from 1): twelve in turn, a 13th reuses the first. */
export const districtColour = (d: number) => `var(--dist-${(((d - 1) % CYCLE) + CYCLE) % CYCLE})`

type Rgb = [number, number, number]
const FALLBACK: Rgb = [136, 136, 136]

function parse(colour: string): Rgb {
  const m = /^#([0-9a-f]{6})$/i.exec(colour.trim())
  if (!m) return FALLBACK
  const n = parseInt(m[1], 16)
  return [n >> 16, (n >> 8) & 255, n & 255]
}

const rgba = ([r, g, b]: Rgb, alpha: number) => `rgba(${r}, ${g}, ${b}, ${alpha})`
const blend = (a: Rgb, b: Rgb, t: number): Rgb => [0, 1, 2].map((k) => Math.round(a[k] + (b[k] - a[k]) * t)) as Rgb

function token(name: string): Rgb {
  if (typeof document === 'undefined') return FALLBACK
  return parse(getComputedStyle(document.documentElement).getPropertyValue(name))
}

export interface Palette {
  /** Section `i`'s colour at an opacity. */
  section: (i: number, alpha?: number) => string
  /** Cluster `i`'s colour at an opacity: twelve in turn, the second round a step away in lightness. */
  cluster: (i: number, alpha?: number) => string
  /** A share (0–1) on the one-hue ramp, at an opacity. */
  share: (share: number, alpha?: number) => string
}

/** The palettes' values in the theme on screen, for a canvas. Read again when the theme changes. */
export function usePalette(): Palette {
  const { shade } = useTheme()
  return useMemo(() => {
    const sec = SECTIONS.map((_, i) => token(`--sec-${i}`))
    const cl = Array.from({ length: CYCLE }, (_, i) => token(`--cl-${i}`))
    const lo = token('--seq-lo')
    const hi = token('--seq-hi')
    // the second round of clusters: towards the page's ink, which is the dark end on a light page
    const ink: Rgb = shade === 'dark' ? [255, 255, 255] : [0, 0, 0]
    return {
      section: (i, alpha = 1) => rgba(sec[i] ?? sec[0], alpha),
      cluster: (i, alpha = 1) => {
        const k = ((i % CYCLE) + CYCLE) % CYCLE
        return rgba(Math.floor(i / CYCLE) % 2 ? blend(cl[k], ink, 0.22) : cl[k], alpha)
      },
      share: (share, alpha = 1) => rgba(blend(lo, hi, Math.min(1, Math.max(0, share))), alpha),
    }
  }, [shade])
}
