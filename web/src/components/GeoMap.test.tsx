// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { GeoMap } from './GeoMap'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('GeoMap', () => {
  it('saves the map as drawn as an SVG file', async () => {
    let blob: Blob | undefined
    let name = ''
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: (b: Blob) => ((blob = b), 'blob:x'), revokeObjectURL: () => undefined }))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      name = this.download
    })
    render(
      <LocaleProvider initial="en">
        <GeoMap
          basemap={{ shapes: [{ layer: 'land', rings: [[[34, 31], [36, 31], [36, 33], [34, 33]]] }] } as never}
          points={[{ place_id: 1, he: 'ירושלים', kind: 'town', lat: 31.78, lon: 35.22, n: 600 }]}
          bounds={{ lon0: 34, lat0: 31, lon1: 36, lat1: 33 }}
          onSelect={() => undefined}
          label="Places"
          labels={1}
          file="places"
        />
      </LocaleProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Save as SVG' }))
    expect(name).toBe('places.svg')
    const svg = await blob!.text()
    expect(svg).toMatch(/^<\?xml/)
    expect(svg).toContain('<title>Places</title>')
    expect(svg).toContain('ירושלים')
    expect(svg).not.toContain('class=')
    click.mockRestore()
  })
})
