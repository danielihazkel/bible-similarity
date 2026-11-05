// The Hebrew half of `../syntax.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { CLAUSES_HE, FUNCTIONS_HE, synEn, verbal } from '../syntax'
import type { Source, ToSource } from '../syntax'

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
    'מאגר התחביר של ETCBC ‏(BHSA): כל פסוקית עם סוג הפסוקית ותפקיד כל צירוף; דיבור ישיר עם הדובר, שנמצא מן הפסוקית שמציגה אותו.',
  speaker: (s: Source, he: string) =>
    s === 'explicit' || s === 'formula'
      ? `אומר: ${he}`
      : s === 'carried' || s === 'framed'
        ? `אומר: ${he} (משוער)`
        : `בתוך דבריו של ${he}`,
  speakerTitle: {
    explicit: 'הפסוקית המציגה נוקבת בשם הדובר (נכון ב־29 מתוך 31 בבדיקה ידנית)',
    carried: 'לפסוקית המציגה אין נושא; נלקח נושא פסוקית שלפניה (נכון ב־13 מתוך 19)',
    enclosing: 'ציטוט בלי דובר משלו, בתוך הציטוט הזה (דברים להעביר, ציטוט בתוך ציטוט)',
    formula: 'בפרשה נאמר "נאם יהוה" ואין בה דובר אחר (נכון ב־4 מתוך 5 בבדיקה ידנית)',
    framed: 'ספר דברים: "הדברים אשר דבר משה" (א, א), כשדבר אחר אינו נוקב בדובר',
  },
  noSpeaker: 'הדובר לא נמצא',
  addressee: (s: ToSource, he: string) => (s === 'explicit' || s === 'vocative' ? `אל ${he}` : `אל ${he} (משוער)`),
  addresseeTitle: {
    explicit: 'הפסוקית המציגה נוקבת במי שאליו נאמרים הדברים (ויאמר … אל משה): נכון ב־21 מתוך 21 בבדיקה ידנית',
    vocative: 'הציטוט קורא לו בשמו: נכון ב־11 מתוך 11',
    pronoun: '„אליו” בפסוקית המציגה, מתפרש כצד השני של השיחה: נכון ב־4 מתוך 9',
    turn: 'הנמען לא נאמר: מתפרש כתשובה למי שדיבר לפני כן (נכון ב־6 מתוך 9)',
  },
  toWord: 'אל',
  sameShape: 'בנוי באותה דרך',
  sameShapeLede: 'פסוקים שבהם אותם סוגי פסוקיות ואותם תפקידי צירופים באותו סדר, בלי קשר למילים (BM25 על מבנה הפסוקיות).',
  noData: 'אין נתוני תחביר בבנייה זו (הריצו `bsim syntax`).',
  title: 'מי מדבר',
  lede: 'כמה מכל ספר הוא סיפור, דיבור ישיר או שיח, ומי מדבר: חלק המילים בכל אחד, לפי סוגי הפסוקיות של BHSA, והדובר של כל ציטוט לפי הפסוקית שמציגה אותו (ויאמר משה, כה אמר יהוה, לאמר).',
  caveat: (explicit: number, carried: number, enclosing: number, formula: number, framed: number, unknown: number) =>
    `פסוקיות ציטוט: הדובר נקוב בפסוקית המציגה ${numHe(explicit)}, משוער מן הפסוקית שלפניה ${numHe(carried)}, האל לפי „נאם יהוה” בפרשה ${numHe(formula)}, משה במסגרת ספר דברים ${numHe(framed)}, בתוך ציטוט עוטף ${numHe(enclosing)}, לא נמצא ${numHe(unknown)} (שירה וחכמה מרבות שלא לומר מי מדבר). בדיקה ידנית של 50 ציטוטים: 42 נכונים (נקוב 29 / 31, משוער 13 / 19); מתוך 50 שהכללים המתוקנים שינו, 37 מתוך 45 שקיבלו דובר נכונים.`,
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
  tabs: { books: 'ספרים', voices: 'קולות', dialogue: 'אל מי' },
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
    cols: { speaker: 'דובר', book: 'ספר עיקרי', words: 'מילים', delta: 'Delta', effect: 'ייחודיות', q: 'q' },
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
    matrixLede: 'Delta של Burrows בין הדוברים, המספר והדיבור הלא משויך; כהה יותר = דומה יותר. בלי תיקון לגודל או לספר: לתיאור בלבד.',
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
