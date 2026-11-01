// Interface strings of the retold speech page (DESIGN.md §16.68): passages told again, by another
// speaker, by the same one, or by the narrator as done, and what changes word by word. English
// first, Hebrew typed against it.

import type { RetoldGroup, RetoldOrder } from '../../api/types'
import { countEn, numEn } from '../fmt'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const pctEn = (x: number) => `${Math.round(x * 100)}%`

export const rtEn = {
  title: 'Retold speech',
  lede: 'The woman tells the serpent what God said in the garden and adds \u2068ולא תגעו בו\u2069; Abraham’s servant tells Laban his master’s charge and leaves part of it out. When something said is told again, the retelling shows its teller. Here every passage told again later in the same book: by another speaker, by the same one, or by the narrator as done. The two are set side by side word by word.',
  notComputed: 'The retold speech was not computed in this build (run bsim retold).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  claim: {
    title: 'Speech retold by another speaker changes more than speech carried out',
    text: (a: number, b: number, na: number, nb: number, p: number) =>
      `${countEn(na, 'retelling by another speaker', 'retellings by another speaker')} change ${pctEn(a)} of their words (substituted, left out, added or moved); ${countEn(nb, 'speech', 'speeches')} told again by the narrator as done change ${pctEn(b)}. Compared within the same lengths: p ${fp(p)}.`,
  },
  known: {
    title: 'The retellings the commentaries read side by side',
    text: (found: number, n: number) => `The alignment finds ${numEn(found)} of the ${numEn(n)} named in advance; the check asked for all of them.`,
    found: (rate: number) => `found, ${pctEn(rate)} changed`,
    missing: 'not found',
  },
  groupsTitle: 'What is told again',
  groups: {
    retold: 'Retold by another speaker',
    repeated: 'Repeated by the same speaker',
    carried: 'Carried out by the narrator',
    told: 'Narration told in a speech',
    narrated: 'Narration told again',
    unclear: 'A speaker not known',
  } satisfies Record<RetoldGroup, string>,
  cols: { group: 'Told again', pairs: 'Passages', rate: 'Words changed' },
  listTitle: 'The passages',
  show: { label: 'Show', all: 'All' },
  order: { label: 'Order', canon: 'Canon', most: 'Most changed', least: 'Least changed' } satisfies Record<RetoldOrder | 'label', string>,
  knownOnly: 'Named in advance only',
  god: 'God',
  narrator: 'the narrator',
  unknown: 'someone not known',
  first: 'First told by',
  again: 'Told again by',
  rate: (r: number, n: number) => `${pctEn(r)} of ${numEn(n)} words changed`,
  knownTag: 'named in advance',
  compare: 'compare the first verses',
  read: 'read the chapter',
  count: (n: number) => countEn(n, 'passage', 'passages'),
  pageOf: (p: number, pages: number) => `page ${numEn(p)} of ${numEn(pages)}`,
  empty: 'Nothing told again here.',
  method:
    'Every word belongs to the narrator or to the speaker of the quotation that holds it (a quotation inside a speech belongs to the one who quotes it). Each run of one teller, cut into pieces of at most 60 content words, is aligned (Smith–Waterman, rare words weighing most) with the earlier text of its book, up to 400 verses back, where it shares the most rare words; at least 5 words aligned. The two passages are then diffed word by word: a change of spelling or form keeps the word. The claim compares the two groups within four length bands, the labels shuffled 9,999 times.',
}
