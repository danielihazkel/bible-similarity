// Interface strings of Pattern search: a query over the words' lemmas, roots, morphology and syntax
// (DESIGN.md §16.46). English first, Hebrew typed against it. Queries are code, so they are not
// translated; their descriptions are.

import type { PatternErrorCode } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

export interface QueryKeyHelp {
  key: string
  values: string
  meaning: string
}

const q = (t: string | undefined) => (t ? ` “${t}”` : '')
const qh = (t: string | undefined) => (t ? ` ”${t}“` : '')

export const qryEn = {
  title: 'Pattern search',
  lede: 'Find a construction rather than a word: describe each word by its lemma, root, form or role in the clause, and how far apart the words may stand. The search runs inside one verse at a time over every word of the Hebrew Bible.',
  inputLabel: 'Query',
  placeholder: '[form=infabs root=@r] [root=@r form=finite]',
  run: 'Search',
  examplesTitle: 'Examples',
  examples: [
    { q: '[form=infabs root=@r] [root=@r form=finite]', text: 'An infinitive absolute, then a finite verb of the same root (מות יומת)' },
    { q: '[form=imperative] ..4 [function=Voct pos=name]', text: 'A command, then within four words a name called out' },
    { q: '[lemma=408] [form=jussive]', text: 'אל and a jussive: a prohibition' },
    { q: '[pos=verb root=@r] ..2 [pos=noun root=@r]', text: 'A verb and a noun of its own root (ויחלם חלום)' },
    { q: '[lemma=2009 suffix=1cs]', text: 'הנה with a first-person suffix: הנני' },
    { q: '[speaker=משה form=imperative]', text: 'Every command Moses gives' },
  ],
  helpTitle: 'How to write a query',
  syntax: [
    'Each word is a pattern in square brackets: [pos=verb stem=hiphil]. Its conditions are separated by spaces, and all must hold. [] is any word.',
    'key=value or key!=value (not); value|value is either: [form=imperative|jussive].',
    'Patterns follow each other word by word. ..3 between them lets the next one stand up to three words on; .. anywhere later in the verse.',
    'A variable @name repeats a lemma, root or word: [root=@r] ..3 [root=@r] is two words of one root; root!=@r is any other.',
    'A word is described by its main part: prefixes (ו, ה, ב, כ, ל, מ, ש) and the pronominal suffix are keys of their own.',
  ],
  keysCaption: 'Keys and their values',
  keyCols: { key: 'Key', values: 'Values', meaning: 'What it is' },
  keys: [
    { key: 'lemma', values: "559, אמר, @name", meaning: "The lemma: its Strong's number, or a Hebrew form" },
    { key: 'root', values: '1288, ברך, @name', meaning: 'The word family (see Roots)' },
    { key: 'word', values: 'בראשית, @name', meaning: 'The letters of the word, prefixes included' },
    { key: 'pos', values: 'noun, name, verb, adjective, number, preposition, conjunction, adverb, pronoun, particle', meaning: 'Part of speech' },
    { key: 'type', values: 'negative, object, relative, interrogative, article, demonstrative, personal, proper, gentilic, cardinal, ordinal …', meaning: 'Kind of particle, pronoun, noun or adjective' },
    { key: 'stem', values: 'qal, niphal, piel, pual, hiphil, hophal, hithpael, polel …; Aramaic peal, pael, haphel …', meaning: 'Verb stem' },
    { key: 'form', values: 'perfect, weqatal, imperfect, wayyiqtol, cohortative, jussive, imperative, participle, passive-participle, infabs, infcon; finite, infinitive, participles', meaning: 'Verb form' },
    { key: 'person', values: '1, 2, 3', meaning: 'Person' },
    { key: 'gender', values: 'm, f, c', meaning: 'Gender (c: common)' },
    { key: 'number', values: 's, p, d', meaning: 'Number (d: dual)' },
    { key: 'state', values: 'a, c, d', meaning: 'State (absolute, construct; d: Aramaic determined)' },
    { key: 'suffix', values: 'yes, no, 3ms, 1cs …', meaning: 'Pronominal suffix' },
    { key: 'prefix', values: 'ו, ה, ב, כ, ל, מ, ש, none', meaning: 'A prefix the word carries' },
    { key: 'lang', values: 'hebrew, aramaic', meaning: 'Language' },
    { key: 'function', values: 'Subj, Objc, Pred, Cmpl, Voct, Time, Loca, Nega, Ques …', meaning: "The phrase's function (ETCBC syntax)" },
    { key: 'clause', values: 'WayX, Way0, xQtX, NmCl, ZIm0 …', meaning: 'The clause type (ETCBC syntax)' },
    { key: 'speech', values: 'yes, no', meaning: 'Inside a quotation' },
    { key: 'speaker', values: 'משה, 3068 …', meaning: 'Who speaks the quotation (see Who speaks)' },
  ] as QueryKeyHelp[],
  errors: {
    empty: () => 'Write a pattern first: a word in square brackets, such as [lemma=559].',
    expected_pattern: (t: string) => `Expected a word pattern in square brackets${t ? ` at${q(t)}` : ' at the end'}.`,
    unclosed: (t: string) => `This bracket is not closed:${q(t)}.`,
    bad_condition: (t: string) => `A condition is key=value or key!=value:${q(t)}.`,
    unknown_key: (t: string) => `There is no key${q(t)}; the keys are listed under “How to write a query”.`,
    bad_value: (t: string) => `This key does not take${q(t)}.`,
    unknown_value: (t: string) => `No lemma or root${q(t)} in the text; try its Strong's number.`,
    bad_gap: (t: string) => `A gap is .. or ..N, with N from 1 to the length of the longest verse:${q(t)}.`,
    too_many: () => 'Too many word patterns in one query.',
    variable: (t: string) => `A variable (@name) goes with lemma, root or word, and is set with = before it is used with !=:${q(t)}.`,
    too_broad: () => 'Too many matches to list: add a condition or shorten a gap.',
  } satisfies Record<PatternErrorCode, (token: string) => string>,
  at: (n: number) => `at character ${numEn(n + 1)}`,
  summary: (matches: number, verses: number) => `${countEn(matches, 'match', 'matches')} in ${countEn(verses, 'verse', 'verses')}`,
  byBook: 'By book',
  bookCount: (name: string, n: number) => `${name} ${numEn(n)}`,
  allBooks: 'All books',
  empty: 'Nothing matches this pattern.',
  read: 'Read the chapter',
  prompt: 'Write a query above, or start from an example.',
}

