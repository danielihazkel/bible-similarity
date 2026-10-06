// Interface strings of the BHSA syntax layer (DESIGN.md §16.26): the clause panel of a unit and
// the Speech page. English first, Hebrew typed against it.

import { numEn, numHe } from '../fmt'

type Lead = 'w' | 'wx' | 'wX' | 'x' | 'X' | 'z'
type Form = 'way' | 'qatal' | 'yiqtol' | 'imv'
/** Verbal clause types: what comes before the verb, the verb form, a subject after it. */
const VERBAL: Record<string, [Lead, Form, boolean]> = {
  Way0: ['w', 'way', false], WayX: ['w', 'way', true],
  WQt0: ['w', 'qatal', false], WQtX: ['w', 'qatal', true],
  WxQ0: ['wx', 'qatal', false], WxQX: ['wx', 'qatal', true], WXQt: ['wX', 'qatal', false],
  xQt0: ['x', 'qatal', false], xQtX: ['x', 'qatal', true], XQtl: ['X', 'qatal', false],
  ZQt0: ['z', 'qatal', false], ZQtX: ['z', 'qatal', true],
  WYq0: ['w', 'yiqtol', false], WYqX: ['w', 'yiqtol', true],
  WxY0: ['wx', 'yiqtol', false], WxYX: ['wx', 'yiqtol', true], WXYq: ['wX', 'yiqtol', false],
  xYq0: ['x', 'yiqtol', false], xYqX: ['x', 'yiqtol', true], XYqt: ['X', 'yiqtol', false],
  ZYq0: ['z', 'yiqtol', false], ZYqX: ['z', 'yiqtol', true],
  WIm0: ['w', 'imv', false], WImX: ['w', 'imv', true],
  WxI0: ['wx', 'imv', false], WXIm: ['wX', 'imv', false],
  xIm0: ['x', 'imv', false], xImX: ['x', 'imv', true], XImp: ['X', 'imv', false],
  ZIm0: ['z', 'imv', false], ZImX: ['z', 'imv', true],
}  // prettier-ignore

function verbal(code: string, forms: Record<Form, string>, leads: Record<Lead, (f: string) => string>, after: string) {
  const v = VERBAL[code]
  if (!v) return undefined
  const [lead, form, subj] = v
  return leads[lead](forms[form]) + (subj ? after : '')
}

const CLAUSES_EN: Record<string, string> = {
  NmCl: 'nominal clause',
  AjCl: 'adjective clause',
  Ptcp: 'participle clause',
  InfC: 'infinitive construct',
  InfA: 'infinitive absolute',
  Ellp: 'ellipsis',
  Voct: 'address',
  CPen: 'casus pendens',
  MSyn: 'discourse marker (ויהי, והנה)',
  XPos: 'extraposition',
  Reop: 'resumption',
}
const CLAUSES_HE: Record<string, string> = {
  NmCl: 'משפט שמני',
  AjCl: 'משפט תוארי',
  Ptcp: 'משפט בינוני',
  InfC: 'מקור נטוי',
  InfA: 'מקור מוחלט',
  Ellp: 'משפט חסר',
  Voct: 'פנייה',
  CPen: 'יחידה מופקעת',
  MSyn: 'סמן שיח (ויהי, והנה)',
  XPos: 'הקדמה',
  Reop: 'חזרה',
}

