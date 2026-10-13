// Interface strings of Patterns → Psalms: the form of each psalm against Gunkel's genres, and the
// turn of the lament (DESIGN.md §16.42). English first, Hebrew typed against it.

import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))
const x3 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(3))
const per100 = (x: number | null | undefined) => (x == null ? '–' : (x * 100).toFixed(1))

export const psaEn = {
  title: 'Psalms',
  lede: 'Form criticism sorts the psalms by their form: a hymn calls a group to praise and speaks of God; a lament speaks to God in the first person, in distress, and often turns to praise before its end — "the certainty of being heard" (Ps 6:9, 13:6, 22:23). Here the form is counted from the words of each psalm, its superscription left out: persons, imperatives, questions (from the morphology) and the words of distress and of praise (from the SDBH domains). Does the counted form recover the genres Gunkel named, and where do the laments turn?',
  noData: 'Not computed in this build: run `bsim psalms`, then `bsim build-db`.',
  genres: {
    hymn: 'Hymn',
    lament_individual: 'Individual lament',
    lament_communal: 'Communal lament',
    royal: 'Royal psalm',
    thanksgiving: 'Thanksgiving',
    trust: 'Song of trust',
    wisdom: 'Wisdom psalm',
  } as Record<string, string>,
  unlabelled: 'mixed or disputed',
  features: {
    first_singular: 'I / me',
    first_plural: 'we / us',
    second: 'you',
    imperative: 'imperatives',
    imperative_plural: 'plural imperatives',
    question: 'questions',
    distress: 'distress',
    praise: 'praise',
  } as Record<string, string>,
  per100: 'per 100 words',
  // the genre test
  genreTitle: 'Does the form recover the genres?',
  genreLede: (labelled: number, k: number, titleWords: number) =>
    `${numEn(labelled)} psalms carry one of Gunkel's genres (the core cases; a mixed or disputed psalm is left out). The eight counts, standardized, group all 150 psalms into ${numEn(k)} clusters (Ward), as many as genres, without seeing the genres; ${numEn(titleWords)} superscription words are left out.`,
  genreResult: (nmi: number, nul: number, p: number) =>
    `The clusters agree with the genres by normalized mutual information ${x3(nmi)}, against ${x3(nul)} with the genres shuffled among the psalms (p ${fp(p)}).`,
  robustGenres: (formOnly: number, formP: number, domainsOnly: number, domainsP: number, kept: number) =>
    `The form alone (persons, imperatives, questions) gives ${x3(formOnly)} (p ${fp(formP)}), the words of distress and praise alone ${x3(domainsOnly)} (p ${fp(domainsP)}); with the superscriptions kept, ${x3(kept)}.`,
  crosstabTitle: 'Genres by cluster',
  cluster: (c: number) => `Cluster ${c}`,
  clusterHead: 'Cluster',
  genreHead: 'Genre',
  profileTitle: 'What each cluster counts',
  // the checks
  checksTitle: 'The forms named in advance',
  checksLede: (held: number, n: number) =>
    `${numEn(held)} of ${numEn(n)} hold: each genre's mean against the other labelled psalms, with the genres shuffled (one-sided, Benjamini–Hochberg q).`,
  checkCols: { genre: 'Genre', feature: 'Count', expected: 'Expected', mean: 'Mean', rest: 'Others', q: 'q' },
  higher: 'higher',
  lower: 'lower',
  // the turn
  turnTitle: 'Where does the lament turn?',
  turnLede: (minSide: number) =>
    `Each verse's mood is its words of praise minus its words of distress. A psalm's turn is the split of its verses (at least ${numEn(minSide)} on each side) where the mood per word rises most from before to after; its p comes from the verse order shuffled within the psalm.`,
  knownLede: (found: number, n: number, expected: number, p: number, tol: number) =>
    `Turns scholars name: ${numEn(found)} of ${numEn(n)} found within ${countEn(tol, 'verse', 'verses')}, against ${expected.toFixed(1)} for a split drawn at random (p ${fp(p)}).`,
  robustTolerance: (rows: { tol: string; found: number; expected: number; p: number }[]) =>
    `Within ${rows.map((r) => `${r.tol}: ${numEn(r.found)} against ${r.expected.toFixed(1)} (p ${fp(r.p)})`).join('; ')} verses — the result rests on the tolerance.`,
  knownCols: { named: 'Named turn', found: 'Turn found', p: 'p', chance: 'Chance' },
  tooShort: 'too short',
  lvh: (laments: number, nLaments: number, hymns: number, nHymns: number, p: number) =>
    `Do laments turn more often than hymns? ${numEn(laments)} of ${numEn(nLaments)} individual laments have a turn above chance, against ${numEn(hymns)} of ${numEn(nHymns)} hymns (Fisher, p ${fp(p)}). Most single psalms are too short for a turn to stand out on its own.`,
  // the list
  listTitle: 'The psalms',
  allGenres: 'All genres',
  allClusters: 'All clusters',
  turnedOnly: 'Turn above chance only',
  sortLabel: 'Order',
  sorts: { chapter: 'In order', turn: 'Clearest turn first' } as Record<string, string>,
  count: (n: number) => countEn(n, 'psalm', 'psalms'),
  words: (n: number) => countEn(n, 'word', 'words'),
  turnAt: (label: string, p: number, before: number, after: number) =>
    `turns at ${label} (p ${fp(p)}; mood ${x2(before)} → ${x2(after)} per word)`,
  noTurn: 'too short to turn',
  read: 'Read with its mood',
  readTitle: 'The psalm in the layered reader, words of distress and praise marked',
  moodLabel: (label: string) => `Mood of ${label}, verse by verse`,
  moodTitle: (verse: number, praise: number, distress: number) => `verse ${verse}: ${numEn(praise)} praise, ${numEn(distress)} distress`,
  empty: 'No psalm matches these filters.',
  per100Value: per100,
}

