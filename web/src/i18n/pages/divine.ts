// Interface strings of the divine names page (DESIGN.md §16.65): each chapter's mix of יהוה and
// אלהים, the books whose mix changes, the Elohistic Psalter and the doubled psalms. English
// first, Hebrew typed against it. The names themselves are Hebrew in both.

import type { DivineName } from '../../api/types'
import { countEn, numEn } from '../fmt'

/** The names as the text writes them (scripture: the same in both interfaces). */
export const NAMES: Record<DivineName, string> = {
  yhwh: 'יהוה',
  elohim: 'אלהים',
  adonai: 'אדני',
  el: 'אל',
  eloah: 'אלוה',
  shaddai: 'שדי',
  yah: 'יה',
  elyon: 'עליון',
  tsevaot: 'צבאות',
}
export const pct = (x: number, locale: string) => `${Math.round(x * 100).toLocaleString(locale)}%`
export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const dvEn = {
  title: 'Names of God',
  lede: 'Which name of God each chapter uses: \u2068יהוה\u2069, \u2068אלהים\u2069, \u2068אדני\u2069, \u2068אל\u2069, \u2068אלוה\u2069, \u2068שדי\u2069, \u2068יה\u2069, \u2068עליון\u2069 and \u2068צבאות\u2069, counted from the lemmas. The strip below colours every chapter by the mix of the two commonest, and each book is cut where its mix changes most.',
  names: NAMES,
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  elohistic: {
    title: 'The Elohistic Psalter, found without being named',
    notSplit: 'Psalms was not split in this build.',
    text: (first: number, last: number, named: [number, number], shares: number[], p: number) =>
      `Cut in three where the mix of \u2068יהוה\u2069 and \u2068אלהים\u2069 changes most, Psalms falls into 1–${numEn(first - 1)}, ${numEn(first)}–${numEn(last)} and ${numEn(last + 1)}–150, with \u2068יהוה\u2069 ${shares.map((s) => pct(s, 'en-US')).join(', ')} of the two. The middle part named in advance is ${numEn(named[0])}–${numEn(named[1])}; against the same cut of the psalms shuffled, p ${fp(p)}.`,
  },
  doubled: {
    title: 'The doubled psalms',
    text: (eWard: number, yWard: number, p: number, n: number) =>
      `In ${countEn(n, 'psalm found twice', 'psalms found twice')}, aligned word by word: the copy inside Psalms 42–83 has \u2068אלהים\u2069 where the other has \u2068יהוה\u2069 ${countEn(eWard, 'time', 'times')}, and the reverse ${countEn(yWard, 'time', 'times')} (sign test, p ${fp(p)}).`,
    missing: (refs: string) => `Not in this corpus: ${refs}.`,
  },
  stripTitle: 'Across the canon',
  stripHint: 'Each square is a chapter, coloured by \u2068יהוה\u2069’s share of \u2068יהוה\u2069 and \u2068אלהים\u2069; a bar marks a cut where a book’s mix changes beyond chance (q ≤ 0.05). Select a chapter to read it with the names marked.',
  legend: { label: 'Legend', allE: 'all \u2068אלהים\u2069', even: 'even', allY: 'all \u2068יהוה\u2069', none: 'neither name' },
  chapterTitle: (label: string, y: number, e: number, other: number) =>
    `${label}: \u2068יהוה\u2069 ${numEn(y)}, \u2068אלהים\u2069 ${numEn(e)}${other ? `, other names ${numEn(other)}` : ''}`,
  stripLabel: (book: string) => `${book}: chapters by the mix of the names`,
  booksTitle: 'Books',
  cols: {
    book: 'Book',
    chapters: 'Chapters',
    yhwh: '\u2068יהוה\u2069',
    elohim: '\u2068אלהים\u2069',
    other: 'Other names',
    share: '\u2068יהוה\u2069’s share',
    split: 'Cut at chapters',
    shares: 'Shares by part',
    p: 'p',
    q: 'q',
    chapter: 'Chapter',
    words: 'Words',
    names: 'Names',
    part: 'Part',
  },
  notSplit: '—',
  split: (a: number, b: number) => `${numEn(a)}, ${numEn(b)}`,
  showBook: (book: string) => `The chapters of ${book}`,
  allBooks: 'All books',
  chaptersTitle: (book: string) => `${book}, chapter by chapter`,
  pairsTitle: 'The doubled psalms, name by name',
  pairHead: (e: string, y: string) => `${e} and ${y}`,
  pairCounts: (eWard: number, yWard: number, same: number) =>
    `\u2068אלהים\u2069 for \u2068יהוה\u2069 ${numEn(eWard)}, the reverse ${numEn(yWard)}, the same name ${numEn(same)}`,
  kinds: { e_ward: '\u2068אלהים\u2069 for \u2068יהוה\u2069', y_ward: '\u2068יהוה\u2069 for \u2068אלהים\u2069', same: 'the same', other: 'another name' } as Record<string, string>,
  placeCols: { inside: 'Inside 42–83', outside: 'Its double', kind: 'Change' },
  absent: '(no word)',
  totals: (n: number) => `${countEn(n, 'name', 'names')} in all`,
  method:
    'A word counts for the name of its OSHB lemma (\u2068יהוה\u2069 also where it is pointed as \u2068אלהים\u2069; \u2068אלהים\u2069 also where it means gods, which the lemma does not tell apart). A book with at least 20 of the two names and 9 chapters is cut in three runs of at least 3 chapters where a single rate fits worst, and the gain is set against the best cut of its chapters shuffled 999 times; q corrects for the books tested. The doubled psalms are aligned as the Changes page aligns parallels.',
  notComputed: 'The divine names were not computed in this build: run `bsim divine`, then `bsim build-db`.',
}
