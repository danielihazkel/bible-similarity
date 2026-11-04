// Interface strings of the naming etiologies page (DESIGN.md §16.66): the names the text gives and
// the words of the verse that explain them. English first, Hebrew typed against it. The names and
// the words are Hebrew in both.

import { countEn, numEn } from '../fmt'
import { register } from '../en'

export const pct = (x: number, locale: string) => `${Math.round(x * 100).toLocaleString(locale)}%`
export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export type EtyShow = 'all' | 'leads' | 'known'
export type EtyOrder = 'canon' | 'strongest'

export const etyEn = {
  title: 'Naming etiologies',
  lede: 'When the text names someone or somewhere, it often says why, in words that sound like the name: \u2068ותקרא שמו ראובן כי אמרה כי ראה יהוה בעניי\u2069 (Genesis 29:32). Every naming formula (\u2068ויקרא שמו\u2069, \u2068ויקרא שם המקום\u2069, \u2068קרא למקום\u2069) is found here, and its verse is searched for the word that echoes the name best.',
  notComputed: 'The naming etiologies were not computed in this build (run bsim etiologies).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  echo: {
    title: 'A name echoes its own explanation',
    text: (own: number, chance: number, n: number, p: number) =>
      `On average ${pct(own, 'en-US')} of a name’s consonants stand in order in one word of its own verse, against ${pct(chance, 'en-US')} with the explanations shuffled among the ${countEn(n, 'naming', 'namings')} (p ${fp(p)}).`,
  },
  known: {
    title: 'The etiologies everyone agrees on',
    text: (found: number, echo: number, n: number, rank: number, share: number) =>
      `The formula finds ${numEn(found)} of the ${numEn(n)} named in advance (Jacob’s sons, \u2068נח\u2069, \u2068שת\u2069, \u2068משה\u2069, \u2068באר שבע\u2069, \u2068בית אל\u2069); ${numEn(echo)} of them echo their name better than all but ${pct(rank, 'en-US')} of the other explanations. The check asked for ${pct(share, 'en-US')}.`,
    missing: (refs: string) => `Not found: ${refs}.`,
  },
  listTitle: 'The namings',
  show: { label: 'Show', all: (n: number) => `All (${numEn(n)})`, leads: (n: number) => `Beyond chance (${numEn(n)})`, known: (n: number) => `Named in advance (${numEn(n)})` },
  order: { label: 'Order', canon: 'Canon', strongest: 'Strongest first' },
  kind: { person: 'person', place: 'place' },
  echoedBy: 'echoed by',
  noEcho: 'no word of the verse echoes it',
  score: (s: number) => `${pct(s, 'en-US')} of its letters`,
  chance: (c: number) => `typical ${pct(c, 'en-US')}`,
  pq: (p: number, q: number) => `p ${fp(p)}, q ${fp(q)}`,
  knownTag: 'named in advance',
  empty: 'No naming here.',
  method:
    'A naming: a form of \u2068קרא\u2069, then within three words \u2068שמו\u2069 / \u2068שם\u2069 + a noun, \u2068למקום\u2069 or a pronoun object, then a proper noun (not a name of God; not after \u2068לא\u2069). Its explanation: the other content words of its verse, without their prefixes. The echo: the most of a name word’s consonants found in order in one of them. p: the echo against 9,999 verses without a naming; q: Benjamini–Hochberg over the namings.',
}

register('ety', etyEn)