export const psaHe: typeof psaEn = {
  title: 'תהלים',
  lede: 'ביקורת הצורות ממיינת את המזמורים לפי צורתם: מזמור השבח קורא לקהל להלל ומדבר על האל; הקינה פונה אל האל בגוף ראשון, מתוך מצוקה, ולעתים קרובות פונה אל השבח לפני סופה — "ודאות ההיענות" (תה׳ ו 9, יג 6, כב 23). כאן הצורה נמנית ממילות כל מזמור, בלי הכותרת: גופים, ציוויים ושאלות (מן המורפולוגיה) ומילות המצוקה והשבח (מתחומי SDBH). האם הצורה הנמנית מחזירה את הסוגים שמנה גונקל, והיכן פונות הקינות?',
  noData: 'לא חושב במבנה זה: הריצו `bsim psalms` ואחר כך `bsim build-db`.',
  genres: {
    hymn: 'מזמור שבח',
    lament_individual: 'קינת יחיד',
    lament_communal: 'קינת ציבור',
    royal: 'מזמור מלכות',
    thanksgiving: 'מזמור תודה',
    trust: 'שיר ביטחון',
    wisdom: 'מזמור חכמה',
  },
  unlabelled: 'מעורב או שנוי במחלוקת',
  features: {
    first_singular: 'אני',
    first_plural: 'אנחנו',
    second: 'אתה',
    imperative: 'ציוויים',
    imperative_plural: 'ציוויים ברבים',
    question: 'שאלות',
    distress: 'מצוקה',
    praise: 'שבח',
  },
  per100: 'ל־100 מילים',
  genreTitle: 'האם הצורה מחזירה את הסוגים?',
  genreLede: (labelled: number, k: number, titleWords: number) =>
    `ל־${numHe(labelled)} מזמורים יש אחד מסוגי גונקל (המקרים המובהקים; מזמור מעורב או שנוי במחלוקת הושמט). שמונה הספירות, מתוקננות, מקבצות את כל 150 המזמורים ל־${numHe(k)} אשכולות (Ward), כמספר הסוגים, בלי לראות את הסוגים; ${numHe(titleWords)} מילות כותרת הושמטו.`,
  genreResult: (nmi: number, nul: number, p: number) =>
    `האשכולות מתאימים לסוגים במידע הדדי מנורמל ${x3(nmi)}, לעומת ${x3(nul)} כשהסוגים מעורבבים בין המזמורים (p ${fp(p)}).`,
  robustGenres: (formOnly: number, formP: number, domainsOnly: number, domainsP: number, kept: number) =>
    `הצורה לבדה (גופים, ציוויים, שאלות) נותנת ${x3(formOnly)} (p ${fp(formP)}), מילות המצוקה והשבח לבדן ${x3(domainsOnly)} (p ${fp(domainsP)}); עם הכותרות, ${x3(kept)}.`,
  crosstabTitle: 'סוגים לפי אשכול',
  cluster: (c: number) => `אשכול ${numHe(c)}`,
  clusterHead: 'אשכול',
  genreHead: 'סוג',
  profileTitle: 'מה כל אשכול מונה',
  checksTitle: 'הצורות שנקבעו מראש',
  checksLede: (held: number, n: number) =>
    `${numHe(held)} מתוך ${numHe(n)} מתקיימות: ממוצע הסוג לעומת שאר המזמורים המסווגים, כשהסוגים מעורבבים (חד־צדדי, q של בנימיני–הוכברג).`,
  checkCols: { genre: 'סוג', feature: 'ספירה', expected: 'צפוי', mean: 'ממוצע', rest: 'האחרים', q: 'q' },
  higher: 'גבוה יותר',
  lower: 'נמוך יותר',
  turnTitle: 'היכן פונה הקינה?',
  turnLede: (minSide: number) =>
    `מצב הרוח של פסוק הוא מילות השבח שבו פחות מילות המצוקה. המפנה של מזמור הוא החלוקה של פסוקיו (לפחות ${numHe(minSide)} מכל צד) שבה מצב הרוח למילה עולה הכי הרבה מלפני לאחרי; ה־p שלו מסדר פסוקים מעורבב בתוך המזמור.`,
  knownLede: (found: number, n: number, expected: number, p: number, tol: number) =>
    `מפנים שהמחקר מונה: ${numHe(found)} מתוך ${numHe(n)} נמצאו בטווח ${countHe(tol, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}, לעומת ${expected.toFixed(1)} לחלוקה אקראית (p ${fp(p)}).`,
  robustTolerance: (rows: { tol: string; found: number; expected: number; p: number }[]) =>
    `בטווח ${rows.map((r) => `${r.tol}: ${numHe(r.found)} לעומת ${r.expected.toFixed(1)} (p ${fp(r.p)})`).join('; ')} פסוקים — התוצאה תלויה בטווח.`,
  knownCols: { named: 'המפנה הנקוב', found: 'המפנה שנמצא', p: 'p', chance: 'סיכוי' },
  tooShort: 'קצר מדי',
  lvh: (laments: number, nLaments: number, hymns: number, nHymns: number, p: number) =>
    `האם קינות פונות יותר ממזמורי שבח? ל־${numHe(laments)} מתוך ${numHe(nLaments)} קינות יחיד יש מפנה מעל המקרה, לעומת ${numHe(hymns)} מתוך ${numHe(nHymns)} מזמורי שבח (פישר, p ${fp(p)}). רוב המזמורים קצרים מכדי שמפנה יבלוט בכל אחד לבדו.`,
  listTitle: 'המזמורים',
  allGenres: 'כל הסוגים',
  allClusters: 'כל האשכולות',
  turnedOnly: 'רק מפנה מעל המקרה',
  sortLabel: 'סדר',
  sorts: { chapter: 'לפי הסדר', turn: 'המפנה הברור תחילה' },
  count: (n: number) => countHe(n, 'מזמור אחד', 'שני מזמורים', 'מזמורים'),
  words: (n: number) => countHe(n, 'מילה אחת', 'שתי מילים', 'מילים'),
  turnAt: (label: string, p: number, before: number, after: number) =>
    `פונה ב־${label} (p ${fp(p)}; מצב רוח ${x2(before)} ← ${x2(after)} למילה)`,
  noTurn: 'קצר מכדי לפנות',
  read: 'קריאה עם מצב הרוח',
  readTitle: 'המזמור בקורא השכבות, מילות המצוקה והשבח מסומנות',
  moodLabel: (label: string) => `מצב הרוח של ${label}, פסוק אחר פסוק`,
  moodTitle: (verse: number, praise: number, distress: number) => `פסוק ${numHe(verse)}: ${numHe(praise)} שבח, ${numHe(distress)} מצוקה`,
  empty: 'אין מזמור שמתאים לסינון.',
  per100Value: per100,
}
