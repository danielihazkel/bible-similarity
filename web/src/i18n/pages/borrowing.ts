// Interface strings of "who borrowed" (DESIGN.md §16.27): the page and the line on parallel
// sequences and Compare. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

type Sign = 'language' | 'spelling' | 'smoothing' | 'expansion'

export const borEn = {
  title: 'Who borrowed',
  lede: 'For passages that run parallel in two books, which side looks like the later text and so the borrower. Four signs, fixed before any result was seen, compare the two sides; the ones that pass the check below vote.',
  caveat:
    'A later-looking text is evidence, not proof: both may draw on a common source, and copyists updated spelling and grammar. Every direction scholars accept runs from a book earlier in the canon to a later one, so this check cannot tell the signs from canon order (they never see it).',
  signs: {
    language: 'Language',
    spelling: 'Spelling',
    smoothing: 'Smoothing',
    expansion: 'Expansion',
  } as Record<Sign, string>,
  signHints: {
    language: 'Late Biblical Hebrew features of each side (late words, אני for אנכי, fewer infinitive absolutes …)',
    spelling: 'Which side writes ו and י more fully where the words are the same',
    smoothing: 'Where a word was replaced, whether the rarer word was replaced by a commoner one',
    expansion: 'Whether one side adds more words than it leaves out',
  } as Record<Sign, string>,
  allSigns: 'All four, voting',
  checkTitle: 'Check: parallels whose direction is accepted',
  checkLede: (n: number) =>
    `${numEn(n)} parallels between books whose direction most scholars accept: Samuel–Kings → Chronicles, Genesis and Joshua → 1 Chronicles, Psalms → 1 Chronicles 16, 2 Kings → Jeremiah 52, Exodus → Deuteronomy.`,
  right: (a: number, n: number, p: string) => `${numEn(a)} of ${numEn(n)} right (sign test p = ${p})`,
  votes: 'votes',
  noVote: 'shown, does not vote',
  heldOut: (a: number, n: number, u: number) =>
    `The voting signs chosen without each book pair and tested on it: ${numEn(a)} of ${numEn(n)} right, ${numEn(u)} undecided.`,
  pairs: 'Book pairs',
  flow: (src: string, dst: string) => `${src} → ${dst}`,
  unclear: 'unclear',
  accepted: 'accepted direction',
  counts: (n: number, ab: number, ba: number) =>
    `${numEn(n)} ${n === 1 ? 'parallel' : 'parallels'}: ${numEn(ab)} point one way, ${numEn(ba)} the other`,
  later: (side: string) => `${side} later`,
  parallel: 'Parallel',
  direction: 'Direction',
  noData: 'No direction estimates in this build (run `bsim borrowing`).',
  line: (src: string, dst: string, votes: number) =>
    `Which borrowed? ${src} → ${dst} (${numEn(votes)} ${votes === 1 ? 'sign' : 'signs'}; the later-looking side drew on the other)`,
  lineUnclear: (a: string, b: string) => `Which borrowed? ${a} ↔ ${b}: the signs disagree or are silent`,
}

register('bor', borEn)
