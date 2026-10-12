// Interface strings of Patterns → Roots and the root family page: words of one root side by side,
// Leitworte counted by root (DESIGN.md §16.38). English first, Hebrew typed against it.

import type { RootPairKind } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const rootEn = {
  title: 'Roots',
  lede: 'A Hebrew root (ב־ר־ך) gives a verb (to bless), nouns (a blessing) and more. The concordance counts words; here they are gathered into their roots, from the derivations of Strong\'s dictionary, kept only when a word holds its root\'s letters in a Hebrew shape (Strong\'s guesses such as בית "from" בנה are left out).',
  noData: 'Not computed in this build: run `bsim roots`, then `bsim build-db`.',
  views: { pairs: 'Side by side', key: 'Key roots' },
  families: (families: number, lemmas: number) => `${numEn(families)} root families gather ${numEn(lemmas)} words.`,
  // side by side
  pairsTitle: 'Two words of one root side by side',
  cognate: (obs: number, exp: number, ratio: number, p: number, window: number, shuffles: number) =>
    `A verb with a noun of its own root within ${numEn(window)} words (ויחלם חלום, “he dreamt a dream”; זבחו זבח): ${numEn(obs)} times, against ${exp.toFixed(0)} with the content words of each chapter shuffled (${ratio.toFixed(1)}×, p ${fp(p)} over ${numEn(shuffles)} shuffles). The figure is chosen, not chance.`,
  other: (obs: number, exp: number, p: number) =>
    `Other words of one root side by side (two nouns, a noun and an adjective): ${numEn(obs)} against ${exp.toFixed(0)} (p ${fp(p)}) — many are number phrases (בשנה השנית).`,
  infAbs: (n: number) =>
    `An infinitive absolute with its own verb (מות יומת, “he shall surely die”): ${numEn(n)} times; a construction of the grammar, counted but not tested.`,
  kinds: { cognate: 'Verb and noun', other: 'Other', inf_abs: 'Infinitive absolute' } satisfies Record<RootPairKind, string>,
  kind: 'Kind',
  anyKind: 'All kinds',
  booksTitle: 'Verb and noun of one root, by book',
  booksCols: { book: 'Book', pairs: 'Pairs', expected: 'By chance', ratio: 'Ratio', inf: 'Infinitive absolute', per: 'per 1,000 words' },
  pairsCount: (n: number) => countEn(n, 'pair', 'pairs'),
  root: 'root',
  // key roots
  knownTitle: 'Leitworte named in advance',
  known: (byRoot: number, byLemma: number, n: number, top: number, better: number) =>
    `Counted by root, ${numEn(byRoot)} of ${numEn(n)} Leitworte that scholars name are among their chapter's top ${numEn(top)}; counted by word, ${numEn(byLemma)}. The root ranks higher for ${numEn(better)}. Most famous Leitworte are carried by one word (שוב in Ruth, שלח in 2 Samuel 11), and gathering a root's words also raises its count in the rest of the Bible.`,
  knownCols: { chapter: 'Chapter', root: 'Root', byLemma: 'Rank by word', byRoot: 'Rank by root' },
  hiddenTitle: 'Key roots that only show by root',
  hiddenLede: (n: number, top: number) =>
    `${countEn(n, 'chapter Leitwort', 'chapter Leitworte')} among the top ${numEn(top)} by root that gather two or more words of the chapter, none of which is in the top by word: the verb and its nouns together (טמא and טהור in Leviticus 13, זרע “sow” and “seed” in Genesis 1). Leads to read, strongest first.`,
  hiddenCols: { chapter: 'Chapter', root: 'Root', words: 'Its words here', count: 'Times', rank: 'Rank by root', lemmaRank: 'Best word' },
  // the family page
  familyTitle: (root: string) => `The root ${root}`,
  familyLede: (n: number, verses: number) => `${countEn(n, 'word', 'words')} of this root, in ${countEn(verses, 'verse', 'verses')}. Click a word for its own concordance.`,
  link: (l: string) => `(${l})`,
  verses: (n: number) => countEn(n, 'verse', 'verses'),
  inBook: (book: string) => ` in ${book}`,
  allBooks: 'All books',
  rootChip: (root: string) => `root ${root}`,
  rootChipTitle: 'Every word of this root',
  // structure panel
  rootLeitworte: 'By root',
  rootLeitworteLede: 'Roots whose words together are over-represented here; ✦ = no word of the root is a Leitwort by itself.',
  rootLeitwortTitle: (count: number, expected: string, g2: string, words: string) => `${count} times (${expected} expected), G² ${g2}: ${words}`,
  hiddenMark: '✦',
}

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
    `מקור מוחלט עם הפועל שלו (מות יומת): ${numHe(n)} פעמים; מבנה של הדקדוק, נספר אך לא נבחן.`,
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
  hiddenCols: { chapter: 'פרק', root: 'שורש', words: 'מילותיו כאן', count: 'פעמים', rank: 'מקום לפי שורש', lemmaRank: 'המילה הטובה' },
  familyTitle: (root: string) => `השורש ${root}`,
  familyLede: (n: number, verses: number) => `${countHe(n, 'מילה אחת', 'שתי מילים', 'מילים')} מן השורש הזה, ב־${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}. לחיצה על מילה פותחת את הקונקורדנציה שלה.`,
  link: (l: string) => `(${l})`,
  verses: (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
  inBook: (book: string) => ` ב${book}`,
  allBooks: 'כל הספרים',
  rootChip: (root: string) => `שורש ${root}`,
  rootChipTitle: 'כל המילים מן השורש הזה',
  rootLeitworte: 'לפי שורש',
  rootLeitworteLede: 'שורשים שמילותיהם יחד שכיחות כאן מן הצפוי; ✦ = אף מילה של השורש אינה מילה מנחה בפני עצמה.',
  rootLeitwortTitle: (count: number, expected: string, g2: string, words: string) => `${count} פעמים (צפוי ${expected}), G² ${g2}: ${words}`,
  hiddenMark: '✦',
}
