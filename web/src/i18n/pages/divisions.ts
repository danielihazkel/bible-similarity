// Interface strings of the Divisions page: where the text turns, and where the tradition divided
// it (DESIGN.md §16.29). English first, Hebrew typed against it.

import type { Paragraph, SegmentKind } from '../../api/types'
import { countEn, numEn, pct } from '../fmt'

export const he = (k: Paragraph) => (k === 'pe' ? 'פ' : 'ס')

export const divEn = {
  title: 'Where the text divides',
  lede: (w: number) =>
    `Every boundary between two verses gets a score from the text alone: how much the words (lemmas) and the meaning (verse embeddings) of the ${w} verses before it differ from the ${w} after it, as a percentile within its book. 0.5 is a typical boundary; near 1 are the book's sharpest turns. The divisions the tradition drew are then placed on it: the open (פ) and closed (ס) paragraphs of two manuscript traditions, the chapters (added in the 13th century), the weekly parashot and the style seams.`,
  noData: 'Not computed in this build: run `bsim segments`, then `bsim build-db`.',
  tests: 'Do the divisions follow the text?',
  testsLede:
    'The mean score of the boundaries of each kind, against the same number of boundaries drawn at random in each book (999 draws); p is the share of draws scoring as high. Words and meaning: the two signals alone.',
  cols: { kind: 'Division', n: 'Boundaries', score: 'Score', lex: 'Words', sem: 'Meaning', p: 'p' },
  groups: {
    mam_pe: 'Open paragraph פ (MAM)',
    mam_samekh: 'Closed paragraph ס (MAM)',
    oshb_pe: 'Open paragraph פ (Leningrad)',
    oshb_samekh: 'Closed paragraph ס (Leningrad)',
    agreed: 'A break in both traditions',
    single: 'A break in one tradition only',
    chapter_break: 'Chapter start at a paragraph break',
    chapter_only: 'Chapter start with no paragraph break',
    parasha: 'Start of a weekly parasha',
    seam: 'Style seam',
    unmarked: 'No division',
  } as Record<string, string>,
  peSamekh: (a: string, b: string, p: string) =>
    `Open paragraphs (פ) score ${a}, closed ones (ס) ${b}; with the two labels shuffled among them in each book, p ${p}.`,
  agreedSingle: (a: string, b: string, p: string) =>
    `Breaks that both traditions mark score ${a}, breaks only one of them marks ${b}; p ${p}.`,
  chapter: (a: string, b: string, p: string) =>
    `Chapters that start at a paragraph break score ${a}, chapters that start without one ${b}; p ${p}.`,
  seams: (share: number, nul: number, near: number, p: string) =>
    `${pct(share)} of the style seams lie within ${countEn(near, 'verse', 'verses')} of a paragraph break or a chapter start, against ${pct(nul)} of random boundaries (p ${p}).`,
  agreement: (ref: 'mam' | 'chapter', better: number, books: number, pk: string, pkNull: string) =>
    `As a segmentation: a book's sharpest turns, as many as its ${ref === 'mam' ? 'MAM paragraph breaks' : 'chapters'}, match them better than random boundaries in ${numEn(better)} of ${numEn(books)} books (mean Pk ${pk} against ${pkNull}; lower is closer).`,
  calibration: (score: string, p: string) =>
    `Check of the test: the MAM breaks shuffled inside each book score ${score} (p ${p}), as chance should.`,
  window: (w: number, grid: string) =>
    `Window: ${countEn(w, 'verse', 'verses')} on each side, chosen on the dev books (mean score of the MAM breaks by window: ${grid}).`,
  caveat:
    'Cohesion is one reason to divide a text, not the only one: a list is divided item by item, a reading by the calendar, and a window several verses wide blurs a turn by a verse or two. A low score does not make a division wrong.',
  book: 'Book',
  chapter_: 'Chapter',
  allChapters: 'All chapters',
  bookTitle: 'One book',
  pickBook: 'Choose a book to see the score of each of its boundaries and where its divisions fall.',
  chart: (book: string) => `The score of every boundary in ${book}, with its divisions`,
  legend: { pe: 'Open פ (MAM)', samekh: 'Closed ס (MAM)', chapter: 'Chapter start', other: 'No paragraph break' },
  bookAgreement: (ref: 'mam' | 'chapter', pk: string, pkNull: string, p: string) =>
    `${ref === 'mam' ? 'MAM paragraphs' : 'Chapters'}: Pk ${pk} against ${pkNull} for random boundaries (p ${p}).`,
  bar: (label: string, score: string) => `${label}: score ${score}`,
  listTitle: 'Where the text and the divisions disagree',
  kinds: {
    turn: {
      label: 'Unmarked turns',
      hint: "A book's sharpest turns (score ≥ 0.97) with no paragraph break or chapter within a verse",
    },
    cut: {
      label: 'Chapters in running text',
      hint: 'Chapter starts with no paragraph break in either tradition, where the text runs on (score ≤ 0.25)',
    },
    quiet: {
      label: 'Quiet paragraph breaks',
      hint: 'MAM paragraph breaks where the text hardly changes (score ≤ 0.05): often a list divided item by item',
    },
  } satisfies Record<SegmentKind, { label: string; hint: string }>,
  anyKind: 'Every kind',
  none: 'None here.',
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'boundary', 'boundaries')} · page ${numEn(page)} of ${numEn(pages)}`,
  score: (s: string) => `score ${s}`,
  scoreTitle: "Within-book percentile of the drop in cohesion (1 = the book's sharpest turn)",
  tags: {
    mam: (k: Paragraph) => `MAM ${he(k)}`,
    oshb: (k: Paragraph) => `Leningrad ${he(k)}`,
    chapter: 'chapter start',
    seam: 'style seam',
  },
  boundary: 'the boundary',
}