export const qryHe: typeof qryEn = {
  title: 'חיפוש תבניות',
  lede: 'חיפוש של מבנה ולא של מילה: כל מילה מתוארת לפי ערכה, שורשה, צורתה או תפקידה במשפט, ולפי המרחק המותר בין המילים. החיפוש רץ בתוך פסוק אחד בכל פעם, על כל מילות המקרא.',
  inputLabel: 'שאילתה',
  placeholder: '[form=infabs root=@r] [root=@r form=finite]',
  run: 'חיפוש',
  examplesTitle: 'דוגמאות',
  examples: [
    { q: '[form=infabs root=@r] [root=@r form=finite]', text: 'מקור מוחלט ואחריו פועל נטוי מאותו שורש (מות יומת)' },
    { q: '[form=imperative] ..4 [function=Voct pos=name]', text: 'ציווי, ובתוך ארבע מילים שם שנקרא בו' },
    { q: '[lemma=408] [form=jussive]', text: 'אל ועתיד מקוצר: איסור' },
    { q: '[pos=verb root=@r] ..2 [pos=noun root=@r]', text: 'פועל ושם עצם משורשו (ויחלם חלום)' },
    { q: '[lemma=2009 suffix=1cs]', text: 'הנה בגוף ראשון: הנני' },
    { q: '[speaker=משה form=imperative]', text: 'כל ציווי שמשה מצווה' },
  ],
  helpTitle: 'איך כותבים שאילתה',
  syntax: [
    'כל מילה היא תבנית בסוגריים מרובעים: [pos=verb stem=hiphil]. התנאים מופרדים ברווחים, וכולם צריכים להתקיים. [] היא כל מילה.',
    'key=value או key!=value (שלילה); value|value הוא אחד מהם: [form=imperative|jussive].',
    'התבניות באות זו אחר זו, מילה אחר מילה. ..3 ביניהן מתיר לבאה לעמוד עד שלוש מילים הלאה; .. בכל מקום בהמשך הפסוק.',
    'משתנה @name חוזר על ערך, שורש או מילה: [root=@r] ..3 [root=@r] הן שתי מילים מאותו שורש; root!=@r הוא כל שורש אחר.',
    'מילה מתוארת לפי חלקה העיקרי: התחיליות (ו, ה, ב, כ, ל, מ, ש) והכינוי החבור הן מפתחות בפני עצמם.',
  ],
  keysCaption: 'המפתחות וערכיהם',
  keyCols: { key: 'מפתח', values: 'ערכים', meaning: 'מה הוא' },
  keys: [
    { key: 'lemma', values: '559, אמר, @name', meaning: 'הערך: מספר סטרונג שלו, או צורה עברית' },
    { key: 'root', values: '1288, ברך, @name', meaning: 'משפחת המילים (ראו שורשים)' },
    { key: 'word', values: 'בראשית, @name', meaning: 'אותיות המילה, כולל התחיליות' },
    { key: 'pos', values: 'noun, name, verb, adjective, number, preposition, conjunction, adverb, pronoun, particle', meaning: 'חלק הדיבר' },
    { key: 'type', values: 'negative, object, relative, interrogative, article, demonstrative, personal, proper, gentilic, cardinal, ordinal …', meaning: 'סוג המילית, הכינוי, השם או התואר' },
    { key: 'stem', values: 'qal, niphal, piel, pual, hiphil, hophal, hithpael, polel …; בארמית peal, pael, haphel …', meaning: 'בניין' },
    { key: 'form', values: 'perfect, weqatal, imperfect, wayyiqtol, cohortative, jussive, imperative, participle, passive-participle, infabs, infcon; finite, infinitive, participles', meaning: 'צורת הפועל' },
    { key: 'person', values: '1, 2, 3', meaning: 'גוף' },
    { key: 'gender', values: 'm, f, c', meaning: 'מין (c: משותף)' },
    { key: 'number', values: 's, p, d', meaning: 'מספר (d: זוגי)' },
    { key: 'state', values: 'a, c, d', meaning: 'מצב (נפרד, נסמך; d: מיודע בארמית)' },
    { key: 'suffix', values: 'yes, no, 3ms, 1cs …', meaning: 'כינוי חבור' },
    { key: 'prefix', values: 'ו, ה, ב, כ, ל, מ, ש, none', meaning: 'תחילית שבמילה' },
    { key: 'lang', values: 'hebrew, aramaic', meaning: 'לשון' },
    { key: 'function', values: 'Subj, Objc, Pred, Cmpl, Voct, Time, Loca, Nega, Ques …', meaning: 'תפקיד הצירוף (תחביר ETCBC)' },
    { key: 'clause', values: 'WayX, Way0, xQtX, NmCl, ZIm0 …', meaning: 'סוג הפסוקית (תחביר ETCBC)' },
    { key: 'speech', values: 'yes, no', meaning: 'בתוך דיבור ישיר' },
    { key: 'speaker', values: 'משה, 3068 …', meaning: 'מי אומר את הדברים (ראו מי מדבר)' },
  ],
  errors: {
    empty: () => 'כתבו קודם תבנית: מילה בסוגריים מרובעים, כגון [lemma=559].',
    expected_pattern: (t: string) => `ציפינו לתבנית מילה בסוגריים מרובעים${t ? ` ב־${qh(t).trim()}` : ' בסוף'}.`,
    unclosed: (t: string) => `הסוגריים לא נסגרו:${qh(t)}.`,
    bad_condition: (t: string) => `תנאי הוא key=value או key!=value:${qh(t)}.`,
    unknown_key: (t: string) => `אין מפתח${qh(t)}; המפתחות מפורטים תחת ”איך כותבים שאילתה“.`,
    bad_value: (t: string) => `המפתח הזה אינו מקבל${qh(t)}.`,
    unknown_value: (t: string) => `אין ערך או שורש${qh(t)} בטקסט; נסו את מספר הסטרונג שלו.`,
    bad_gap: (t: string) => `מרווח הוא .. או ..N, ו־N בין 1 לאורך הפסוק הארוך ביותר:${qh(t)}.`,
    too_many: () => 'יותר מדי תבניות מילה בשאילתה אחת.',
    variable: (t: string) => `משתנה (@name) הולך עם lemma, root או word, ונקבע ב־= לפני שמשתמשים בו עם !=:${qh(t)}.`,
    too_broad: () => 'יותר מדי התאמות להצגה: הוסיפו תנאי או קצרו מרווח.',
  },
  at: (n: number) => `בתו ${numHe(n + 1)}`,
  summary: (matches: number, verses: number) =>
    `${countHe(matches, 'התאמה אחת', 'שתי התאמות', 'התאמות')}, ${verses === 1 ? 'בפסוק אחד' : verses === 2 ? 'בשני פסוקים' : `ב־${numHe(verses)} פסוקים`}`,
  byBook: 'לפי ספר',
  bookCount: (name: string, n: number) => `${name} ${numHe(n)}`,
  allBooks: 'כל הספרים',
  empty: 'אין דבר התואם את התבנית.',
  read: 'קריאת הפרק',
  prompt: 'כתבו שאילתה למעלה, או התחילו מדוגמה.',
}
