// Interface strings of the vocabulary page (DESIGN.md §16.76): new words book by book, against
// Heaps' law; rare words. English first, Hebrew typed against it.

import { numEn } from '../fmt'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))
export const x2 = (x: number) => (x > 0 ? `+${x.toFixed(2)}` : x.toFixed(2))

export const vcEn = {
  title: 'Vocabulary over the canon',
  lede: 'Read in canon order, each book brings in words not found before it. Genesis brings in most of the vocabulary; a book read later brings in fewer, whatever its age. Here each book’s new words are set against what its length and its place predict, and against random orders of the books, so that its place in the canon does not decide.',
  notComputed: 'The vocabulary was not computed in this build (run bsim vocabulary).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  late: {
    title: 'The late books bring in more new words',
    text: (late: number, early: number, p: number, splits: number) =>
      `The late books (Chronicles, Ezra, Nehemiah, Esther, Daniel) have a mean novelty of ${x2(late)}, the early books (Genesis to Kings) ${x2(early)}: compared with every one of the ${numEn(splits)} ways to split those books into two such sets, p ${fp(p)}.`,
  },
  known: {
    title: 'Job and the Song: rich in words found once',
    rank: (book: string, rank: number | null, atMost: number) =>
      `${book}: ${rank === null ? '–' : `${ordinal(rank)}`} by words found once per 1,000 words (expected in the first ${numEn(atMost)})`,
  },
  described: (words: number, lemmas: number, hapax: number, k: number, b: number) =>
    `${numEn(words)} words of ${numEn(lemmas)} lemmas (Hebrew, proper names and Aramaic left out); ${numEn(hapax)} lemmas found once. Heaps’ law over the canon: V = ${k.toFixed(2)} N^${b.toFixed(3)}.`,
  oneCorpus: (torah: number, prophets: number, writings: number) =>
    `Lemmas found in one part of the canon only: Torah ${numEn(torah)}, Prophets ${numEn(prophets)}, Writings ${numEn(writings)}.`,
  chartTitle: 'Novelty, book by book',
  chartLede: 'How many more (right) or fewer (left) new words a book brings in than Heaps’ law predicts for its length, averaged over random orders of the books (a log ratio).',
  chartLabel: 'Each book’s novelty in canon order, the early and late books coloured',
  legend: { early: 'Early books', late: 'Late books', other: 'Not compared' },
  readout: (book: string, n: number, exp: number, nov: number) =>
    `${book}: ${numEn(n)} new lemmas in canon order, ${exp.toFixed(1)} expected; novelty ${x2(nov)}`,
  tableTitle: 'Each book',
  cols: {
    book: 'Book',
    words: 'Words',
    lemmas: 'Lemmas',
    new: 'New',
    perK: 'New per 1,000',
    expected: 'Expected',
    novelty: 'Novelty',
    hapax: 'Found once',
    hapaxK: 'Once per 1,000',
    one: 'One part only',
  },
  limits: 'A lemma is OSHB’s, so a word written two ways or a homonym split differently counts as two; a book’s own words (its names left out) are all that counts, and a short book’s rates swing widely.',
  first: (ref: string) => `First used in ${ref}`,
  firstSection: { Torah: 'found in the Torah only', Prophets: 'found in the Prophets only', Writings: 'found in the Writings only' } as Record<string, string>,
  hapaxNote: 'found once in the Bible',
  books: (n: number) => (n === 1 ? 'in one book' : `in ${numEn(n)} books`),
}

function ordinal(n: number) {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : (['th', 'st', 'nd', 'rd'][n % 10] ?? 'th')
  return `${numEn(n)}${s}`
}
