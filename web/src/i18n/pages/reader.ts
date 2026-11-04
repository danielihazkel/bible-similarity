// Interface strings of the layered reader: a chapter with what the analyses found painted onto its
// words (DESIGN.md §16.39). English first, Hebrew typed against it.

import type { Paragraph, SegmentKind } from '../../api/types'
import { countEn } from '../fmt'

export type Layer = 'speakers' | 'cola' | 'leitworte' | 'refrains' | 'phrases' | 'rare' | 'wordplay' | 'ketiv' | 'mood' | 'sources' | 'turns' | 'gematria' | 'places' | 'divine' | 'reception'

export const pctOf = (x: number) => Math.round(x * 100)

export const readerEn = {
  title: 'Reader',
  lede: 'The text with what the analyses found painted onto its words. Turn layers on and off; hover a word for what each layer says about it, click it for its grammar.',
  open: 'Read with layers',
  openTitle: 'The text with its speakers, Leitworte, verse halves, wordplay and more marked on the words',
  unitPage: 'Similar passages and every analysis',
  layersLabel: 'Layers',
  layers: {
    speakers: 'Speakers',
    cola: 'Verse halves',
    leitworte: 'Leitworte',
    refrains: 'Refrains',
    phrases: 'Shared phrases',
    rare: 'Rare words',
    wordplay: 'Wordplay',
    ketiv: 'Ketiv / qere',
    mood: 'Distress and praise',
    sources: 'P / non-P',
    turns: 'Turns',
    gematria: 'Gematria',
    places: 'Places',
    divine: 'Names of God',
    reception: 'Rabbinic citations',
  } satisfies Record<Layer, string>,
  hints: {
    speakers: 'Who speaks each word (BHSA quotations and the speakers found for them)',
    cola: 'Where the accents divide each verse into halves and clauses',
    leitworte: 'Words repeated here far more than in the rest of the Bible',
    refrains: 'Phrases that come back nearby, more densely than chance',
    phrases: 'Words in a phrase another verse shares',
    rare: 'Words found in only a few verses of the Bible',
    wordplay: 'Words a few apart that sound alike',
    ketiv: 'Words read otherwise than they are written',
    mood: 'Words of distress and of praise (SDBH domains): where a lament turns',
    sources: 'Which side of the unsupervised P / non-P split each verse of Genesis–Numbers falls on',
    turns: 'Where the text changes sharply between verses, and the paragraph breaks of the tradition',
    gematria: 'Each word’s letter value, and each verse’s total',
    places: 'The places named, by kind, each linked to the map',
    divine: 'Each name of God marked by a line above it: יהוה, אלהים, and the others',
    reception: 'How many passages of the Mishnah, the Tosefta and the Talmuds cite each verse',
  } satisfies Record<Layer, string>,
  notComputed: (layer: string) => `${layer}: not computed in this build.`,
  loading: (layer: string) => `Loading ${layer.toLowerCase()}…`,
  // speakers
  speakersKey: 'Who speaks (a dotted line: speech whose speaker was not found):',
  noSpeech: 'No quoted speech here.',
  unknownSpeaker: 'speaker not found',
  divine: 'God',
  spokenBy: (who: string) => `spoken by ${who}`,
  speakerWords: (n: number) => countEn(n, 'word', 'words'),
  // cola
  colaKey: '‖ ends a verse half, | a clause: the pauses of the accents.',
  // Leitworte
  leitworteKey: 'Most over-represented first:',
  countBy: 'Count',
  byWord: 'By word',
  byRoot: 'By root',
  noLeitworte: 'No Leitworte here.',
  leitwortTitle: (he: string, count: number, expected: string) => `Leitwort ${he}: ${count} times here, ${expected} expected`,
  // mood
  moodKey: 'A bar under a word: solid, a word of praise (praise, song, joy, blessing); dashed, a word of distress (fear, grief, shame, sickness, enemies).',
  moodTitle: { distress: 'a word of distress', praise: 'a word of praise' } as Record<string, string>,
  // sources
  sourcesKey: 'A tag after the verse number: its side of the unsupervised split (Genesis–Numbers); outlined where the critics assign it to the other source.',
  sourceTag: { P: 'P', nonP: 'non-P' } as Record<string, string>,
  sourceTitle: (side: string, prob: number, reference: string | null) =>
    `${side === 'P' ? 'P-like' : 'not P-like'} (${Math.round(prob * 100)}% P-like); the critics: ${reference === null ? 'unassigned' : reference === 'P' ? 'P' : 'non-P'}`,
  allSources: "The split on the Pentateuch's sources page",
  // refrains
  refrainsKey: 'A line above: a phrase that comes back nearby (a refrain).',
  noRefrains: 'No refrain here.',
  refrainTitle: (text: string, k: number) => `refrain ${text}: in ${countEn(k, 'verse', 'verses')}`,
  allRefrains: 'Every refrain here',
  // phrases
  phrasesKey: 'Underlined: in a phrase another verse shares (thicker: more verses).',
  phraseTitle: (n: number) => `in a phrase shared with ${countEn(n, 'other verse', 'other verses')}`,
  // rare words
  rareKey: (max: number) =>
    `A small number after a word: its rarest word is in only that many verses of the Bible (at most ${max}; names left out). 1: nowhere else.`,
  rareTitle: (n: number) => (n === 1 ? 'nowhere else in the Bible (hapax legomenon)' : `in ${n} verses of the Bible`),
  // gematria
  gematriaKey: '=913 after a word: its letter value (standard gematria). After the verse number, the verse’s total: click it for the verses that add up to the same.',
  gematriaTitle: (v: number) => `letter value ${v.toLocaleString('en-US')}`,
  gematriaTotalTitle: (v: number) => `The verse adds up to ${v.toLocaleString('en-US')}: every verse of this value`,
  // wordplay
  wordplayKey: 'Dashed box: sounds like a word nearby. Click a word to mark its partner.',
  wordplayTitle: (partner: string, where: string, kind: string) => `sounds like ${partner} (${where}): ${kind}`,
  // ketiv / qere
  ketivKey: 'ק after a word: it is read otherwise than written.',
  ketivTitle: (ketiv: string, qere: string, cls: string) => `written ${ketiv || '–'}, read ${qere}: ${cls}`,
  // turns
  turnsKey:
    'Between verses: a turn (the text changes more sharply than almost anywhere in the book, with no break marked), a chapter cutting running text, a quiet break, and the paragraph breaks of the MAM, פ and ס.',
  gapKinds: { turn: 'turn', cut: 'chapter in running text', quiet: 'quiet break' } satisfies Record<SegmentKind, string>,
  gapTitle: (score: number) => `The text changes here more than at ${pctOf(score)}% of the book's verse gaps.`,
  paragraphTitle: { pe: 'Open paragraph (MAM)', samekh: 'Closed paragraph (MAM)' } satisfies Record<Paragraph, string>,
  // places
  placesKey: 'A place’s name boxed in the colour of its kind (town, region, landform, water); the places here, on the map:',
  noPlaces: 'No place is named here.',
  placeTitle: (he: string, kind: string) => `${he}: ${kind}`,
  allPlaces: 'all on the map',
  // divine names
  divineKey: 'A line above each name of God: \u2068יהוה\u2069, \u2068אלהים\u2069, another name;',
  divineTitle: (he: string) => `a name of God: ${he}`,
  allDivine: 'the mix of every chapter',
}
