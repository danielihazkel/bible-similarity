// Interface strings of Patterns → Atbash and albam: names hidden by a letter swap, against random
// swaps (DESIGN.md §16.54). English first, Hebrew typed against it.

import type { CipherName } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const cphEn = {
  title: 'Atbash and albam',
  lede: 'Atbash writes each letter as its mirror in the alphabet (א↔ת, ב↔ש …), albam as its partner in the other half (א↔ל, ב↔מ …). Jeremiah writes Babel as ששך and the Chaldeans as לב קמי. Here every unusual word, and every two words read as one, is read through both swaps and kept when it becomes a name of the Bible; random swaps of the letters show how many names chance alone gives.',
  noData: 'Not computed in this build: run `bsim ciphers`, then `bsim build-db`.',
  summary: (names: number, spans: number, single: number, shuffles: number) =>
    `${numEn(names)} names; ${numEn(spans)} places a cipher could hide (${numEn(single)} rare words, the rest two words read as one); ${numEn(shuffles)} random swaps of the 22 letters as the measure of chance.`,
  checksTitle: 'The checks, fixed in advance',
  verdict: { holds: 'holds', fails: 'does not hold' },
  known: (found: number, n: number) => `The places named in advance are found: ${numEn(found)} of ${numEn(n)}.`,
  jeremiah: (obs: number, exp: number, p: number, where: string) =>
    `In ${where}, atbash reads ${countEn(obs, 'name', 'names')} against ${exp.toFixed(2)} for a random swap (p ${fp(p)}).`,
  elsewhere: (obs: number, exp: number, p: number) =>
    `In the rest of the Bible, atbash reads ${countEn(obs, 'name', 'names')} against ${exp.toFixed(1)} for a random swap (p ${fp(p)}).`,
  albam: (obs: number, exp: number, p: number) =>
    `Albam, anywhere: ${countEn(obs, 'name', 'names')} against ${exp.toFixed(1)} (p ${fp(p)}). Isaiah 7:6’s טבאל, which Rashi reads by albam as רמלא (Remaliah), is not a name as the text writes it: noted, not tested.`,
  knownTitle: 'Named in advance',
  knownCols: { where: 'Verse', cipher: 'Swap', text: 'Written', name: 'Reads as', found: 'Found' },
  found: 'found',
  missing: 'not found',
  ciphers: { atbash: 'Atbash', albam: 'Albam' } satisfies Record<CipherName, string>,
  cipher: 'Swap',
  both: 'Both',
  hitsTitle: 'Names read through a swap',
  hitsLede: 'A random swap of the letters turns about as many words into names, so most of these are chance; the places named in advance are marked.',
  hitCount: (n: number) => countEn(n, 'name', 'names'),
  reads: 'reads',
  named: 'named in advance',
  knownOnly: 'Only those named in advance',
  emptyHits: 'No name read through a swap here.',
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  chaptersTitle: 'Chapters against random swaps',
  chaptersLede: (n: number) =>
    `The chapters with a name read through a swap, the least likely by chance first: p is the share of random swaps that read as many names there, q corrects for the ${numEn(n)} chapters.`,
  chaptersCols: { chapter: 'Chapter', cipher: 'Swap', hits: 'Names', expected: 'Random swap', p: 'p', q: 'q' },
  // the word panel
  wordCiphers: 'Swapped',
  wordCipherTitle: (n: number) => (n > 0 ? `written ${countEn(n, 'time', 'times')} in the Bible` : 'not written in the Bible'),
}

export const cphHe: typeof cphEn = {
  title: 'את״ב״ש ואל״ב״ם',
  lede: 'את״ב״ש כותב כל אות כתמונת הראי שלה באלף־בית (א↔ת, ב↔ש …), ואל״ב״ם כבת זוגה בחצי השני (א↔ל, ב↔מ …). ירמיהו כותב את בבל ששך ואת הכשדים לב קמי. כאן כל מילה חריגה, וכל שתי מילים שנקראות כאחת, נקראות בשתי ההמרות ונשמרות כשהן נעשות שם מן המקרא; המרות אקראיות של האותיות מראות כמה שמות נותן המקרה לבדו.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim ciphers` ואחר כך `bsim build-db`.',
  summary: (names: number, spans: number, single: number, shuffles: number) =>
    `${numHe(names)} שמות; ${numHe(spans)} מקומות שצופן יכול להסתתר בהם (${numHe(single)} מילים נדירות, והשאר שתי מילים שנקראות כאחת); ${numHe(shuffles)} המרות אקראיות של 22 האותיות כמדד למקרה.`,
  checksTitle: 'הבדיקות, שנקבעו מראש',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  known: (found: number, n: number) => `המקומות שנמנו מראש נמצאים: ${numHe(found)} מתוך ${numHe(n)}.`,
  jeremiah: (obs: number, exp: number, p: number, where: string) =>
    `ב${where}, את״ב״ש קורא ${countHe(obs, 'שם אחד', 'שני שמות', 'שמות')} לעומת ${exp.toFixed(2)} בהמרה אקראית (p ${fp(p)}).`,
  elsewhere: (obs: number, exp: number, p: number) =>
    `בשאר המקרא, את״ב״ש קורא ${countHe(obs, 'שם אחד', 'שני שמות', 'שמות')} לעומת ${exp.toFixed(1)} בהמרה אקראית (p ${fp(p)}).`,
  albam: (obs: number, exp: number, p: number) =>
    `אל״ב״ם, בכל מקום: ${countHe(obs, 'שם אחד', 'שני שמות', 'שמות')} לעומת ${exp.toFixed(1)} (p ${fp(p)}). טבאל שבישעיהו ז:ו, שרש״י קורא באל״ב״ם רמלא (רמליהו), אינו שם כפי שהכתוב כותב אותו: נזכר, לא נבדק.`,
  knownTitle: 'שנמנו מראש',
  knownCols: { where: 'פסוק', cipher: 'המרה', text: 'כתוב', name: 'נקרא', found: 'נמצא' },
  found: 'נמצא',
  missing: 'לא נמצא',
  ciphers: { atbash: 'את״ב״ש', albam: 'אל״ב״ם' },
  cipher: 'המרה',
  both: 'שתיהן',
  hitsTitle: 'שמות שנקראים בהמרה',
  hitsLede: 'המרה אקראית של האותיות הופכת לשמות מילים כמעט באותו מספר, ולכן רובם מקרה; המקומות שנמנו מראש מסומנים.',
  hitCount: (n: number) => countHe(n, 'שם אחד', 'שני שמות', 'שמות'),
  reads: 'נקרא',
  named: 'נמנה מראש',
  knownOnly: 'רק שנמנו מראש',
  emptyHits: 'אין כאן שם שנקרא בהמרה.',
  pageOf: (page: number, pages: number) => `עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  chaptersTitle: 'פרקים מול המרות אקראיות',
  chaptersLede: (n: number) =>
    `הפרקים שיש בהם שם שנקרא בהמרה, הפחות סבירים במקרה ראשונים: p הוא חלקן של ההמרות האקראיות שקוראות שם שמות כמספר הזה, ו־q מתקן לכל ${numHe(n)} הפרקים.`,
  chaptersCols: { chapter: 'פרק', cipher: 'המרה', hits: 'שמות', expected: 'המרה אקראית', p: 'p', q: 'q' },
  wordCiphers: 'בהמרה',
  wordCipherTitle: (n: number) => (n > 0 ? `כתוב ${countHe(n, 'פעם אחת', 'פעמיים', 'פעמים')} במקרא` : 'אינו כתוב במקרא'),
}
