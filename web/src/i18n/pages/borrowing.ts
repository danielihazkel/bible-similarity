// Interface strings of "who borrowed" (DESIGN.md §16.27): the page and the line on parallel
// sequences and Compare. English first, Hebrew typed against it.

import { numEn, numHe } from '../fmt'

type Sign = 'language' | 'spelling' | 'smoothing' | 'expansion'

export const borEn = {
  title: 'Who borrowed',
  lede: 'For passages that run parallel in two books, which side looks like the later text and so the borrower. Four signs, fixed before any result was seen, compare the two sides; the ones that pass the check below vote.',
  caveat:
    'A later-looking text is evidence, not proof: both may draw on a common source, and copyists updated spelling and grammar. Every direction scholars accept runs from a book earlier in the canon to a later one, so this check cannot tell the signs from canon order (they never see it).',
  signs: {
    language: 'Language',
    spelling: 'Spelling',
    smoothing: 'Smoothing',
    expansion: 'Expansion',
  } as Record<Sign, string>,
  signHints: {
    language: 'Late Biblical Hebrew features of each side (late words, אני for אנכי, fewer infinitive absolutes …)',
    spelling: 'Which side writes ו and י more fully where the words are the same',
    smoothing: 'Where a word was replaced, whether the rarer word was replaced by a commoner one',
    expansion: 'Whether one side adds more words than it leaves out',
  } as Record<Sign, string>,
  allSigns: 'All four, voting',
  checkTitle: 'Check: parallels whose direction is accepted',
  checkLede: (n: number) =>
    `${numEn(n)} parallels between books whose direction most scholars accept: Samuel–Kings → Chronicles, Genesis and Joshua → 1 Chronicles, Psalms → 1 Chronicles 16, 2 Kings → Jeremiah 52, Exodus → Deuteronomy.`,
  right: (a: number, n: number, p: string) => `${numEn(a)} of ${numEn(n)} right (sign test p = ${p})`,
  votes: 'votes',
  noVote: 'shown, does not vote',
  heldOut: (a: number, n: number, u: number) =>
    `The voting signs chosen without each book pair and tested on it: ${numEn(a)} of ${numEn(n)} right, ${numEn(u)} undecided.`,
  pairs: 'Book pairs',
  flow: (src: string, dst: string) => `${src} → ${dst}`,
  unclear: 'unclear',
  accepted: 'accepted direction',
  counts: (n: number, ab: number, ba: number) =>
    `${numEn(n)} ${n === 1 ? 'parallel' : 'parallels'}: ${numEn(ab)} point one way, ${numEn(ba)} the other`,
  later: (side: string) => `${side} later`,
  parallel: 'Parallel',
  direction: 'Direction',
  noData: 'No direction estimates in this build (run `bsim borrowing`).',
  line: (src: string, dst: string, votes: number) =>
    `Which borrowed? ${src} → ${dst} (${numEn(votes)} ${votes === 1 ? 'sign' : 'signs'}; the later-looking side drew on the other)`,
  lineUnclear: (a: string, b: string) => `Which borrowed? ${a} ↔ ${b}: the signs disagree or are silent`,
}

export const borHe: typeof borEn = {
  title: 'מי שאל ממי',
  lede: 'בקטעים מקבילים בשני ספרים: איזה צד נראה מאוחר, ולכן השואל. ארבעה סימנים, שנקבעו לפני שנראתה תוצאה כלשהי, משווים בין שני הצדדים; אלה שעוברים את הבדיקה שלמטה מצביעים.',
  caveat:
    'טקסט שנראה מאוחר הוא ראיה ולא הוכחה: שניהם עשויים לשאוב ממקור משותף, ומעתיקים עדכנו כתיב ודקדוק. כל כיוון שהחוקרים מקבלים הולך מספר מוקדם בסדר הכתובים לספר מאוחר בו, ולכן הבדיקה אינה מבחינה בין הסימנים לבין סדר הספרים (הם אינם רואים אותו).',
  signs: { language: 'לשון', spelling: 'כתיב', smoothing: 'החלקה', expansion: 'הרחבה' },
  signHints: {
    language: 'סימני עברית מקראית מאוחרת בכל צד (מילים מאוחרות, אני במקום אנכי, פחות מקורות מוחלטים …)',
    spelling: 'איזה צד כותב ו ו־י בכתיב מלא יותר במילים הזהות',
    smoothing: 'במקום שמילה הוחלפה: האם מילה נדירה הוחלפה במילה שכיחה',
    expansion: 'האם צד אחד מוסיף יותר מילים משהוא משמיט',
  },
  allSigns: 'כל הארבעה, בהצבעה',
  checkTitle: 'בדיקה: מקבילות שכיוונן מקובל',
  checkLede: (n: number) =>
    `${numHe(n)} מקבילות בין ספרים שרוב החוקרים מקבלים את כיוון השאילה ביניהם: שמואל–מלכים ← דברי הימים, בראשית ויהושע ← דברי הימים א, תהלים ← דברי הימים א טז, מלכים ב ← ירמיהו נב, שמות ← דברים.`,
  right: (a: number, n: number, p: string) => `${numHe(a)} מתוך ${numHe(n)} נכונים (מבחן סימנים p = ${p})`,
  votes: 'מצביע',
  noVote: 'מוצג, אינו מצביע',
  heldOut: (a: number, n: number, u: number) =>
    `הסימנים המצביעים נבחרו בלי כל זוג ספרים ונבדקו עליו: ${numHe(a)} מתוך ${numHe(n)} נכונים, ${numHe(u)} לא הוכרעו.`,
  pairs: 'זוגות ספרים',
  flow: (src: string, dst: string) => `${src} ← ${dst}`,
  unclear: 'לא ברור',
  accepted: 'כיוון מקובל',
  counts: (n: number, ab: number, ba: number) =>
    `${numHe(n)} מקבילות: ${numHe(ab)} מצביעות לכיוון אחד, ${numHe(ba)} לאחר`,
  later: (side: string) => `${side} מאוחר`,
  parallel: 'מקבילה',
  direction: 'כיוון',
  noData: 'אין הערכות כיוון בבנייה זו (הריצו `bsim borrowing`).',
  line: (src: string, dst: string, votes: number) =>
    `מי שאל ממי? ${src} ← ${dst} (${numHe(votes)} סימנים; הצד שנראה מאוחר שאב מן האחר)`,
  lineUnclear: (a: string, b: string) => `מי שאל ממי? ${a} ↔ ${b}: הסימנים חלוקים או שותקים`,
}
