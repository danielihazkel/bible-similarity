// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadCsv, toCsv } from './csv'

afterEach(() => vi.restoreAllMocks())

describe('toCsv', () => {
  it('writes a header and quotes cells that need it', () => {
    const csv = toCsv([
      { a: 'Genesis 1:1', b: 'תהו, ובהו', n: 3, empty: null },
      { a: 'say "hi"', b: 'line\nbreak', n: 0.5, empty: undefined },
    ])
    expect(csv).toBe('a,b,n,empty\r\nGenesis 1:1,"תהו, ובהו",3,\r\n"say ""hi""","line\nbreak",0.5,\r\n')
    expect(toCsv([])).toBe('')
  })

  it('downloads a BOM-prefixed UTF-8 file', async () => {
    let blob: Blob | undefined
    vi.spyOn(URL, 'createObjectURL').mockImplementation((b) => {
      blob = b as Blob
      return 'blob:x'
    })
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    downloadCsv('names.csv', [{ name: 'משה' }])
    expect(click).toHaveBeenCalledOnce()
    const bytes = new Uint8Array(await blob!.arrayBuffer())
    expect([...bytes.slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf])
    expect(new TextDecoder().decode(bytes.slice(3))).toBe('name\r\nמשה\r\n')
  })
})