const FUNCTIONS_EN: Record<string, string> = {
  Pred: 'predicate', Subj: 'subject', Objc: 'object', Cmpl: 'complement', PreC: 'predicate noun',
  Adju: 'adjunct', Time: 'time', Loca: 'place', Conj: 'conjunction', Rela: 'relative', Nega: 'negation',
  Ques: 'question', Modi: 'modifier', Intj: 'interjection', Voct: 'address', Frnt: 'fronted',
  PreO: 'predicate + object', PreS: 'predicate + subject', PtcO: 'participle + object',
  NCop: 'אין', NCoS: 'אין + subject', Exst: 'יש', ExsS: 'יש + subject', IntS: 'interjection + subject',
  ModS: 'modifier + subject', PrAd: 'predicative adjunct', PrcS: 'predicate noun + subject',
  EPPr: 'enclitic pronoun', Supp: 'supplement',
}  // prettier-ignore
const FUNCTIONS_HE: Record<string, string> = {
  Pred: 'נשוא', Subj: 'נושא', Objc: 'מושא', Cmpl: 'משלים', PreC: 'נשוא שמני', Adju: 'תיאור',
  Time: 'זמן', Loca: 'מקום', Conj: 'חיבור', Rela: 'זיקה', Nega: 'שלילה', Ques: 'שאלה', Modi: 'מגביל',
  Intj: 'קריאה', Voct: 'פנייה', Frnt: 'מוקדם', PreO: 'נשוא + מושא', PreS: 'נשוא + נושא',
  PtcO: 'בינוני + מושא', NCop: 'אין', NCoS: 'אין + נושא', Exst: 'יש', ExsS: 'יש + נושא',
  IntS: 'קריאה + נושא', ModS: 'מגביל + נושא', PrAd: 'תיאור מצב', PrcS: 'נשוא שמני + נושא',
  EPPr: 'כינוי מצורף', Supp: 'תוספת',
}  // prettier-ignore

type Source = 'explicit' | 'carried' | 'enclosing'

export const synEn = {
  clauseType: (code: string) =>
    CLAUSES_EN[code] ??
    verbal(
      code,
      { way: 'wayyiqtol', qatal: 'qatal', yiqtol: 'yiqtol', imv: 'imperative' },
      {
        w: (f) => (f === 'wayyiqtol' ? f : `ו + ${f}`),
        wx: (f) => `ו + … + ${f}`,
        wX: (f) => `ו + subject + ${f}`,
        x: (f) => `… + ${f}`,
        X: (f) => `subject + ${f}`,
        z: (f) => `${f} first`,
      },
      ', subject after',
    ) ??
    code,
  fn: (code: string) => FUNCTIONS_EN[code] ?? code,
  textTypes: { N: 'narration', Q: 'direct speech', D: 'discourse' } as Record<string, string>,
  panel: 'Clauses and speakers',
  panelLede:
    'The ETCBC syntax database (BHSA): each clause with its type and the function of each phrase; direct speech with who speaks it, found from the clause that introduces it.',
  speaker: (s: Source, he: string) =>
    s === 'explicit' ? `spoken by ${he}` : s === 'carried' ? `spoken by ${he} (inferred)` : `within the speech of ${he}`,
  speakerTitle: {
    explicit: 'The introduction names the speaker (right 29 of 31 times in a hand check)',
    carried: 'The introduction has no subject; the subject of a clause just before it (right 13 of 19 times)',
    enclosing: 'A quotation without its own speaker, inside this one (words to be passed on, a quotation within a quotation)',
  } as Record<Source, string>,
  noSpeaker: 'speaker not found',
  sameShape: 'Built the same way',
  sameShapeLede: 'Verses with the same clause types and phrase functions in the same order, whatever their words (BM25 over clause shapes).',
  noData: 'No syntax data in this build (run `bsim syntax`).',
  // the Speech page
  title: 'Who speaks',
  lede: 'How much of each book is narration, direct speech or discourse, and who speaks: the share of words in each, from the BHSA clause types, with the speaker of each quotation taken from the clause that introduces it (ויאמר משה, כה אמר יהוה, לאמר).',
  caveat: (explicit: number, carried: number, enclosing: number, unknown: number) =>
    `Quotation clauses: speaker named in the introduction ${numEn(explicit)}, inferred from the clause before ${numEn(carried)}, inside an enclosing quotation ${numEn(enclosing)}, not found ${numEn(unknown)} (poetry and prophecy rarely say who speaks). A hand check of 50 quotations: 42 right (named 29 / 31, inferred 13 / 19). Deuteronomy is Moses' speech without an introducing clause, so it shows as unattributed.`,
  legend: {
    narration: 'narration',
    divine: 'God speaks',
    other: 'others speak',
    unattributed: 'speech, speaker not found',
    discourse: 'discourse',
  },
  books: 'Books',
  chapters: (book: string) => `Chapters of ${book}`,
  speakers: 'Speakers',
  speakersOf: (book: string) => `Who speaks in ${book}`,
  words: (n: number) => `${numEn(n)} words`,
  explicitShare: (n: number, of: number) => `named in the introduction for ${numEn(n)} of ${numEn(of)} words`,
  share: (label: string, pct: number) => `${label} ${pct}%`,
  chapter: 'Chapter',
}

