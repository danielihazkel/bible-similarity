// The Hebrew half of `../gematria.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import type { gmEn } from '../gematria'

export const gmHe: typeof gmEn = {
  title: 'גימטריה',
  lede: 'כל אות עברית היא גם מספר (א 1, י 10, ק 100 …), והגימטריה של מילה היא סכום אותיותיה. אפשר להקליד מילה או מספר: ערכם בארבע שיטות מניין, והמילים, הלמות והפסוקים במקרא שמסתכמים באותו ערך.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim gematria` ואחר כך `bsim build-db`.',
  input: 'מילה או מספר',
  placeholder: 'אליעזר · 318',
  noLetters: 'יש להקליד אותיות עבריות או מספר.',
  system: 'שיטה',
  systems: { standard: 'רגיל', gadol: 'גדול', ordinal: 'סידורי', katan: 'קטן' },
  systemHints: {
    standard: 'א 1 … ט 9, י 10 … צ 90, ק 100 … ת 400; אות סופית כאות עצמה',
    gadol: 'מספר גדול: כרגיל, והאותיות הסופיות ך ם ן ף ץ 500 … 900',
    ordinal: 'מספר סידורי: מקומה של האות באלף־בית, 1 … 22',
    katan: 'מספר קטן: הערך הרגיל בלי האפסים (י 1, ק 1, ר 2)',
  },
  valuesOf: (letters: string) => `ערכו של ${letters} בכל שיטה (לחיצה מחפשת לפיה):`,
  view: 'הצגה',
  views: {
    forms: (n: number) => `מילים (${numHe(n)})`,
    lemmas: (n: number) => `למות (${numHe(n)})`,
    verses: (n: number) => `פסוקים (${numHe(n)})`,
  },
  summary: (value: number, system: string, forms: number, words: number, lemmas: number, verses: number) =>
    `${numHe(value)} (${system}): ${countHe(forms, 'צורה כתובה אחת', 'שתי צורות כתובות', 'צורות כתובות')} (${countHe(words, 'מילה אחת', 'שתי מילים', 'מילים')} בטקסט), ${countHe(lemmas, 'למה אחת', 'שתי למות', 'למות')} ו־${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}.`,
  ledes: {
    forms: 'כל צורה כפי שהיא כתובה, עם תחיליותיה (והארץ אינה הארץ), השכיחה ראשונה.',
    lemmas: 'מילות מילון, לפי ערכה של מילת הערך במילון סטרונג, השכיחה ראשונה.',
    verses: 'פסוקים שמילותיהם מסתכמות בערך זה, לפי סדר המקרא.',
  },
  empty: {
    forms: 'אין צורה כתובה בערך זה.',
    lemmas: 'אין למה בערך זה.',
    verses: 'אין פסוק בערך זה.',
  },
  formCount: (words: number, verses: number) =>
    `${countHe(words, 'פעם אחת', 'פעמיים', 'פעמים')} ב־${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}`,
  firstIn: 'לראשונה ב־',
  lemmaWords: (n: number) => countHe(n, 'מילה אחת', 'שתי מילים', 'מילים'),
  verseCount: (letters: number, words: number) =>
    `${countHe(letters, 'אות אחת', 'שתי אותיות', 'אותיות')}, ${countHe(words, 'מילה אחת', 'שתי מילים', 'מילים')}`,
  pageOf: (page: number, pages: number) => `עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  knownTitle: 'שוויונות מן המסורת',
  knownLede:
    'מילים שהמסורת קוראת יחד כי הן מסתכמות באותו ערך. לחיצה מחפשת אותן. ערך שווה אינו ראיה לקשר: אם מילים שוות ערך קרובות יותר במשמען מן המקרה — זו בדיקה נפרדת.',
  wordValue: (v: number) => `גימטריה ${numHe(v)}`,
  wordValueTitle: 'ערך אותיותיה (רגיל): כל מילה ופסוק באותו ערך',
}
