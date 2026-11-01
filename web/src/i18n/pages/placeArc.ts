// Interface strings of Overview → The geographic arc (DESIGN.md §16.60). English first, Hebrew
// typed against it.

import { countEn, countHe, numEn, numHe } from '../fmt'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const chaptersHe = (n: number) => countHe(n, 'פרק אחד', 'שני פרקים', 'פרקים')
const kmEn = (n: number) => `${numEn(Math.round(n))} km`
export const kmHe = (n: number) => `${numHe(Math.round(n))} ק״מ`

export const paEn = {
  title: 'The geographic arc',
  lede: 'Where does each chapter take place? A chapter’s centre is the mean of the places it names, each counted once per verse, and its spread how far those places lie from the centre on average. Do consecutive chapters stay close, does the centre move where the story goes, and do the oracles against the nations range wider than the rest of the prophets?',
  noData: 'Not computed in this build: run `bsim place-arc`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (placed: number, chapters: number, mean: number, nullMean: number, p: number, shuffles: number) =>
    `${numEn(placed)} of ${numEn(chapters)} chapters name places enough to be placed. Within a book, consecutive placed chapters lie ${kmEn(mean)} apart on average, against ${kmEn(nullMean)} with each book’s chapters shuffled (${numEn(shuffles)} orders; p ${fp(p)}).`,
  booksHeld: (held: number, n: number) => `${numEn(held)} of the ${numEn(n)} books with enough placed chapters hold on their own.`,
  caveat: (min: number) =>
    `A chapter is placed when it names places in ${countEn(min, 'mention', 'mentions')} or more (a place counts once per verse). Every place it names pulls on its centre: a place named in passing, Tarshish or Egypt in a memory of the exodus, as much as the scene’s own.`,
  // one book
  bookTitle: (book: string) => `The path of ${book}`,
  book: 'Book',
  bookNote: (n: number, chapters: number, mean: number, nullMean: number, p: number) =>
    `${numEn(n)} of ${numEn(chapters)} chapters placed: ${kmEn(mean)} from one to the next on average, against ${kmEn(nullMean)} in shuffled order (p ${fp(p)}).`,
  bookUntested: (n: number, chapters: number) => `${numEn(n)} of ${numEn(chapters)} chapters placed: too few to test.`,
  mapLabel: (book: string) => `The centres of the chapters of ${book} on the map, joined in order`,
  pointTitle: (label: string, n: number, spread: number) => `${label}: ${countEn(n, 'mention', 'mentions')}, spread ${kmEn(spread)}`,
  chaptersTitle: 'Chapter by chapter',
  chaptersLede: 'Each placed chapter with the place it names most, the km from the placed chapter before and its spread. The three longest steps are marked.',
  step: (km: number) => kmEn(km),
  stepFrom: (km: number, prev: number) => `${kmEn(km)} from ch. ${numEn(prev)}`,
  spread: (km: number) => `spread ${kmEn(km)}`,
  oracleTag: 'oracle',
  onMap: (label: string) => `${label} on Places on the map`,
  chapterNumber: (n: number) => numEn(n),
  booksTitle: 'Book by book',
  cols: { book: 'Book', placed: 'Placed chapters', step: 'Mean step', shuffled: 'Shuffled', ratio: 'Ratio', p: 'p' },
  colHints: { ratio: 'The book’s path over the shuffled orders’ mean: below 1, consecutive chapters lie closer than chance' },
  placedOf: (n: number, chapters: number) => `${numEn(n)} of ${numEn(chapters)}`,
  untested: 'too few',
  open: (book: string) => `Show ${book} on the map`,
  ratio: (x: number) => x.toFixed(2),
  km: kmEn,
  // known moves
  movesTitle: 'Known moves',
  movesLede: 'Four moves the story makes. A move holds when the centre of the span after lies nearer the region the story goes to than the centre of the span before, and the span before nearer the region it leaves. A check of the centres, not a discovery.',
  movesSummary: (held: number, n: number) => `${numEn(held)} of ${numEn(n)} moves hold.`,
  moves: { abram: 'Abram to Canaan', descent: 'Down to Egypt', exodus: 'Out of Egypt', exile: 'Carried to Babylon' } as Record<string, string>,
  regions: { mesopotamia: 'Mesopotamia', canaan: 'Canaan', egypt: 'Egypt', wilderness: 'the wilderness' } as Record<string, string>,
  mcols: { move: 'Move', before: 'Before', after: 'After', km: 'Centres apart' },
  endNote: (from: number, fromRegion: string, to: number, toRegion: string) => `${kmEn(from)} from ${fromRegion}, ${kmEn(to)} from ${toRegion}`,
  unplaced: 'too few places',
  movesMap: 'The known moves on the map: each from the centre of the span before to the centre of the span after',
  moveTitle: (move: string, label: string) => `${move}: ${label}`,
  // the oracles
  oraclesTitle: 'The oracles against the nations',
  oraclesLede: (refs: string) =>
    `The oracles against the nations (${refs}) name the nations’ lands and cities. Do their chapters range wider than the other chapters of the prophets? Spread, and reach (the centre’s km from Jerusalem), each against the labels shuffled over the placed chapters of the prophets, one-sided.`,
  oracleVerdict: (alpha: number) => `Holds when either measure is wider at p ≤ ${alpha}.`,
  ocols: { measure: 'Measure', oracles: 'Oracles', others: 'Other prophetic chapters', shuffled: 'Shuffled', p: 'p' },
  measures: { spread: 'Spread', reach: 'Reach from Jerusalem' } as Record<string, string>,
  meanMedian: (mean: number, median: number, n: number) => `${kmEn(mean)} (median ${kmEn(median)}; ${countEn(n, 'chapter', 'chapters')})`,
  oracleChapters: 'The oracles’ chapters',
  chcols: { chapter: 'Chapter', place: 'Named most', places: 'Places', spread: 'Spread', reach: 'Reach' },
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
}
