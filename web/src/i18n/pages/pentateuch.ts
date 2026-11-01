// Interface strings of Overview → Pentateuch: an unsupervised P / non-P split of Genesis-Numbers
// tested against the source critics' P (DESIGN.md §16.43). English first, Hebrew typed against it.

import { countEn } from '../fmt'

export const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const x3 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(3))
export const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)

export const pentEn = {
  title: "The Pentateuch's sources",
  lede: 'Source criticism holds that a Priestly writer (P) and older, non-Priestly sources were woven together in Genesis–Numbers. Following Koppel, Dershowitz and colleagues, the text is split in two without being told where P is — first chunks of ten verses by their choices between synonyms (אני or אנכי, עדה or קהל, מטה or שבט, …), a choice a writer makes without thinking of the topic, then every verse by those choices and the commonest function words. The divine names are held back. The split is then laid against P as the critics draw it (Noth, entered by hand). The hypothesis is contested; the checks were fixed before the first run and could have failed.',
  noData: 'Not computed in this build: run `bsim pentateuch`, then `bsim build-db`.',
  testsTitle: 'Does the split find P?',
  split: (kappa: number, nul: number, p: number, agreement: number) =>
    `Over Genesis–Numbers the split agrees with the reference on ${pct(agreement)} of the verses: Cohen's kappa ${x3(kappa)}, against ${x3(nul)} for the same split shifted to a random place in each book (p ${fp(p)}).`,
  genesis: (kappa: number, nul: number, p: number) =>
    `Within Genesis, where both sources tell stories (so law against narrative cannot carry it): kappa ${x3(kappa)}, against ${x3(nul)} (p ${fp(p)}).`,
  names: (gap: number, nul: number, p: number, pLike: number | null, nonP: number | null, refP: number | null, refNon: number | null) =>
    `The divine names, never seen by the split: before Exodus 6 — where P has the name יהוה revealed — the P-like side should avoid יהוה. It is ${pct(pLike)} of the divine names on the P-like side and ${pct(nonP)} on the other (gap ${x3(gap)} against ${x3(nul)}, p ${fp(p)}); in the reference itself, ${pct(refP)} in P and ${pct(refNon)} outside it.`,
  confusionTitle: 'The split against the reference',
  confusion: { rowP: 'P-like side', rowNon: 'Other side', colP: 'Reference: P', colNon: 'Reference: non-P' },
  booksTitle: 'By book',
  bookCols: { book: 'Book', verses: 'Verses', agree: 'Agreement', pLike: 'P-like', pRef: 'Reference P' },
  bookNames: { Genesis: 'Genesis', Exodus: 'Exodus', Leviticus: 'Leviticus', Numbers: 'Numbers' } as Record<string, string>,
  gridTitle: 'Robustness',
  gridLede: 'Chunk size and smoothing; the bold row is the setting fixed in advance (200 shifts each).',
  gridCols: { chunk: 'Chunk (verses)', smooth: 'Smoothing (± verses)', kappa: 'Kappa', genesis: 'Genesis', names: 'Names gap' },
  wordsTitle: 'What decides it',
  pLikeWords: 'Pulling toward the P-like side',
  nonPWords: 'Pulling toward the other side',
  stems: { h: 'hiphil', q: 'qal' } as Record<string, string>,
  synonymsTitle: 'The synonym choices on each side',
  synCols: { set: 'Choice', members: 'Words', pLike: 'P-like side', nonP: 'Other side' },
  setNames: {
    I: 'I',
    tribe: 'tribe',
    congregation: 'congregation',
    die: 'die',
    holding: 'holding',
    maidservant: 'maidservant',
    make: 'make, create',
    speak: 'speak, say',
    beget: 'beget',
    chief: 'chief',
    dwell: 'dwell',
    people: 'people, nation',
    bring_up: 'bring out / up',
    with: 'with',
    lest: 'lest',
    behold: 'behold',
    only: 'only',
    also: 'also',
  } as Record<string, string>,
  chaptersTitle: 'Chapter by chapter',
  chaptersLede: 'The bar is the share of each chapter on the P-like side; the mark, the share the reference calls P.',
  book: 'Book',
  chapterRow: (pLike: number, pRef: number | null) => `P-like ${pct(pLike)} · reference P ${pRef == null ? '–' : pct(pRef)}`,
  read: 'Read with the split',
  count: (n: number) => countEn(n, 'chapter', 'chapters'),
  empty: 'No chapter here.',
}
