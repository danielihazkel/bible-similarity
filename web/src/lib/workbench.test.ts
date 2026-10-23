import { describe, expect, it } from 'vitest'
import { addItem, formatP, joinSet, parseRange, patternFor, removeItem, splitSet } from './workbench'

describe('workbench sets', () => {
  it('reads and writes a set item by item', () => {
    expect(splitSet(' Book:1-3 ;; pattern:[lemma=430] ..2 [] ;odd')).toEqual([
      { kind: 'book', value: '1-3' },
      { kind: 'pattern', value: '[lemma=430] ..2 []' },
      { kind: '', value: 'odd' },
    ])
    expect(joinSet(splitSet('book:1;chapters:26:42-83'))).toBe('book:1; chapters:26:42-83')
    expect(addItem('book:1', { kind: 'section', value: 'torah' })).toBe('book:1; section:torah')
    expect(addItem('book:1', { kind: 'book', value: '1' })).toBe('book:1') // already there
    expect(addItem('', { kind: 'only', value: 'speech' })).toBe('only:speech')
    expect(removeItem('book:1; section:torah; only:speech', 1)).toBe('book:1; only:speech')
    expect(removeItem('book:1', 0)).toBe('')
  })

  it('reads ranges, formats p and builds the pattern of a value', () => {
    expect(parseRange('42-83')).toEqual([42, 83])
    expect(parseRange('5')).toEqual([5, 5])
    expect(parseRange('x')).toBeNull()
    expect([formatP(0.001), formatP(0.0456), formatP(1), formatP(9.6e-48), formatP(0)]).toEqual(['0.001', '0.046', '1', '9.6e-48', '0'])
    expect(patternFor('lemma', '430')).toBe('[lemma=430]')
    expect(patternFor('function', 'subj')).toBe('[function=subj]')
    expect(patternFor('domain', '001001')).toBeNull()
  })
})
