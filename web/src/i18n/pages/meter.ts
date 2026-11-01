// Interface strings of Poetry → Meter: stresses per line and the falling lament line (DESIGN.md
// §16.37). English first, Hebrew typed against it.

import type { MeterGroup } from '../../api/types'
import { countEn, numEn, pct } from '../fmt'

export const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const x2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))

export const metEn = {
  view: 'Meter',
  lede: 'Hebrew verse is counted in stresses: every accented word carries one, and words joined by a maqaf share one. The accents divide each verse in two, and each part in two again; a line here is the largest of those parts with at most a handful of stresses, and its own main pause splits it into two members. The lament (qinah) line is said to fall: a longer member, then a shorter one (3:2), the voice breaking off. Lamentations 1–4 are said to be written in it.',
  noData: 'Not computed in this build: run `bsim meter`, then `bsim build-db`.',
  testTitle: 'Does Lamentations fall?',
  test: (min: number, max: number, mean: number | null, pool: number | null, n: number, p: number | null, poeticP: number | null) =>
    `Lines of ${numEn(min)}–${numEn(max)} stresses, net fall = the share of lines whose first member is longer minus the share whose first member is shorter. Lamentations 1–4: ${x2(mean)}; other poetry under the same (prose) accents, ${numEn(n)} chapters: ${x2(pool)} (p ${fp(p)}, chapters drawn at random). Against Psalms, Proverbs and Job, which have accents of their own: p ${fp(poeticP)}.`,
  testNote: 'The prose accents end a verse or a half-verse on a short member, so lines fall a little everywhere, prose lists included; that is why the comparison is with poetry under the same accents. The line lengths were chosen with Lamentations in view, so the table below repeats the test with other lengths.',
  poolNote: (quantile: number, prob: number | null) =>
    `The poetry pool: the prose-accented chapters in the top ${pct(1 - quantile)} by their verses' probability of parallel halves (at least ${x2(prob)}).`,
  cols: {
    chapter: 'Chapter',
    group: 'Group',
    lines: 'Lines',
    fall: 'Falling',
    rise: 'Rising',
    net: 'Net fall',
    share32: '3:2',
    pct: 'Above the pool',
  },
  colTitles: {
    lines: 'Lines of the measured length that split into two stressed members',
    fall: 'Share of lines whose first member is longer (3:2, 4:2 …)',
    rise: 'Share of lines whose first member is shorter (2:3 …)',
    net: 'Falling minus rising',
    share32: 'Share of lines of exactly 3 and 2 stresses',
    pct: 'Share of the poetry pool with a lower net fall',
  },
  controlTitle: 'The control: Lamentations 5',
  control: 'Lamentations 5 is a lament too, but a prayer in even lines (mostly 3:3); it should not stand out.',
  namedTitle: 'Chapters that speak of a lament',
  named: (n: number, mean: number | null, pool: number | null, p: number | null) =>
    `The ${countEn(n, 'chapter', 'chapters')} outside Lamentations that use the word קינה, tested the same way: net fall ${x2(mean)} against ${x2(pool)} (p ${fp(p)}). The word picks out the laments of Ezekiel and Amos, but also chapters that only mention one.`,
  gridTitle: 'Other line lengths',
  grid: { length: 'Stresses per line', lam: 'Lamentations 1–4', pool: 'Pool', p: 'p (pool)', poeticP: 'p (Psalms, Proverbs, Job)' },
  patternsTitle: 'Commonest lines',
  patterns: (lines: number) => `${countEn(lines, 'line', 'lines')}:`,
  rankTitle: 'Chapters by net fall',
  rankNote: (min: number) =>
    `Chapters with at least ${numEn(min)} measured lines. Prose lists of offerings and the like rank high: their verses end on short members. Among the poetry, high net falls are leads for laments outside Lamentations.`,
  groups: {
    test: 'Lamentations 1–4',
    control: 'Lamentations 5',
    pool: 'Poetry (prose accents)',
    poetic: 'Psalms, Proverbs, Job',
    prose: 'Prose',
  } satisfies Record<MeterGroup, string>,
  anyGroup: 'All',
  ranked: (n: number) => countEn(n, 'chapter', 'chapters'),
  // the unit page
  toggle: 'Stresses',
  toggleTitle: 'The stresses of each line: first member : second member',
  theMeter: 'the stresses',
  verseLines: 'Stresses per line',
  unsplit: (n: number) => `${numEn(n)}`,
  chapterLine: (net: number, pctile: number | null, group: string) =>
    `This chapter's lines: net fall ${x2(net)}${pctile == null ? '' : `, above ${pct(pctile)} of the poetry pool`} (${group}).`,
}
