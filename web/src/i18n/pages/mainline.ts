// Interface strings of the narrative main line (DESIGN.md §16.91, D153). English first, Hebrew
// typed against it.

import { countEn, numEn, pct } from '../fmt'
import { register } from '../en'

export const mlEn = {
  title: 'The narrative main line',
  lede: 'A biblical story moves on a chain of wayyiqtol clauses (ויקם … וילך … ויאמר). Here every independent clause of the narrator is either on that chain or off it: background that sets a scene, describes, or tells what had happened before (והנחש היה ערום). A pause is a run of background clauses between two wayyiqtols in the narrative books.',
  counts: (clauses: number, main: number, background: number, pauses: number) =>
    `${numEn(clauses)} narrator clauses: ${numEn(main)} on the main line, ${numEn(background)} background; ${countEn(pauses, 'pause', 'pauses')}.`,
  claim: (excess: number, nullMean: number, p: string, opening: number) =>
    `Fixed in advance: background is more common among a paragraph’s first ${numEn(opening)} narrator clauses than among the rest. It is ${(excess * 100).toFixed(1)} points more common there, against ${(nullMean * 100).toFixed(1)} with the clauses shuffled within paragraphs (p ${p}).`,
  claimNote: 'The Masoretic paragraphs mostly open on the main line (ויהי …, ויאמר יהוה …): the scene is set inside a story more than at its paragraph breaks.',
  verdict: { holds: 'Borne out', fails: 'Not borne out' } as Record<'holds' | 'fails', string>,
  knownTitle: 'Named in advance',
  known: (found: number, n: number) => `The pauses the commentaries point to are found: ${numEn(found)} of ${numEn(n)}.`,
  knownFound: 'found',
  knownMissing: 'not found',
  booksTitle: 'Books by their main line',
  booksLede: 'The share of the narrator’s independent clauses on the wayyiqtol chain: high in the stories, low in law, poetry and prophecy.',
  cols: { book: 'Book', main: 'Main line', background: 'Background', share: 'Share', pauses: 'Pauses' },
  share: (x: number | null) => (x === null ? '–' : pct(x)),
  pausesTitle: 'The pauses',
  order: { label: 'Order', longest: 'Longest first', canon: 'Canon order' } as Record<'label' | 'longest' | 'canon', string>,
  knownOnly: 'Only those named in advance',
  pauseCount: (total: number, page: number, pages: number) => `${countEn(total, 'pause', 'pauses')} · page ${numEn(page)} of ${numEn(pages)}`,
  pause: (n: number) => countEn(n, 'background clause', 'background clauses'),
  read: 'read it with the layer',
  more: (n: number) => `and ${countEn(n, 'more verse', 'more verses')}`,
  namedTag: 'named in advance',
  types: {
    NmCl: 'nominal',
    AjCl: 'adjectival',
    Ptcp: 'participle',
    xQt0: 'x-qatal',
    xQtX: 'x-qatal',
    XQtl: 'x-qatal',
    WXQt: 'ו + x-qatal',
    WxQ0: 'ו + x-qatal',
    WxQX: 'ו + x-qatal',
    ZQt0: 'qatal',
    ZQtX: 'qatal',
    WQt0: 'weqatal',
    WQtX: 'weqatal',
    xYq0: 'x-yiqtol',
    xYqX: 'x-yiqtol',
    XYqt: 'x-yiqtol',
    WxY0: 'ו + x-yiqtol',
    WxYX: 'ו + x-yiqtol',
    WXYq: 'ו + x-yiqtol',
    Ellp: 'without a verb',
    CPen: 'casus pendens',
  } as Record<string, string>,
  noData: 'The main line was not computed in this build.',
  none: 'No pause here.',
}

register('ml', mlEn)
