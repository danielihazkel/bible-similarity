// Interface strings of Patterns → Gematria: a text's letter values and what has the same value
// (DESIGN.md §16.53). English first, Hebrew typed against it.

import type { GematriaSystem, GematriaView } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

export const gmEn = {
  title: 'Gematria',
  lede: 'Every Hebrew letter is also a number (א 1, י 10, ק 100 …), and a word’s gematria is the sum of its letters. Type a word or a number for its value in four counting systems and the words, lemmas and verses of the Bible that add up to the same.',
  noData: 'Not computed in this build: run `bsim gematria`, then `bsim build-db`.',
  input: 'Word or number',
  placeholder: 'אליעזר · 318',
  noLetters: 'Type Hebrew letters or a number.',
  system: 'System',
  systems: { standard: 'Standard', gadol: 'Large', ordinal: 'Ordinal', katan: 'Reduced' } satisfies Record<GematriaSystem, string>,
  systemHints: {
    standard: 'א 1 … ט 9, י 10 … צ 90, ק 100 … ת 400; a final letter counts as its letter',
    gadol: 'Mispar gadol: as the standard, with the final forms ך ם ן ף ץ at 500 … 900',
    ordinal: 'Mispar siduri: each letter’s place in the alphabet, 1 … 22',
    katan: 'Mispar katan: the standard value without its zeros (י 1, ק 1, ר 2)',
  } satisfies Record<GematriaSystem, string>,
  valuesOf: (letters: string) => `The value of ${letters} in each system (click one to search by it):`,
  view: 'Show',
  views: {
    forms: (n: number) => `Words (${numEn(n)})`,
    lemmas: (n: number) => `Lemmas (${numEn(n)})`,
    verses: (n: number) => `Verses (${numEn(n)})`,
  } satisfies Record<GematriaView, (n: number) => string>,
  summary: (value: number, system: string, forms: number, words: number, lemmas: number, verses: number) =>
    `${numEn(value)} (${system}): ${countEn(forms, 'written form', 'written forms')} (${countEn(words, 'word', 'words')} in the text), ${countEn(lemmas, 'lemma', 'lemmas')} and ${countEn(verses, 'verse', 'verses')}.`,
  ledes: {
    forms: 'Each form as written, with its prefixes (והארץ is not הארץ), the commonest first.',
    lemmas: 'Dictionary words, valued by their headword in Strong’s dictionary, the commonest first.',
    verses: 'Verses whose words add up to this value, in canon order.',
  } satisfies Record<GematriaView, string>,
  empty: {
    forms: 'No written form has this value.',
    lemmas: 'No lemma has this value.',
    verses: 'No verse has this value.',
  } satisfies Record<GematriaView, string>,
  formCount: (words: number, verses: number) => `${countEn(words, 'time', 'times')} in ${countEn(verses, 'verse', 'verses')}`,
  firstIn: 'first in',
  lemmaWords: (n: number) => countEn(n, 'word', 'words'),
  verseCount: (letters: number, words: number) => `${countEn(letters, 'letter', 'letters')}, ${countEn(words, 'word', 'words')}`,
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  knownTitle: 'Traditional equivalences',
  knownLede:
    'Words the tradition reads together because they add up alike. Click one to look it up. An equal value is not evidence of a link: whether words of equal value are closer in meaning than chance is a separate test.',
  // the word panel and the reader
  wordValue: (v: number) => `gematria ${numEn(v)}`,
  wordValueTitle: 'Its letter value (standard): every word and verse of the same value',
}

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
