// Interface strings of names built on God's name (DESIGN.md §16.90, D152): the Language page's
// section and the line on a name's panel. English first, Hebrew typed against it.

import { countEn, numEn, pct } from '../fmt'
import { register } from '../en'

export const theoEn = {
  title: 'Names built on God’s name',
  lede: 'Many names carry God’s name: ירמיהו or ירמיה, יהורם or יורם, ישמעאל. The long ending ‑יהו is the older spelling and the short ‑יה the later, though most books write both. Here every occurrence of a name HebrewStrong derives from יה, יהוה or אל, by the form it is written in.',
  claim: (late: number, early: number, names: number, p: string) =>
    `For the same names, the late books (Chronicles, Ezra–Nehemiah, Esther, Daniel) spell the ending short ${pct(late)} of the time, Genesis–Kings ${pct(early)} (${countEn(names, 'name', 'names')} in both; p ${p}, each name’s spellings shuffled between the two).`,
  verdict: { holds: 'Borne out', fails: 'Not borne out' } as Record<'holds' | 'fails', string>,
  knownTitle: 'Named in advance',
  known: (books: string, side: string, short: number | null, endings: number, holds: boolean) =>
    `${books}: mostly ${side === 'long' ? 'long (‑יהו)' : 'short (‑יה)'}: ${short === null ? 'no endings' : `${pct(short)} short of ${countEn(endings, 'ending', 'endings')}`} · ${holds ? 'holds' : 'does not hold'}`,
  notInModel:
    'The short ending is also measured as a feature of the late-language profile, but left out of the model: with it the profile told books apart less well (2 Chronicles keeps the long spellings of Kings).',
  booksTitle: 'By book',
  cols: { book: 'Book', yahu: '‑יהו', yah: '‑יה', short: 'Short', yeho: 'יהו‑', yo: 'יו‑', el: 'With אל' },
  namesTitle: 'The most frequent names',
  namesCols: { name: 'Name', n: 'Occurrences', forms: 'Forms' },
  forms: { yahu: '‑יהו', yah: '‑יה', yeho: 'יהו‑', yo: 'יו‑', el_first: 'אל‑', el_last: '‑אל' } as Record<string, string>,
  line: (divine: string, forms: string) => `Built on ${divine === 'el' ? 'אל' : 'יה'}: ${forms}.`,
  times: (form: string, n: number) => `${form} ${numEn(n)}×`,
}

register('theo', theoEn)
