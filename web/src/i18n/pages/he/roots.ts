// The Hebrew half of `../roots.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, rootEn } from '../roots'

export const rootHe: typeof rootEn = {
  title: 'שורשים',
  lede: 'שורש עברי (ב־ר־ך) נותן פועל (לברך), שמות (ברכה) ועוד. הקונקורדנציה סופרת מילים; כאן הן נאספות לשורשיהן, לפי הגזירות של מילון סטרונג, ורק כשהמילה מחזיקה את אותיות השורש בתבנית עברית (ניחושים כמו בית „מן” בנה נשארים בחוץ).',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim roots` ואחר כך `bsim build-db`.',
  views: { pairs: 'זו לצד זו', key: 'שורשים מנחים' },
  families: (families: number, lemmas: number) => `${numHe(families)} משפחות שורש אוספות ${numHe(lemmas)} מילים.`,
  pairsTitle: 'שתי מילים מאותו שורש זו לצד זו',
  cognate: (obs: number, exp: number, ratio: number, p: number, window: number, shuffles: number) =>
    `פועל עם שם מאותו שורש במרחק של עד ${numHe(window)} מילים (מושא פנימי: ויחלם חלום, זבחו זבח): ${numHe(obs)} פעמים, לעומת ${exp.toFixed(0)} כשמילות התוכן של כל פרק מעורבבות (פי ${ratio.toFixed(1)}, p ${fp(p)} על פני ${numHe(shuffles)} ערבובים). הצירוף נבחר, ואינו מקרה.`,
  other: (obs: number, exp: number, p: number) =>
    `מילים אחרות מאותו שורש זו לצד זו (שני שמות, שם ותואר): ${numHe(obs)} לעומת ${exp.toFixed(0)} (p ${fp(p)}) — רבות מהן צירופי מספר (בשנה השנית).`,
  infAbs: (n: number) =>
    `מקור מוחלט עם הפועל שלו (מות יומת): ${numHe(n)} פעמים; מבנה דקדוקי, נספר אך לא נבחן.`,
  kinds: { cognate: 'פועל ושם', other: 'אחר', inf_abs: 'מקור מוחלט' },
  kind: 'סוג',
  anyKind: 'כל הסוגים',
  booksTitle: 'פועל ושם מאותו שורש, לפי ספר',
  booksCols: { book: 'ספר', pairs: 'זוגות', expected: 'במקרה', ratio: 'יחס', inf: 'מקור מוחלט', per: 'לכל 1,000 מילים' },
  pairsCount: (n: number) => countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות'),
  root: 'שורש',
  knownTitle: 'מילים מנחות שנקבעו מראש',
  known: (byRoot: number, byLemma: number, n: number, top: number, better: number) =>
    `בספירה לפי שורש, ${numHe(byRoot)} מתוך ${numHe(n)} מילים מנחות שהמחקר מונה נמצאות בין ${numHe(top)} המובילות בפרקן; בספירה לפי מילה, ${numHe(byLemma)}. השורש מדורג גבוה יותר ב־${numHe(better)}. רוב המילים המנחות הנודעות נישאות במילה אחת (שוב ברות, שלח בשמואל ב יא), ואיסוף מילות השורש מעלה גם את ספירתו בשאר המקרא.`,
  knownCols: { chapter: 'פרק', root: 'שורש', byLemma: 'מקום לפי מילה', byRoot: 'מקום לפי שורש' },
  hiddenTitle: 'שורשים מנחים שנראים רק לפי שורש',
  hiddenLede: (n: number, top: number) =>
    `${countHe(n, 'מילה מנחה אחת', 'שתי מילים מנחות', 'מילים מנחות')} של פרקים, בין ${numHe(top)} המובילות לפי שורש, שאוספות שתי מילים או יותר של הפרק ואף אחת מהן אינה בין המובילות לפי מילה: הפועל ושמותיו יחד (טמא וטהור בויקרא יג, זרע בבראשית א). כיווני חקירה, החזקים תחילה.`,
  hiddenCols: { chapter: 'פרק', root: 'שורש', words: 'מילותיו כאן', count: 'פעמים', rank: 'מקום לפי שורש', lemmaRank: 'המילה הטובה ביותר' },
  familyTitle: (root: string) => `השורש ${root}`,
  familyLede: (n: number, verses: number) => `${countHe(n, 'מילה אחת', 'שתי מילים', 'מילים')} מן השורש הזה, ב־${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}. לחיצה על מילה פותחת את הקונקורדנציה שלה.`,
  link: (l: string) => `(${l})`,
  verses: (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
  inBook: (book: string) => ` ב${book}`,
  allBooks: 'כל הספרים',
  rootChip: (root: string) => `שורש ${root}`,
  rootChipTitle: 'כל המילים מן השורש הזה',
  rootLeitworte: 'לפי שורש',
  rootLeitworteLede: 'שורשים שמילותיהם יחד שכיחות כאן יותר מן הצפוי; ✦ = אף מילה של השורש אינה מילה מנחה בפני עצמה.',
  rootLeitwortTitle: (count: number, expected: string, g2: string, words: string) => `${count} פעמים (צפוי ${expected}), G² ${g2}: ${words}`,
  hiddenMark: '✦',
}
