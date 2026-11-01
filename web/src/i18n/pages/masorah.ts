// Interface strings of Patterns → The Masorah's counts: the middle letter, words and verse of the
// Torah and each book's verses, counted on this text (DESIGN.md §16.55). English first, Hebrew
// typed against it.

import type { MasorahReason, MasorahText } from '../../api/types'
import { countEn, numEn } from '../fmt'

export type Unit = 'letter' | 'word' | 'verse'
type TotalUnit = 'verses' | 'words' | 'letters'
type Source = 'masorah' | 'talmud' | 'soferim' | 'printed'

/** A distance in units, whole or with its half. */
export const fd = (d: number, num: (n: number) => string) => num(Math.abs(d))
const ordEn = (k: number) => {
  const s = k % 100 >= 11 && k % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[k % 10] ?? 'th'
  return `${numEn(k)}${s}`
}
const unitEn: Record<Unit, [string, string]> = { letter: ['letter', 'letters'], word: ['word', 'words'], verse: ['verse', 'verses'] }
export const unitHe: Record<Unit, [string, string, string]> = {
  letter: ['אות אחת', 'שתי אותיות', 'אותיות'],
  word: ['תיבה אחת', 'שתי תיבות', 'תיבות'],
  verse: ['פסוק אחד', 'שני פסוקים', 'פסוקים'],
}

export const msrEn = {
  title: 'The Masorah’s counts',
  lede: 'The first scribes were called soferim, counters, “because they counted all the letters of the Torah” (Kiddushin 30a): the ו of גחון is its middle letter, דרש דרש its middle words. The Masorah’s notes give the middle verse of each book and how many verses each book holds. Here the same things are counted on this text, in its letters as written (ketiv) and as read (qere): where each middle falls against ours, and why a total differs. It checks the text and its verse division; it is not a test against chance.',
  noData: 'Not computed in this build: run `bsim masorah`, then `bsim build-db`.',
  summary: (verses: number, wk: number, lk: number, wq: number, lq: number) =>
    `Counted here, the Torah has ${numEn(verses)} verses: as written, ${numEn(wk)} words and ${numEn(lk)} letters; as read, ${numEn(wq)} words and ${numEn(lq)} letters.`,
  kq: (pairs: number, k: number, q: number) =>
    `The two texts differ at the ${numEn(pairs)} places where the Leningrad Codex writes one thing and reads another. The text shown here reads the qere but keeps the written letters of some words, so ${countEn(k, 'word was', 'words were')} rewritten for the written text and ${numEn(q)} for the read one.`,
  text: 'Letters',
  texts: { ketiv: 'As written', qere: 'As read' } satisfies Record<MasorahText, string>,
  middlesTitle: 'The middles',
  middlesLede: (tol: number) =>
    `A span of n letters, words or verses has its middle halfway, between two of them when n is even. A middle the tradition names lands when it is at most ${countEn(tol, 'unit', 'units')} from ours.`,
  torah: 'The Torah',
  units: { letter: 'the middle letter', word: 'the middle words', verse: 'the middle verse' } satisfies Record<Unit, string>,
  heading: (span: string, unit: string) => `${span}: ${unit}`,
  sources: { masorah: 'the Masorah', talmud: 'Kiddushin 30a', soferim: 'Tractate Soferim 9:3', printed: 'the count printed at the end of Deuteronomy' } satisfies Record<Source, string>,
  verdict: { holds: 'lands', fails: 'off' },
  tradLetter: (k: number, word: string) => `the ${ordEn(k)} letter of ${word}`,
  tradWords: (words: string) => {
    const w = words.split(' ')
    return w.length === 2 ? `between ${w[0]} and ${w[1]}` : words
  },
  says: (source: string) => `According to ${source}:`,
  ours: 'Here:',
  oursLetter: (k: number, word: string) => `the ${ordEn(k)} letter of ${word}`,
  position: (unit: Unit, pos: number, n: number, even: boolean) =>
    even
      ? `between ${unitEn[unit][0]} ${numEn(pos)} and ${numEn(pos + 1)} of ${numEn(n)}`
      : `${unitEn[unit][0]} ${numEn(pos)} of ${numEn(n)}`,
  distance: (unit: Unit, d: number, verses: number) =>
    d === 0
      ? 'It is ours exactly.'
      : `It falls ${fd(d, numEn)} ${unitEn[unit][Math.abs(d) === 1 ? 0 : 1]} ${d > 0 ? 'after' : 'before'} ours${unit !== 'verse' && verses !== 0 ? `, ${countEn(Math.abs(verses), 'verse', 'verses')} ${verses > 0 ? 'on' : 'back'}` : ''}.`,
  tradVerse: 'The tradition’s place',
  ourVerse: 'Ours',
  // totals
  totalsTitle: 'Verses in each book',
  totalsLede:
    'The Masorah closes each book with the number of its verses; Samuel, Kings, the Twelve, Ezra–Nehemiah and Chronicles are one book each. The figures are those most manuscripts give, as Ginsburg collates them; other figures they give are listed.',
  cols: { book: 'Book', tradition: 'The Masorah', ours: 'Here', diff: 'Difference', why: 'Why', also: 'Other manuscripts' },
  groups: {
    samuel: 'Samuel',
    kings: 'Kings',
    twelve: 'The Twelve',
    ezra: 'Ezra–Nehemiah',
    chronicles: 'Chronicles',
    torah: 'Torah',
    prophets: 'Prophets',
    writings: 'Writings',
    bible: 'The whole Bible',
  } as Record<string, string>,
  reasons: {
    split: 'The Masorah counts this verse as two (it carries two sets of accents):',
    decalogue: 'The Ten Commandments are divided otherwise: 12 verses in the Masorah’s count, 13 here:',
    absent: 'The Masorah’s count leaves out two verses this text has (manuscripts that have them give the same total):',
    untraced: 'Counting chapter by chapter gives this text’s figure; where the Masorah’s differs is not known.',
    witnesses: 'The manuscripts disagree, and another figure they give is this text’s.',
  } satisfies Record<MasorahReason, string>,
  agree: 'agrees',
  booksAgree: (agree: number, n: number) => `${numEn(agree)} of ${numEn(n)} books have the Masorah’s total.`,
  sectionsTitle: 'Sections and the whole',
  sectionsLede:
    'The totals given for the sections and the whole, and for the Torah in words and letters. Where the Masorah gives the totals of a section’s books, their sum is shown: the section totals do not always add up from them.',
  sectionCols: { section: 'Section', count: 'Count', source: 'Given by', tradition: 'Given', ours: 'Here', diff: 'Difference', bookSum: 'Its books added' },
  totalUnits: { verses: 'Verses', words: 'Words', letters: 'Letters' } satisfies Record<TotalUnit, string>,
  countOf: (unit: string, text: string | null) => (text ? `${unit} (${text.toLowerCase()})` : unit),
  booksTitle: 'Each book, counted',
  booksCols: { book: 'Book', verses: 'Verses', wordsK: 'Words written', wordsQ: 'Words read', lettersK: 'Letters written', lettersQ: 'Letters read' },
}
