// Interface strings of the haftarot page (DESIGN.md §16.69): each parasha's reading from the
// Prophets and where the systems rank it among all the chapters of the Prophets. English first,
// Hebrew typed against it.

import { countEn, numEn } from '../fmt'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const pct = (x: number) => `${Math.round(x * 100)}%`

export const hfEn = {
  title: 'Haftarot',
  lede: 'Each Sabbath the Torah reading is followed by a reading from the Prophets chosen to match it: Noach is read with Isaiah 54, where God swears by the waters of Noah; Vayera with II Kings 4, a son promised to a woman who had none. The sages’ pairing is an independent judgement of which passages belong together. Here every parasha is set against all 380 chapters of the Prophets, as the site’s own systems rank them, and its haftarah is looked for in the list.',
  notComputed: 'The haftarot were not computed in this build (run bsim haftarot).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  claim: {
    title: 'The haftarah ranks high among the Prophets',
    text: (n: number, own: number, shuffled: number, p: number) =>
      `The ${numEn(n)} haftarot chosen for their parasha stand at percentile ${pct(own)} of the 380 chapters on average (0: the first), against ${pct(shuffled)} with the haftarot shuffled among those parashot (p ${fp(p)}).`,
  },
  calendar: {
    title: 'The calendar’s haftarot rank lower',
    text: (cal: number, own: number, p: number) =>
      `The ten fixed by the calendar, three of rebuke before the Ninth of Av and seven of consolation after, stand at percentile ${pct(cal)}, against ${pct(own)} for the rest (p ${fp(p)}).`,
  },
  known: {
    title: 'Noah’s waters and the Shunammite’s son',
    text: (k: number, ranks: string) => `Both within the first ${numEn(k)} chapters for their parasha? Ranked ${ranks}.`,
    rank: (name: string, r: number) => `${name} ${numEn(r)}`,
  },
  modesTitle: 'How each system finds the haftarah',
  modesLede: (n: number) => `Each list of the ${countEn(n, 'parasha', 'parashot')} whose haftarah follows it, scored with the haftarah as the right answer: the first gold the parashot have had.`,
  modes: { lexical: 'Words (TF-IDF)', semantic: 'Meaning (BEREL)', fused: 'Both (fused)' } as Record<string, string>,
  cols: {
    system: 'System',
    mrr: 'MRR',
    hits: (k: number) => `In the first ${numEn(k)}`,
    median: 'Median rank',
    pct: 'Mean percentile',
    num: '#',
    parasha: 'Parasha',
    haftarah: 'Haftarah',
    rank: 'Rank (words · meaning)',
  },
  calendarTag: { admonition: 'rebuke', consolation: 'consolation' } as Record<string, string>,
  calendarHint: 'Fixed by the calendar, not chosen for the parasha',
  sephardi: (refs: string) => `Sephardi: ${refs}`,
  of: (r: number, lex: number, sem: number) => `${numEn(r)} (${numEn(lex)} · ${numEn(sem)})`,
  showList: (name: string) => `The chapters of the Prophets for ${name}`,
  listTitle: (name: string) => `${name}: the first chapters of the Prophets`,
  listLede: (haft: string) => `The haftarah: ${haft}. Ranked by both systems together; the chapters holding the haftarah are marked.`,
  inHaftarah: 'the haftarah',
  compare: 'compare',
  close: 'Close',
  credit: 'The pairings: Hebcal leyning, Copyright (c) 2020, hebcal (BSD 2-Clause License), the Ashkenazi haftarot.',
}
