// The Hebrew half of `../ciphers.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { cphEn, fp } from '../ciphers'

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
