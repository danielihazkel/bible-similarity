// Interface strings of Poetry → Meter: stresses per line and the falling lament line (DESIGN.md
// §16.37). English first, Hebrew typed against it.

import type { MeterGroup } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))

export const metEn = {
  view: 'Meter',
  lede: 'Hebrew verse is counted in stresses: every accented word carries one, and words joined by a maqaf share one. The accents divide each verse in two, and each part in two again; a line here is the largest of those parts with at most a handful of stresses, and its own main pause splits it into two members. The lament (qinah) line is said to fall: a longer member, then a shorter one (3:2), the voice breaking off. Lamentations 1–4 are said to be written in it.',
  noData: 'Not computed in this build: run `bsim meter`, then `bsim build-db`.',
  testTitle: 'Does Lamentations fall?',
  test: (min: number, max: number, mean: number | null, pool: number | null, n: number, p: number | null, poeticP: number | null) =>
    `Lines of ${numEn(min)}–${numEn(max)} stresses, net fall = the share of lines whose first member is longer minus the share whose first member is shorter. Lamentations 1–4: ${x2(mean)}; other poetry under the same (prose) accents, ${numEn(n)} chapters: ${x2(pool)} (p ${fp(p)}, chapters drawn at random). Against Psalms, Proverbs and Job, which have accents of their own: p ${fp(poeticP)}.`,
  testNote: 'The prose accents end a verse or a half-verse on a short member, so lines fall a little everywhere, prose lists included; that is why the comparison is with poetry under the same accents. The line lengths were chosen with Lamentations in view, so the table below repeats the test with other lengths.',
  poolNote: (quantile: number, prob: number | null) =>
    `The poetry pool: the prose-accented chapters in the top ${pct(1 - quantile)} by their verses' probability of parallel halves (at least ${x2(prob)}).`,
  cols: {
    chapter: 'Chapter',
    group: 'Group',
    lines: 'Lines',
    fall: 'Falling',
    rise: 'Rising',
    net: 'Net fall',
    share32: '3:2',
    pct: 'Above the pool',
  },
  colTitles: {
    lines: 'Lines of the measured length that split into two stressed members',
    fall: 'Share of lines whose first member is longer (3:2, 4:2 …)',
    rise: 'Share of lines whose first member is shorter (2:3 …)',
    net: 'Falling minus rising',
    share32: 'Share of lines of exactly 3 and 2 stresses',
    pct: 'Share of the poetry pool with a lower net fall',
  },
  controlTitle: 'The control: Lamentations 5',
  control: 'Lamentations 5 is a lament too, but a prayer in even lines (mostly 3:3); it should not stand out.',
  namedTitle: 'Chapters that speak of a lament',
  named: (n: number, mean: number | null, pool: number | null, p: number | null) =>
    `The ${countEn(n, 'chapter', 'chapters')} outside Lamentations that use the word קינה, tested the same way: net fall ${x2(mean)} against ${x2(pool)} (p ${fp(p)}). The word picks out the laments of Ezekiel and Amos, but also chapters that only mention one.`,
  gridTitle: 'Other line lengths',
  grid: { length: 'Stresses per line', lam: 'Lamentations 1–4', pool: 'Pool', p: 'p (pool)', poeticP: 'p (Psalms, Proverbs, Job)' },
  patternsTitle: 'Commonest lines',
  patterns: (lines: number) => `${countEn(lines, 'line', 'lines')}:`,
  rankTitle: 'Chapters by net fall',
  rankNote: (min: number) =>
    `Chapters with at least ${numEn(min)} measured lines. Prose lists of offerings and the like rank high: their verses end on short members. Among the poetry, high net falls are leads for laments outside Lamentations.`,
  groups: {
    test: 'Lamentations 1–4',
    control: 'Lamentations 5',
    pool: 'Poetry (prose accents)',
    poetic: 'Psalms, Proverbs, Job',
    prose: 'Prose',
  } satisfies Record<MeterGroup, string>,
  anyGroup: 'All',
  ranked: (n: number) => countEn(n, 'chapter', 'chapters'),
  // the unit page
  toggle: 'Stresses',
  toggleTitle: 'The stresses of each line: first member : second member',
  theMeter: 'the stresses',
  verseLines: 'Stresses per line',
  unsplit: (n: number) => `${numEn(n)}`,
  chapterLine: (net: number, pctile: number | null, group: string) =>
    `This chapter's lines: net fall ${x2(net)}${pctile == null ? '' : `, above ${pct(pctile)} of the poetry pool`} (${group}).`,
}

