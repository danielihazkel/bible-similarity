import { describe, expect, it } from 'vitest'
import type { ExplainResponse } from '../api/types'
import { rankFraction, similarityBand } from './format'
import { displayForm, joinTokens } from './hebrew'
import { highlightFor } from './highlight'
import { parseExclude, parseK, parseMode } from './urlState'

// Genesis 1:1 and Psalms 14:1 (end) as stored in verses.display_tokens.
const BERESHIT = 'בְּרֵאשִׁ֖ית'
const OSEH = 'עֹֽשֵׂה־'

describe('displayForm', () => {
  it('keeps everything with te‘amim', () => {
    expect(displayForm(BERESHIT, 'teamim')).toBe(BERESHIT)
  })
  it('strips cantillation and meteg for niqqud', () => {
    expect(displayForm(BERESHIT, 'niqqud')).toBe('בְּרֵאשִׁית')
    expect(displayForm(OSEH, 'niqqud')).toBe('עֹשֵׂה־')
  })
  it('keeps consonants, maqaf and sof pasuq only', () => {
    expect(displayForm(BERESHIT, 'consonants')).toBe('בראשית')
    expect(displayForm(OSEH, 'consonants')).toBe('עשה־')
    expect(displayForm('הָאָֽרֶץ׃', 'consonants')).toBe('הארץ׃')
    expect(displayForm('כׇּל־', 'consonants')).toBe('כל־')
  })
})

describe('joinTokens', () => {
  it('joins maqaf-bound words without a space', () => {
    expect(joinTokens(['אֵ֣ין', OSEH, 'טֽוֹב׃'])).toBe('אֵ֣ין עֹֽשֵׂה־טֽוֹב׃')
  })
})

describe('url state', () => {
  it('validates mode and k', () => {
    expect(parseMode('semantic')).toBe('semantic')
    expect(parseMode('bogus')).toBe('fused')
    expect(parseK('20')).toBe(20)
    expect(parseK('7')).toBe(10)
    expect(parseK(null)).toBe(10)
  })
  it('defaults and sanitizes exclude per unit type', () => {
    expect(parseExclude(null, 'verse')).toEqual(['neighbors'])
    expect(parseExclude(null, 'chapter')).toEqual([])
    expect(parseExclude('', 'verse')).toEqual([])
    expect(parseExclude('book,neighbors,x', 'verse')).toEqual(['neighbors', 'book'])
    expect(parseExclude('book,neighbors,chapter', 'pericope')).toEqual(['book'])
  })
})

describe('format', () => {
  it('maps ranks and cosines', () => {
    expect(rankFraction(1, 50)).toBe(1)
    expect(rankFraction(null, 50)).toBe(0)
    expect(rankFraction(26, 50)).toBe(0.5)
    expect(similarityBand(0.95)).toBe(4)
    expect(similarityBand(0.1)).toBe(0)
  })
})

describe('highlightFor', () => {
  const explain: ExplainResponse = {
    a: 1,
    b: 2,
    shared: [
      {
        lemma: '430',
        he_lemma: 'אלהים',
        formula: false,
        a_words: [{ idx: 2, display_idx: 2, in_formula: false }],
        b_words: [{ idx: 0, display_idx: 0, in_formula: false }],
      },
      {
        lemma: '559',
        he_lemma: 'יאמר',
        formula: true,
        a_words: [
          { idx: 3, display_idx: 3, in_formula: true },
          { idx: 4, display_idx: null, in_formula: true },
        ],
        b_words: [{ idx: 1, display_idx: 0, in_formula: true }],
      },
    ],
  }
  it('marks shared and formula words, skipping unaligned ones', () => {
    expect([...highlightFor(explain, 'a')]).toEqual([
      [2, 'shared'],
      [3, 'formula'],
    ])
    // token 0 of b carries both lemmas: shared wins over formula
    expect([...highlightFor(explain, 'b')]).toEqual([[0, 'shared']])
    expect(highlightFor(explain, 'a', '559').get(3)).toBe('focus')
    expect(highlightFor(undefined, 'a').size).toBe(0)
  })
})
