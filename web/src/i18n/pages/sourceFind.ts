// Interface strings of the source finder (DESIGN.md §11.1): the biblical phrases of a pasted text.
// English first, Hebrew typed against it.

import { countEn, numEn } from '../fmt'
import { register } from '../en'

export const sfEn = {
  title: 'Source finder',
  lede: 'Paste a Hebrew text, a prayer, a passage of the Mishnah, a letter, and the phrases it takes from the Bible are marked, each with its verse. Spelling, vowel points and the divine name written as ה׳ or יי do not matter.',
  label: 'Hebrew text',
  placeholder: 'אשרי יושבי ביתך…',
  submit: 'Find the sources',
  examples: 'Try',
  exampleNames: { ashrei: 'Ashrei', aleinu: 'Aleinu', priestly: 'The priestly blessing', mishnah: 'Mishnah Berakhot 1:3' } as Record<string, string>,
  chars: (n: number, max: number) => `${numEn(n)} of ${numEn(max)} characters`,
  tooLong: (max: number) => `The text is longer than ${numEn(max)} characters; shorten it to search.`,
  none: 'No phrase of the Bible was found in this text.',
  found: (n: number, words: number) => `${countEn(n, 'passage', 'passages')} from the Bible, ${countEn(words, 'word', 'words')} of the text.`,
  textTitle: 'The text, its biblical phrases marked',
  listTitle: 'The passages',
  passageLabel: (i: number) => `Passage ${numEn(i)}`,
  matched: (n: number) => countEn(n, 'word matched', 'words matched'),
  alsoIn: 'The same words also in',
  how: 'Each pair of adjacent words is looked up in the verses; a verse that has the pair is aligned with the text round it, rare words counting for more. Phrases so common that they are in many verses seed nothing, so a formula alone is not a source.',
}

register('sf', sfEn)
