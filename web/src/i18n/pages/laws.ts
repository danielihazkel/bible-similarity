// Interface strings of the law codes side by side (DESIGN.md §16.93, D155). English first, Hebrew
// typed against it.

import { countEn, numEn, pct } from '../fmt'
import { register } from '../en'

export type LawCodeKey = 'covenant' | 'ritual' | 'holiness' | 'deuteronomic' | 'priestly'
export type LawFormKey = 'casuistic' | 'apodictic' | 'other'
export type LawAddress = '2ms' | '2mp' | '3' | 'mixed'

export const lawsEn = {
  title: 'The law codes side by side',
  lede: 'The Pentateuch gives some laws more than once, each code in its own words: the release of a Hebrew slave in Exodus 21, Leviticus 25 and Deuteronomy 15. Here each code is cut into its laws at the Masoretic paragraphs, each law’s form is read from its clauses, and the laws one code gives again in another are found on the combined list of similar verses and set side by side word by word.',
  codes: {
    covenant: 'Covenant Code',
    ritual: 'Exodus 34',
    holiness: 'Holiness Code',
    deuteronomic: 'Deuteronomic Code',
    priestly: 'Other priestly law',
  } as Record<LawCodeKey, string>,
  codeRanges: {
    covenant: 'Exodus 20:22–23:33',
    ritual: 'Exodus 34:10–26 (one paragraph, so one law)',
    holiness: 'Leviticus 17–26',
    deuteronomic: 'Deuteronomy 12–26',
    priestly: 'Leviticus 1–16; Numbers 5–6, 15, 18–19, 27:1–11, 28–30, 35–36',
  } as Record<LawCodeKey, string>,
  forms: { casuistic: 'Casuistic', apodictic: 'Apodictic', other: 'Other' } as Record<LawFormKey, string>,
  formHints: {
    casuistic: 'If … then: כי or אם with a yiqtol opening a clause in its first two verses (וכי יגנב איש)',
    apodictic: 'Thou shalt (not): לא + yiqtol, אל + jussive, or מות יומת',
    other: 'Neither: a frame, an exhortation, a list',
  } as Record<LawFormKey, string>,
  address: { '2ms': 'you (singular)', '2mp': 'you (plural)', '3': 'third person', mixed: 'mixed' } as Record<LawAddress, string>,
  counts: (laws: number, pairs: number) => `${countEn(laws, 'law', 'laws')} in five codes; ${countEn(pairs, 'matched pair', 'matched pairs')} across them.`,
  profileTitle: 'Each code’s laws by form and address',
  profileLede: 'The form of each law, and the person most of its verbs are in. Laws addressed in the third person are mostly casuistic: “if a man …”.',
  cols: { code: 'Code', ranges: 'Verses', laws: 'Laws', address: 'Mostly addressed to', share: (n: number, of: number) => `${numEn(n)} (${pct(of ? n / of : 0)})` },
  knownTitle: 'The laws the commentaries set side by side',
  groups: {
    'slave release': 'The release of a slave',
    asylum: 'Asylum for the manslayer',
    festivals: 'The festivals',
    'sabbatical year': 'The sabbatical year',
    interest: 'Interest',
    "the kid in its mother's milk": 'The kid in its mother’s milk',
  } as Record<string, string>,
  knownLede: 'Fixed before the first run. Each pair of a group’s passages counts, found when a matched pair joins a law in one and a law in the other.',
  verdict: { holds: 'Found', fails: 'Not found' } as Record<'holds' | 'fails', string>,
  known: (found: number, n: number) => `${numEn(found)} of ${numEn(n)} pairs of passages found.`,
  strict: (n: number, of: number) => `By the aligned verses themselves, not their whole paragraphs: ${numEn(n)} of ${numEn(of)}.`,
  member: (a: string, b: string, found: boolean) => `${a} and ${b}: ${found ? 'found' : 'not found'}`,
  showPair: 'side by side',
  view: { label: 'Show', pairs: 'Matched pairs', laws: 'Laws' } as Record<'label' | 'pairs' | 'laws', string>,
  pairsTitle: 'Matched pairs',
  pairsLede: (k: number, min: number) =>
    `Two verses are linked when one is among the other’s first ${numEn(k)} on the combined list; two laws in two codes are matched when they have at least ${numEn(min)} links and one is the other’s best match in its code. The weakest matches are often only a shared phrase.`,
  order: { label: 'Order', score: 'Strongest first', canon: 'Canon order' } as Record<'label' | 'score' | 'canon', string>,
  code: 'Code',
  allCodes: 'All codes',
  knownOnly: 'Only those named in advance',
  pairCount: (total: number, page: number, pages: number) => `${countEn(total, 'pair', 'pairs')} · page ${numEn(page)} of ${numEn(pages)}`,
  links: (n: number) => countEn(n, 'link', 'links'),
  kept: (x: number) => `${pct(x)} of the words aligned keep their lemma`,
  namedTag: (group: string) => `named in advance: ${group}`,
  lawsTitle: 'The laws',
  form: 'Form',
  allForms: 'All forms',
  lawCount: (total: number, page: number, pages: number) => `${countEn(total, 'law', 'laws')} · page ${numEn(page)} of ${numEn(pages)}`,
  lawPairs: (n: number) => (n ? countEn(n, 'matched pair', 'matched pairs') : 'no match'),
  synopsisTitle: (a: string, b: string) => `${a} beside ${b}`,
  synopsisLede: 'The verses of each law that the combined list links, first to last, aligned word by word; the marks show what the second changes against the first.',
  more: (n: number) => `and ${countEn(n, 'more verse', 'more verses')}`,
  close: 'Close',
  read: 'read the paragraph',
  noData: 'The law codes were not computed in this build.',
  none: 'Nothing here.',
}

register('laws', lawsEn)
