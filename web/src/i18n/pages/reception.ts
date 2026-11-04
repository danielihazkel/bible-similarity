// Interface strings of the rabbinic reception page (DESIGN.md §16.77): where the Mishnah, the
// Tosefta and the two Talmuds cite the Bible. English first, Hebrew typed against it.

import { countEn, numEn } from '../fmt'
import { register } from '../en'

export type Corpus = 'mishnah' | 'tosefta' | 'bavli' | 'yerushalmi'
export type CorpusChoice = Corpus | 'all'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))

export const rcEn = {
  title: 'Rabbinic reception',
  lede: 'Where the Mishnah, the Tosefta and the two Talmuds cite the Bible, verse by verse. Which books, chapters and verses did the rabbis read most? Each citation links to its passage on Sefaria, in Hebrew; the rabbinic texts themselves are not shown here.',
  source: 'Citations from Sefaria’s links',
  sourceLicence: 'CC BY 4.0',
  sourceNote: ': which passage cites which verse.',
  notComputed: 'The rabbinic citations were not computed in this build (run bsim reception).',
  described: (citations: number, verses: number, passages: number) =>
    `${countEn(citations, 'citation', 'citations')} (a rabbinic passage with a verse) of ${countEn(verses, 'verse', 'verses')}, from ${countEn(passages, 'passage', 'passages')}.`,
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  law: {
    title: 'The Mishnah cites the Torah’s law more than its stories',
    text: (ratio: number, p: number, shifts: number, legal: number, narrative: number) =>
      `Per verse, the Mishnah cites the Torah’s legal blocks (${countEn(legal, 'verse', 'verses')}: the Covenant Code, Leviticus, the laws of Numbers, the Deuteronomic Code) ${ratio.toFixed(2)} times as often as the other ${numEn(narrative)}. Against the same blocks shifted round their books ${numEn(shifts)} times: p ${fp(p)}.`,
  },
  bavli: {
    title: 'The Bavli, with its stories and sermons, leans to the law less',
    text: (mishnah: number, bavli: number, gap: number, p: number) =>
      `The law over the rest, per verse: ${mishnah.toFixed(2)} in the Mishnah, ${bavli.toFixed(2)} in the Bavli. The gap of ${gap.toFixed(2)} against the two corpora’s citations of the Torah shuffled between them: p ${fp(p)}.`,
  },
  known: {
    title: 'Citations the tradition knows',
    found: 'found',
    missing: 'not found',
  },
  ratiosTitle: 'The law over the rest of the Torah, per verse',
  corpora: { mishnah: 'Mishnah', tosefta: 'Tosefta', bavli: 'Bavli', yerushalmi: 'Yerushalmi' } as Record<Corpus, string>,
  all: 'All four',
  corpusLabel: 'Cited in',
  stripTitle: 'Chapter by chapter',
  stripHint: 'Each square a chapter, darker where its verses are cited more often; choose one to read it with its citations.',
  stripLabel: (book: string) => `${book}: each chapter’s citations per verse`,
  chapterTitle: (chapter: string, n: number, verses: number) => `${chapter}: ${countEn(n, 'citation', 'citations')}, ${(n / verses).toFixed(2)} per verse`,
  legend: { label: 'Citations per verse', none: 'none', range: (lo: number, hi: number | null) => (hi === null ? `${lo.toFixed(1)}+` : `${lo.toFixed(1)}–${hi.toFixed(1)}`) },
  booksTitle: 'Each book',
  cols: { book: 'Book', verses: 'Verses', total: 'Citations', perVerse: 'Per verse', verse: 'Verse' },
  topTitle: 'The verses cited most',
  topIn: (book: string) => `The verses of ${book} cited most`,
  allBooks: 'Every book',
  unitTitle: (label: string) => `Who cites ${label}`,
  unitNone: 'No passage of the Mishnah, the Tosefta or the Talmuds cites these verses in Sefaria’s links.',
  allVerses: 'Back to every verse',
  onSefaria: '(on Sefaria, in a new tab)',
  readWith: 'Read with its citations',
  limits: (span: number, long: number) =>
    `A link is Sefaria’s: a quotation, an allusion, or a passage tied to the verse by an editor. A link to more than ${numEn(span)} verses (a chapter, a passage; ${numEn(long)} of them) is not counted per verse. Commentaries on these texts, other editions and Alfasi’s code are left out.`,
  // the reader's layer
  layerTitle: (n: number, parts: string) => `cited ${countEn(n, 'time', 'times')} in the rabbinic texts: ${parts}`,
  layerKey: 'Beside each verse, how many passages of the Mishnah, the Tosefta and the Talmuds cite it; choose it for the list.',
  layerNone: 'No verse here is cited.',
}

register('rc', rcEn)
