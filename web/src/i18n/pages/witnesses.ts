// Interface strings of the other witnesses page (DESIGN.md §16.78): the Samaritan Pentateuch and
// the Dead Sea Scrolls against the MT. English first, Hebrew typed against it.

import { countEn, numEn } from '../fmt'

export type WitnessKind = 'sp' | 'scroll'
export type WitnessOp = 'same' | 'spelling' | 'form' | 'substitution' | 'omitted' | 'added' | 'moved'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))

export const wtEn = {
  title: 'Other witnesses',
  lede: 'The Samaritan Pentateuch and the Dead Sea Scrolls against the Masoretic text, word by word: where they spell a word otherwise, read another word, or have words the Masoretic text lacks. A scroll’s word counts only where none of its letters is restored by an editor.',
  sources: 'The Samaritan Pentateuch of the Halle Samaritanus project (DT-UCPH / CACCHT) and the biblical scrolls from Martin Abegg’s data (ETCBC), both',
  licence: 'CC BY-NC 4.0',
  sourcesNote: ': for non-commercial use.',
  notComputed: 'The other witnesses were not compared in this build (run bsim download --only witnesses, then bsim witnesses).',
  described: (spVerses: number, scrolls: number, scrollVerses: number, read: number) =>
    `The Samaritan Pentateuch in ${countEn(spVerses, 'verse', 'verses')}; ${countEn(scrolls, 'scroll', 'scrolls')} in ${countEn(scrollVerses, 'verse copy', 'verse copies')}, ${countEn(read, 'word', 'words')} of them read whole.`,
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  parallel: {
    title: 'The Samaritan adds most where the Torah has a parallel',
    text: (inPar: number, elsewhere: number, ratio: number, nullMean: number, p: number, shifts: number, n: number) =>
      `Of the ${numEn(n)} Torah verses with a parallel elsewhere in the Torah, ${(inPar * 100).toFixed(1)}% carry a Samaritan plus, against ${(elsewhere * 100).toFixed(1)}% of the others: ${ratio.toFixed(2)} times, against ${nullMean.toFixed(2)} when the parallels are shifted round their books ${numEn(shifts)} times (p ${fp(p)}).`,
  },
  known: {
    title: 'Readings the witnesses are known to have',
    found: 'found',
    missing: 'not found',
    plus: (n: number) => `a plus of ${numEn(n)} words or more`,
    reads: 'reads',
    flood: (year: number | null, expected: number) => `The Samaritan Flood in year ${year === null ? '—' : numEn(year)} from Adam (known: ${numEn(expected)})`,
  },
  sp: 'Samaritan',
  scrolls: 'Scrolls',
  kindLabel: 'Witness',
  ops: {
    same: 'same',
    spelling: 'spelling',
    form: 'form',
    substitution: 'another word',
    omitted: 'lacking',
    added: 'added',
    moved: 'moved',
  } as Record<WitnessOp, string>,
  opsHint: 'Spelling: other vowel letters (ו, י). Form: one prefix or ending letter more or less. Another word: a different word in its place. Added: words only the witness has; lacking: words only the Masoretic text has.',
  plusesTitle: 'The largest pluses',
  plusesHint: 'Verses where the witness has the most words the Masoretic text lacks.',
  plusOf: (n: number) => countEn(n, 'word', 'words'),
  chronTitle: 'Two chronologies',
  chronHint: 'The years from Adam, read from the ages of Genesis 5 and 11 in each text. In the Samaritan, Jared, Methuselah and Lamech all die in the year of the Flood.',
  chronCols: { event: 'Event', verse: 'Verse', mt: 'Masoretic', sp: 'Samaritan', gap: 'Difference' },
  booksTitle: 'Book by book',
  cols: { book: 'Book', verses: 'Verses', words: 'Words', read: 'Read', variants: 'Variants per 100 words', pluses: 'Pluses', scroll: 'Scroll' },
  scrollsTitle: 'The scrolls with the most text',
  scrollsHint: (n: number) => `The ${numEn(n)} scrolls with the most words read whole; variants per 100 of those words, spelling left out.`,
  unitTitle: (label: string) => `The witnesses of ${label}`,
  unitNone: 'No other witness has these verses.',
  allVerses: 'Back to all the witnesses',
  readWith: 'Read with the witnesses',
  mt: 'Masoretic',
  lacks: 'Lacks',
  unread: 'restored by an editor or uncertain',
  legend: 'Key',
  limits: (plusMin: number, maxUnc: number) =>
    `A plus is ${numEn(plusMin)} or more words in a row that the witness has and the Masoretic text lacks. A scroll’s word is read when none of its letters is restored and none is less certain than degree ${numEn(maxUnc)}; restored words still anchor the alignment but are never counted. The Masoretic text is compared as read (the qere). Both datasets are machine-analysed; a word split or joined otherwise shows as a change.`,
  layerTitle: (sp: number | undefined, scrolls: number | undefined, scrollVariants: number | undefined) =>
    [sp !== undefined ? `the Samaritan: ${countEn(sp, 'variant', 'variants')}` : null, scrolls ? `${countEn(scrolls, 'scroll', 'scrolls')}: ${countEn(scrollVariants ?? 0, 'variant', 'variants')}` : null].filter(Boolean).join('; '),
  layerKey: 'Beside each verse, the variants of the Samaritan Pentateuch (ש) and of the scrolls (ק), spelling left out; choose one to compare.',
  layerNone: 'No other witness has these verses.',
  layerSp: 'ש',
  layerScroll: 'ק',
}
