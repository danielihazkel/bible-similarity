// Interface strings of the dossier bar on a unit page: what every analysis found about this unit
// (DESIGN.md §10). English first, Hebrew typed against it.

import type { DossierKind } from '../../api/types'
import { countEn, numEn } from '../fmt'

export const fmtQ = (q: number) => (q < 0.001 ? '< 0.001' : q < 0.01 ? q.toFixed(3) : q.toFixed(2))

export const dosEn = {
  label: 'What the analyses found here',
  what: 'what the analyses found here',
  found: 'Found here:',
  none: 'Nothing found:',
  notComputed: 'Not computed in this build:',
  inChapter: ' (chapter)',
  /** a finding, with its count or value */
  chip: {
    phrases: (n: number) => countEn(n, 'shared phrase', 'shared phrases'),
    sequences: (n: number) => countEn(n, 'parallel run', 'parallel runs'),
    changes: (n: number) => countEn(n, 'word change in parallels', 'word changes in parallels'),
    borrowing: (n: number) => countEn(n, 'parallel with a borrowing estimate', 'parallels with a borrowing estimate'),
    wordplay: (n: number) => countEn(n, 'wordplay pair', 'wordplay pairs'),
    alliteration: (n: number) => countEn(n, 'alliteration candidate', 'alliteration candidates'),
    rhymes: (n: number) => countEn(n, 'rhyme run', 'rhyme runs'),
    typescenes: (n: number) => countEn(n, 'action sequence', 'action sequences'),
    discoveries: (n: number) => countEn(n, 'strong pair without a Sefaria link', 'strong pairs without a Sefaria link'),
    seams: (n: number) => countEn(n, 'style seam', 'style seams'),
    names: (n: number) => countEn(n, 'name', 'names'),
    labels: (n: number) => countEn(n, 'pair you labelled', 'pairs you labelled'),
    acrostic: (q: number) => `acrostic, q ${fmtQ(q)}`,
    structure: (q: number) => `inclusio / chiasm, q ${fmtQ(q)}`,
    dating: (score: number) => `late-language profile ${score.toFixed(2)}`,
    speech: (n: number, who: string | null) => `${countEn(n, 'quotation clause', 'quotation clauses')}${who ? `, mostly ${who}` : ''}`,
    voices: (who: string) => `the voice of ${who}`,
    network: (rank: number, of: number) => `echoes: number ${numEn(rank)} of ${numEn(of)}`,
    divisions: (n: number, key: string | null) =>
      n === 1 && key === 'turn'
        ? 'opens at an unmarked turn'
        : n === 1 && key === 'cut'
          ? 'a chapter start inside running text'
          : n === 1 && key === 'quiet'
            ? 'opens at a quiet paragraph break'
            : countEn(n, 'point where text and division disagree', 'points where text and division disagree'),
    ketiv: (n: number) => countEn(n, 'word written one way and read another', 'words written one way and read another'),
    citations: (n: number) => countEn(n, 'explicit citation', 'explicit citations'),
    allusions: (n: number) => countEn(n, 'passage sharing rare words', 'passages sharing rare words'),
    mirrors: (n: number) => countEn(n, 'mirrored order', 'mirrored orders'),
    echoes: (n: number) => countEn(n, 'directed echo with another book', 'directed echoes with other books'),
    meter: (net: number) => `lines fall like a lament (net ${net.toFixed(2)})`,
    roots: (n: number) => countEn(n, 'pair of words of one root', 'pairs of words of one root'),
    refrains: (n: number) => countEn(n, 'refrain', 'refrains'),
    psalms: (n: number) => countEn(n, 'psalm: its genre, form and turn', 'psalms: their genres, form and turns'),
    pentateuch: (n: number) => countEn(n, 'verse on the P-like side', 'verses on the P-like side'),
    dialogue: (n: number) => countEn(n, 'exchange between two speakers', 'exchanges between two speakers'),
    forms: (n: number) => countEn(n, 'graded numerical saying or list', 'graded numerical sayings and lists'),
    places: (n: number, top: string | null) => `${countEn(n, 'place', 'places')} on the map${top ? `, most named ${top}` : ''}`,
    people: (n: number, top: string | null) => `${countEn(n, 'person', 'people')} in the family tree${top ? `, most named ${top}` : ''}`,
    divine: (n: number, top: string | null, share: number | null) =>
      `${countEn(n, 'name of God', 'names of God')}${top ? `, most often ${top}` : ''}${share === null ? '' : ` (\u2068יהוה\u2069 ${Math.round(share * 100)}% of \u2068יהוה\u2069 and \u2068אלהים\u2069)`}`,
    ciphers: (n: number, words: string | null, name: string | null) =>
      `${countEn(n, 'name read through atbash or albam', 'names read through atbash or albam')}${words && name ? ` (${words} read as ${name})` : ''}`,
    gematria: (n: number, texts: string | null, value: number | null, others: number | null) =>
      [
        value === null ? null : `letter value ${numEn(value)}${others ? `, as in ${countEn(others, 'other verse', 'other verses')}` : ', in no other verse'}`,
        n > 0 && texts ? `the tradition's values: ${texts}` : null,
      ]
        .filter(Boolean)
        .join(' · '),
  },
  /** the analysis's name, in the "nothing found" / "not computed" lines */
  kinds: {
    phrases: 'shared phrases',
    sequences: 'parallel runs',
    changes: 'word changes',
    borrowing: 'who borrowed',
    wordplay: 'wordplay',
    alliteration: 'alliteration',
    rhymes: 'rhyme',
    typescenes: 'action sequences',
    discoveries: 'unlinked strong pairs',
    seams: 'style seams',
    names: 'names',
    labels: 'your labels',
    acrostic: 'acrostic',
    structure: 'inclusio / chiasm',
    dating: 'language profile',
    speech: 'direct speech',
    voices: 'speaker voices',
    network: 'echo network',
    divisions: 'text and divisions',
    ketiv: 'ketiv and qere',
    citations: 'explicit citations',
    allusions: 'rare words shared',
    mirrors: 'mirrored order',
    echoes: 'who echoes whom',
    meter: 'falling lines',
    roots: 'words of one root',
    refrains: 'refrains',
    psalms: 'psalm form',
    pentateuch: 'P-like verses',
    dialogue: 'exchanges',
    forms: 'numerical sayings and lists',
    places: 'places on the map',
    people: 'people in the family tree',
    ciphers: 'atbash and albam',
    divine: 'names of God',
    gematria: 'letter values',
  } as Record<DossierKind, string>,
}
