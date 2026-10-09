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
  // the Voices tab (DESIGN.md §16.28)
  tabs: { books: 'Books', voices: 'Voices' } as Record<'books' | 'voices', string>,
  view: 'View',
  voices: {
    lede: "Does a speaker have a style of their own? Each person's direct speech is profiled with the features of the Style page (the most frequent words, verb forms, grammar) and compared with the other attributed speech of the same books, so book and genre are held fixed. A speaker is distinct when the distance (Burrows' Delta) is larger than when the speaker labels are shuffled among the quotations of each book.",
    summary: (n: number, sig: number) => `${numEn(n)} speakers profiled; ${numEn(sig)} distinct beyond chance (q ≤ 0.05).`,
    calibration: (cal: number, of: number) => `Check of the test: one shuffled labelling scored the same way passes ${numEn(cal)} of ${numEn(of)}.`,
    rho: (r: string, n: number) => `With only the quotations whose introduction names the speaker (${numEn(n)} speakers), the ranking agrees at ρ ${r}.`,
    reliability: 'Speakers inferred from an earlier clause are right about two times in three; Job, his friends, Elihu and Daniel are almost all inferred.',
    noData: 'No speaker voices in this build (run `bsim voices`).',
    divine: 'God (יהוה, אלהים, אדני)',
    narrator: 'narrator',
    unattributed: 'speech, speaker not found',
    speakers: 'Speakers, most distinct first',
    cols: { speaker: 'Speaker', book: 'Mostly in', words: 'Words', delta: 'Delta', effect: 'Distinctiveness', q: 'q' },
    effectTitle: 'Delta above its shuffled expectation, in standard deviations of the shuffles',
    explicit: (n: number, of: number) => `${numEn(n)} of ${numEn(of)} words named in the introduction`,
    deltaTitle: (d: string, n: string) => `Delta ${d} (shuffled labels: ${n} on average)`,
    checks: 'Checks named in advance',
    author: (who: string, a: string, b: string) => `${who} in ${a} and in ${b}`,
    verdicts: {
      author: "each portrayal sounds like its own book's narrator: the author's voice over the character's",
      differs: 'the two portrayals differ, but not towards their narrators',
      same: 'no difference between the two portrayals beyond chance',
      underpowered: 'too few words on one side to tell',
    } as Record<string, string>,
    authorNums: (cross: string, pc: string, dab: string, pab: string, wa: number, wb: number) =>
      `towards the narrators ${cross} (p ${pc}); between the portrayals ${dab} (p ${pab}); ${numEn(wa)} / ${numEn(wb)} words`,
    distinct: (who: string, book: string, rank: number | null, of: number) =>
      rank === null
        ? `${book}: ${who} is not among the profiled speakers`
        : `${book}: ${who} is number ${rank} of ${numEn(of)} speakers by distinctiveness (expected: number 1)`,
    matrix: 'Distance between voices',
    matrixLede: "Burrows' Delta between the speakers, the narrator and unattributed speech; darker = more alike. Not adjusted for size or book: descriptive only.",
    pair: (a: string, b: string, d: string) => `${a} – ${b}: Delta ${d}`,
    profile: (who: string) => `What stands out in the speech of ${who}`,
    more: 'Uses more than the others in the same books',
    less: 'Uses less',
    nearest: 'Closest voices:',
    chapters: 'Where they speak most',
    clauses: (n: number) => `${numEn(n)} clauses`,
    select: 'Choose a speaker in the table to see their profile.',
  },
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
  tabs: { books: 'ספרים', voices: 'קולות' },
  view: 'תצוגה',
  voices: {
    lede: 'האם לדובר יש סגנון משלו? הדיבור הישיר של כל דמות מתואר בתכונות של עמוד הסגנון (המילים השכיחות, צורות הפועל, הדקדוק) ומושווה לשאר הדיבור המשויך באותם ספרים, כך שהספר והסוגה קבועים. דובר נחשב ייחודי כשהמרחק (Delta של Burrows) גדול מזה שמתקבל כשמערבבים את שמות הדוברים בין הציטוטים של כל ספר.',
    summary: (n: number, sig: number) => `${numHe(n)} דוברים נבדקו; ${numHe(sig)} ייחודיים מעבר למקרה (q ≤ 0.05).`,
    calibration: (cal: number, of: number) => `בדיקת המבחן: שיוך מעורבב אחד שנבדק באותה דרך עובר ב־${numHe(cal)} מתוך ${numHe(of)}.`,
    rho: (r: string, n: number) => `רק עם הציטוטים שבהם הפסוקית המציגה נוקבת בשם הדובר (${numHe(n)} דוברים) הדירוג מתאים ב־ρ ${r}.`,
    reliability: 'דוברים שהוסקו מפסוקית קודמת נכונים בערך פעמיים מתוך שלוש; איוב, רעיו, אליהוא ודניאל כמעט כולם משוערים.',
    noData: 'אין קולות דוברים בבנייה זו (הריצו `bsim voices`).',
    divine: 'האל (יהוה, אלהים, אדני)',
    narrator: 'המספר',
    unattributed: 'דיבור, הדובר לא נמצא',
    speakers: 'דוברים, הייחודי ביותר ראשון',
    cols: { speaker: 'דובר', book: 'בעיקר ב', words: 'מילים', delta: 'Delta', effect: 'ייחודיות', q: 'q' },
    effectTitle: 'ה־Delta מעל הצפוי בערבוב, ביחידות של סטיית התקן של הערבובים',
    explicit: (n: number, of: number) => `${numHe(n)} מתוך ${numHe(of)} מילים עם דובר נקוב`,
    deltaTitle: (d: string, n: string) => `Delta ${d} (בערבוב: ${n} בממוצע)`,
    checks: 'בדיקות שנקבעו מראש',
    author: (who: string, a: string, b: string) => `${who} ב${a} וב${b}`,
    verdicts: {
      author: 'כל תיאור נשמע כמו המספר של ספרו: קול המחבר גובר על קול הדמות',
      differs: 'שני התיאורים שונים, אבל לא בכיוון המספרים שלהם',
      same: 'אין הבדל בין שני התיאורים מעבר למקרה',
      underpowered: 'מעט מדי מילים באחד הצדדים כדי לקבוע',
    },
    authorNums: (cross: string, pc: string, dab: string, pab: string, wa: number, wb: number) =>
      `לכיוון המספרים ${cross} (p ${pc}); בין התיאורים ${dab} (p ${pab}); ${numHe(wa)} / ${numHe(wb)} מילים`,
    distinct: (who: string, book: string, rank: number | null, of: number) =>
      rank === null
        ? `${book}: ${who} אינו בין הדוברים שנבדקו`
        : `${book}: ${who} במקום ${numHe(rank)} מתוך ${numHe(of)} דוברים בייחודיות (הצפי: מקום 1)`,
    matrix: 'המרחק בין הקולות',
    matrixLede: 'Delta של Burrows בין הדוברים, המספר והדיבור הלא משויך; כהה יותר = דומה יותר. בלי תיקון לגודל או לספר: תיאורי בלבד.',
    pair: (a: string, b: string, d: string) => `${a} – ${b}: Delta ${d}`,
    profile: (who: string) => `מה בולט בדיבורו של ${who}`,
    more: 'משתמש יותר מאחרים באותם ספרים',
    less: 'משתמש פחות',
    nearest: 'הקולות הקרובים:',
    chapters: 'היכן מדבר הכי הרבה',
    clauses: (n: number) => `${numHe(n)} פסוקיות`,
    select: 'בחרו דובר בטבלה כדי לראות את הפרופיל שלו.',
  },
}