export const metHe: typeof metEn = {
  view: 'משקל',
  lede: 'שירת המקרא נמדדת בהטעמות: כל מילה מוטעמת נושאת הטעמה אחת, ומילים המחוברות במקף חולקות אחת. הטעמים מחלקים כל פסוק לשניים, וכל חלק שוב לשניים; שורה כאן היא החלק הגדול ביותר שיש בו עד הטעמות אחדות, וההפסק הראשי שלה מחלק אותה לשתי צלעות. שורת הקינה, כך אומרים, יורדת: צלע ארוכה ואחריה קצרה (3:2), כקול הנשבר. איכה א–ד נכתבו, כך אומרים, בשורה זו.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim meter` ואחר כך `bsim build-db`.',
  testTitle: 'האם שורות איכה יורדות?',
  test: (min: number, max: number, mean: number | null, pool: number | null, n: number, p: number | null, poeticP: number | null) =>
    `שורות של ${numHe(min)}–${numHe(max)} הטעמות; ירידה נטו = שיעור השורות שצלען הראשונה ארוכה פחות שיעור השורות שצלען הראשונה קצרה. איכה א–ד: ${x2(mean)}; שירה אחרת באותה מערכת טעמים (טעמי כ״א הספרים), ${numHe(n)} פרקים: ${x2(pool)} (p ${fp(p)}, פרקים בהגרלה). מול תהלים, משלי ואיוב, שטעמיהם אחרים: p ${fp(poeticP)}.`,
  testNote: 'טעמי כ״א הספרים מסיימים פסוק או חצי פסוק בצלע קצרה, ולכן שורות יורדות מעט בכל מקום, גם ברשימות שבפרוזה; משום כך ההשוואה היא לשירה באותה מערכת טעמים. אורכי השורות נבחרו כשאיכה לנגד העיניים, ולכן הטבלה למטה חוזרת על המבחן באורכים אחרים.',
  poolNote: (quantile: number, prob: number | null) =>
    `מאגר השירה: הפרקים בטעמי כ״א הספרים שב־${pct(1 - quantile)} העליונים לפי הסיכוי של פסוקיהם לחצאים מקבילים (לפחות ${x2(prob)}).`,
  cols: {
    chapter: 'פרק',
    group: 'קבוצה',
    lines: 'שורות',
    fall: 'יורדות',
    rise: 'עולות',
    net: 'ירידה נטו',
    share32: '3:2',
    pct: 'מעל המאגר',
  },
  colTitles: {
    lines: 'שורות באורך הנמדד שמתחלקות לשתי צלעות מוטעמות',
    fall: 'שיעור השורות שצלען הראשונה ארוכה (3:2, 4:2 …)',
    rise: 'שיעור השורות שצלען הראשונה קצרה (2:3 …)',
    net: 'יורדות פחות עולות',
    share32: 'שיעור השורות של 3 ו־2 הטעמות בדיוק',
    pct: 'שיעור הפרקים במאגר השירה שירידתם נמוכה יותר',
  },
  controlTitle: 'הביקורת: איכה ה',
  control: 'גם איכה ה היא קינה, אבל תפילה בשורות שקולות (בעיקר 3:3); היא אינה אמורה לבלוט.',
  namedTitle: 'פרקים המדברים על קינה',
  named: (n: number, mean: number | null, pool: number | null, p: number | null) =>
    `${countHe(n, 'הפרק', 'שני הפרקים', 'הפרקים')} מחוץ לאיכה שבהם המילה קינה, במבחן זהה: ירידה נטו ${x2(mean)} לעומת ${x2(pool)} (p ${fp(p)}). המילה מאתרת את הקינות של יחזקאל ועמוס, אבל גם פרקים שרק מזכירים קינה.`,
  gridTitle: 'אורכי שורה אחרים',
  grid: { length: 'הטעמות בשורה', lam: 'איכה א–ד', pool: 'המאגר', p: 'p (המאגר)', poeticP: 'p (תהלים, משלי, איוב)' },
  patternsTitle: 'השורות השכיחות',
  patterns: (lines: number) => `${countHe(lines, 'שורה אחת', 'שתי שורות', 'שורות')}:`,
  rankTitle: 'פרקים לפי ירידה נטו',
  rankNote: (min: number) =>
    `פרקים שיש בהם לפחות ${numHe(min)} שורות נמדדות. רשימות קרבנות וכדומה שבפרוזה מדורגות גבוה: פסוקיהן מסתיימים בצלעות קצרות. בשירה, ירידה גבוהה היא כיוון חקירה לקינות מחוץ לאיכה.`,
  groups: {
    test: 'איכה א–ד',
    control: 'איכה ה',
    pool: 'שירה (טעמי כ״א)',
    poetic: 'תהלים, משלי, איוב',
    prose: 'פרוזה',
  },
  anyGroup: 'הכול',
  ranked: (n: number) => countHe(n, 'פרק אחד', 'שני פרקים', 'פרקים'),
  toggle: 'הטעמות',
  toggleTitle: 'ההטעמות של כל שורה: צלע ראשונה : צלע שנייה',
  theMeter: 'ההטעמות',
  verseLines: 'הטעמות בכל שורה',
  unsplit: (n: number) => `${numHe(n)}`,
  chapterLine: (net: number, pctile: number | null, group: string) =>
    `שורות הפרק: ירידה נטו ${x2(net)}${pctile == null ? '' : `, מעל ${pct(pctile)} ממאגר השירה`} (${group}).`,
}
