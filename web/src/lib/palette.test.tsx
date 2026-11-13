// @vitest-environment jsdom
import { cleanup, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it } from 'vitest'
import { ThemeContext } from '../context/themeContext'
import type { Shade } from './theme'
import { districtColour, sectionColour, sectionIndex, usePalette, type Palette } from './palette'

afterEach(() => {
  cleanup()
  document.documentElement.removeAttribute('style')
})

function paletteIn(shade: Shade): Palette {
  const wrapper = ({ children }: { children: ReactNode }) => <ThemeContext.Provider value={{ theme: shade, shade, setTheme: () => {} }}>{children}</ThemeContext.Provider>
  return renderHook(() => usePalette(), { wrapper }).result.current
}

describe('the chart palettes (M176)', () => {
  it('names a section’s and a district’s token', () => {
    expect(['Torah', 'Prophets', 'Writings', 'Apocrypha', undefined].map(sectionIndex)).toEqual([0, 1, 2, 0, 0])
    expect([0, 2, 7].map(sectionColour)).toEqual(['var(--sec-0)', 'var(--sec-2)', 'var(--sec-2)'])
    // districts count from 1; the 13th reuses the first, and a place with no district (0) the last
    expect([1, 12, 13, 0].map(districtColour)).toEqual(['var(--dist-0)', 'var(--dist-11)', 'var(--dist-0)', 'var(--dist-11)'])
  })

  it('reads the tokens’ values for a canvas, at an opacity', () => {
    const root = document.documentElement.style
    root.setProperty('--sec-1', '#eb6834')
    root.setProperty('--cl-0', '#204080')
    root.setProperty('--seq-lo', '#000000')
    root.setProperty('--seq-hi', '#ff8040')
    const p = paletteIn('light')
    expect(p.section(1)).toBe('rgba(235, 104, 52, 1)')
    expect(p.section(1, 0.5)).toBe('rgba(235, 104, 52, 0.5)')
    expect(p.cluster(0, 0.85)).toBe('rgba(32, 64, 128, 0.85)')
    // the second round of twelve: a step towards the ink (darker on a light page)
    expect(p.cluster(12)).toBe('rgba(25, 50, 100, 1)')
    expect(p.cluster(24)).toBe(p.cluster(0))
    expect([0, 0.5, 1, 7].map((s) => p.share(s))).toEqual(['rgba(0, 0, 0, 1)', 'rgba(128, 64, 32, 1)', 'rgba(255, 128, 64, 1)', 'rgba(255, 128, 64, 1)'])
  })

  it('steps the second round towards white on a dark page, and falls back to grey for a token that is not there', () => {
    document.documentElement.style.setProperty('--cl-0', '#204080')
    const p = paletteIn('dark')
    expect(p.cluster(12)).toBe('rgba(81, 106, 156, 1)')
    expect(p.section(0)).toBe('rgba(136, 136, 136, 1)')
  })
})