export const synHe: typeof synEn = {
  clauseType: (code: string) =>
    CLAUSES_HE[code] ??
    verbal(
      code,
      { way: 'ויקטל', qatal: 'קטל', yiqtol: 'יקטל', imv: 'ציווי' },
      {
        w: (f) => (f === 'ויקטל' ? f : `ו + ${f}`),
        wx: (f) => `ו + … + ${f}`,
        wX: (f) => `ו + נושא + ${f}`,
        x: (f) => `… + ${f}`,
        X: (f) => `נושא + ${f}`,
        z: (f) => `${f} בראש`,
      },
      ', נושא אחריו',
    ) ??
    code,
  fn: (code: string) => FUNCTIONS_HE[code] ?? code,
  textTypes: { N: 'סיפור', Q: 'דיבור ישיר', D: 'שיח' },
  panel: 'פסוקיות ודוברים',
  panelLede:
    'מאגר התחביר של ETCBC ‏(BHSA): כל פסוקית עם סוגה ותפקיד כל צירוף; דיבור ישיר עם הדובר, שנמצא מן הפסוקית שמציגה אותו.',
  speaker: (s: Source, he: string) =>
    s === 'explicit' ? `אומר: ${he}` : s === 'carried' ? `אומר: ${he} (משוער)` : `בתוך דבריו של ${he}`,
  speakerTitle: {
    explicit: 'הפסוקית המציגה נוקבת בשם הדובר (נכון ב־29 מתוך 31 בבדיקה ידנית)',
    carried: 'לפסוקית המציגה אין נושא; נלקח נושא פסוקית שלפניה (נכון ב־13 מתוך 19)',
    enclosing: 'ציטוט בלי דובר משלו, בתוך הציטוט הזה (דברים להעביר, ציטוט בתוך ציטוט)',
  },
  noSpeaker: 'הדובר לא נמצא',
  sameShape: 'בנוי באותה דרך',
  sameShapeLede: 'פסוקים שבהם אותם סוגי פסוקיות ואותם תפקידי צירופים באותו סדר, בלי קשר למילים (BM25 על מבנה הפסוקיות).',
  noData: 'אין נתוני תחביר בבנייה זו (הריצו `bsim syntax`).',
  title: 'מי מדבר',
  lede: 'כמה מכל ספר הוא סיפור, דיבור ישיר או שיח, ומי מדבר: חלק המילים בכל אחד, לפי סוגי הפסוקיות של BHSA, והדובר של כל ציטוט לפי הפסוקית שמציגה אותו (ויאמר משה, כה אמר יהוה, לאמר).',
  caveat: (explicit: number, carried: number, enclosing: number, unknown: number) =>
    `פסוקיות ציטוט: הדובר נקוב בפסוקית המציגה ${numHe(explicit)}, משוער מן הפסוקית שלפניה ${numHe(carried)}, בתוך ציטוט עוטף ${numHe(enclosing)}, לא נמצא ${numHe(unknown)} (שירה ונבואה מרבות שלא לומר מי מדבר). בדיקה ידנית של 50 ציטוטים: 42 נכונים (נקוב 29 / 31, משוער 13 / 19). ספר דברים הוא נאום משה בלי פסוקית מציגה, ולכן מופיע כלא משויך.`,
  legend: {
    narration: 'סיפור',
    divine: 'האל מדבר',
    other: 'אחרים מדברים',
    unattributed: 'דיבור, הדובר לא נמצא',
    discourse: 'שיח',
  },
  books: 'ספרים',
  chapters: (book: string) => `פרקי ${book}`,
  speakers: 'דוברים',
  speakersOf: (book: string) => `מי מדבר ב${book}`,
  words: (n: number) => `${numHe(n)} מילים`,
  explicitShare: (n: number, of: number) => `נקוב בפסוקית המציגה ב־${numHe(n)} מתוך ${numHe(of)} מילים`,
  share: (label: string, pct: number) => `${label} ${pct}%`,
  chapter: 'פרק',
}
