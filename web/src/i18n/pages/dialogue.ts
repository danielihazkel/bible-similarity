// Interface strings of Who speaks → To whom: addressees, conversations and the three checks fixed
// in advance (DESIGN.md §16.44). English first, Hebrew typed against it.

import { countEn, numEn } from '../fmt'

export const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const x1 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(1))
export const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)

export type Src = 'explicit' | 'vocative' | 'pronoun' | 'turn'

export const dlgEn = {
  lede: 'Who is each quotation said to? The clause that introduces it often says (ויאמר יהוה אל משה); otherwise the quotation may call someone by name (a vocative), the introduction may say only “to him” (אליו), which is read as the other party of the conversation, or say nothing (ויאמר), which is read as an answer to whoever spoke just before. From these: who speaks to whom in each book, the exchanges between two speakers, and three checks fixed before the first run.',
  noData: 'Not computed in this build: run `bsim syntax`, `bsim dialogue`, then `bsim build-db`.',
  summary: (q: number, found: number, by: Record<Src, number>) =>
    `${numEn(q)} quotations; an addressee found for ${numEn(found)}: named in the introduction ${numEn(by.explicit)}, called by name ${numEn(by.vocative)}, “to him” read as the other party ${numEn(by.pronoun)}, an answer to the speaker before ${numEn(by.turn)}.`,
  handCheck: (h: Record<Src, [number, number]>) =>
    `A hand check of 50 quotations drawn after the rules were set: named ${h.explicit[0]} / ${h.explicit[1]}, called by name ${h.vocative[0]} / ${h.vocative[1]}, “to him” ${h.pronoun[0]} / ${h.pronoun[1]}, an answer ${h.turn[0]} / ${h.turn[1]}. The checks below use the first two only; every addressee is the sensitivity check.`,
  sources: { explicit: 'named', vocative: 'called by name', pronoun: '“to him”', turn: 'an answer' } as Record<Src, string>,
  checksTitle: 'Checks fixed in advance',
  verdict: { holds: 'holds', fails: 'does not hold' },
  deference: (up: number, rest: number, count: number, of: number, nul: number | null, p: number | null) =>
    `“Your servant” (עבדך, אמתך, שפחתך) in speech to God or a king: ${up.toFixed(1)} times per 1,000 words (${numEn(count)} in ${numEn(of)} words), against ${rest.toFixed(1)} in speech to anyone else; the difference is ${(up - rest).toFixed(1)}, against ${x1(nul)} with the “up” label shuffled among the quotations of each book (p ${fp(p)}). A known answer: deference to a superior (Revell 1996).`,
  particle: (up: number, rest: number, count: number, of: number, p: number | null) =>
    `נא right after an imperative: ${pct(up)} of the commands to God or a king (${numEn(count)} of ${numEn(of)}), against ${pct(rest)} of the others (p ${fp(p)}). Contested: is נא a mark of politeness (Shulman 1996, Christiansen 2009) or a logical particle, “then” (Lambdin 1971)?`,
  lastWord: (obs: number, n: number, exp: number, p: number) =>
    `In ${numEn(n)} exchanges between God or a king and someone of lower rank, the higher one speaks last in ${numEn(obs)}, against ${exp.toFixed(1)} if the last turn were any of the exchange's turns at random (p ${fp(p)}). An open question.`,
  sensitivity: (d: number, dp: number | null, pr: number, pp: number | null) =>
    `With every addressee, however it was found: “your servant” ${d.toFixed(1)} more per 1,000 words (p ${fp(dp)}); נא ${pct(pr)} more often (p ${fp(pp)}).`,
  described: (opens: number, n: number, exp: number, p: number, longer: number, shorter: number, mh: number | null, ml: number | null, lp: number | null) =>
    `Described, without a verdict: the higher party opens ${numEn(opens)} of the ${numEn(n)} exchanges (${exp.toFixed(1)} expected, p ${fp(p)}); its turns are longer in ${numEn(longer)} and shorter in ${numEn(shorter)} (median ${x1(mh)} against ${x1(ml)} words a turn; sign test p ${fp(lp)}).`,
  booksTitle: 'Who speaks to whom',
  book: 'Book',
  bookOption: (name: string, q: number) => `${name} (${numEn(q)})`,
  network: (book: string) => `Conversations in ${book}`,
  networkLabel: (n: number, book: string) => `The ${n} most active speakers of ${book} and who they speak to; the same pairs are listed in the table below.`,
  pairsTitle: (book: string) => `Pairs in ${book}`,
  cols: { speaker: 'Speaker', addressee: 'To', quotes: 'Quotations', words: 'Words', named: 'Named or called' },
  pairTitle: (s: string, a: string, n: number) => `${s} → ${a}: ${countEn(n, 'quotation', 'quotations')}`,
  filterParty: (who: string) => `Show the exchanges of ${who}`,
  noPairs: 'No addressed speech found in this book.',
  exchangesTitle: 'Exchanges',
  exchangesLede: 'Runs of turns introduced by the narrator between two speakers who both speak; a third speaker, or a turn addressed to someone else, ends one.',
  unequal: 'Only God or a king with someone of lower rank',
  party: (who: string) => `With ${who}`,
  allParties: 'Anyone',
  count: (n: number) => countEn(n, 'exchange', 'exchanges'),
  turns: (n: number, a: string, an: number, b: string, bn: number) => `${countEn(n, 'turn', 'turns')}: ${a} ${an}, ${b} ${bn}`,
  last: (who: string) => `last word: ${who}`,
  read: 'Read with the speakers',
  empty: 'No exchanges match.',
  god: 'God',
}
