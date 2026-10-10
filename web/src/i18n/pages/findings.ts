// Interface strings of the Findings page: each analysis's tested claim and its verdict (DESIGN.md
// §10, `/findings`). English first, Hebrew typed against it. Each text reads its numbers from the
// API, so it states what the current build found; wording that depends on a direction branches.

import type { FindingKey } from '../../api/types'
import { numEn, numHe, pct } from '../fmt'

type V = Record<string, number | null>
const n = (v: V, k: string) => v[k] ?? 0
const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (r: number) => r.toFixed(2)

export const findEn = {
  title: 'Findings',
  lede: (alpha: number) =>
    `What each analysis set out to test, and what the data say, with the numbers that decide it. A claim holds when its test passes at p ≤ ${alpha}; the verdicts are recomputed with every build, and each links to the page with the evidence.`,
  noData: 'No analysis has been computed in this build: run `bsim all`, then `bsim build-db`.',
  groups: {
    holds: { title: 'Borne out', hint: 'Above chance, or the check passes' },
    fails: { title: 'Not borne out', hint: 'No better than chance, or the data point the other way' },
    lead: { title: 'Leads, not findings', hint: 'Candidates no test yet separates from chance' },
  },
  items: {
    acrostics: {
      title: 'Alphabetic acrostics',
      text: (v: V) =>
        `${numEn(n(v, 'found'))} chapters run through the alphabet beyond chance; they include ${pct(n(v, 'recall'))} of the acrostics scholars list, and nothing else.`,
    },
    divisions: {
      title: 'Where the text divides',
      text: (v: V) =>
        `The scribes' paragraph breaks fall where the text itself turns: open breaks score ${x2(n(v, 'open'))} and closed ones ${x2(n(v, 'closed'))} on a scale where chance is ${x2(n(v, 'null'))} and unmarked verse ends ${x2(n(v, 'unmarked'))} (p ${fp(n(v, 'p'))}).`,
    },
    dating: {
      title: 'A late-language profile',
      text: (v: V) =>
        `Trained without Samuel, Kings and Chronicles, the profile finds the Chronicles side later in ${numEn(n(v, 'later'))} of ${numEn(n(v, 'pairs'))} parallel passages (p ${fp(n(v, 'p'))}): the same content in two states of the language. Each book left out in turn, it tells the late books from the early at AUC ${x2(n(v, 'auc'))}.`,
    },
    borrowing: {
      title: 'Who borrowed',
      text: (v: V) =>
        `Language and spelling name the borrower that scholars accept in ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'n'))} parallels they decide, each book pair held out in turn (${numEn(n(v, 'unclear'))} undecided; p ${fp(n(v, 'p'))}).`,
    },
    citations: {
      title: 'Explicit citations',
      text: (v: V) =>
        `“As the LORD commanded Moses” points to the command it carries out: ${pct(n(v, 'share'))} resolve to one source, against ${pct(n(v, 'null'))} of random verses (p ${fp(n(v, 'p'))}). Of the ${numEn(n(v, 'others'))} other formulas, ${numEn(n(v, 'others_held'))} do better than chance.`,
    },
    voices: {
      title: 'Speaker voices',
      text: (v: V) =>
        `${numEn(n(v, 'significant'))} of ${numEn(n(v, 'speakers'))} speakers talk unlike the other speakers of their own books; with the speakers shuffled, ${numEn(n(v, 'calibration'))} do.`,
    },
    clauses: {
      title: 'Mirrored clauses',
      text: (v: V) =>
        `${n(v, 'poetry') > n(v, 'prose') ? 'Poetry reverses the order of two parallel clauses more often than prose' : 'Poetry does not reverse two parallel clauses more often than prose'}: ${pct(n(v, 'poetry'))} of ${numEn(n(v, 'poetry_n'))} pairs against ${pct(n(v, 'prose'))} of ${numEn(n(v, 'prose_n'))} (p ${fp(n(v, 'p'))}).`,
    },
    echoes: {
      title: 'Who echoes whom',
      text: (v: V) =>
        `Where the spelling of a parallel points to its borrower, the language profile points the same way in ${numEn(n(v, 'agree'))} of ${numEn(n(v, 'n'))} (p ${fp(n(v, 'p'))}). ${numEn(n(v, 'backward'))} of the ${numEn(n(v, 'language'))} directions given by language alone run against the canon order: leads to read.`,
    },
    sevens: {
      title: 'Sevens',
      text: (v: V) =>
        n(v, 'largest') === 7
          ? `Key words come in multiples of 7 ${x2(n(v, 'ratio7'))} times as often as expected, more than for any other divisor.`
          : `Key words come in multiples of 7 ${x2(n(v, 'ratio7'))} times as often as expected — but every divisor shows an excess (10: ${x2(n(v, 'ratio10'))} times; the most, ${numEn(n(v, 'largest'))})${n(v, 'smallest') === 7 ? ', and 7 the least' : ''}. Nothing singles out 7.`,
    },
    chiasm: {
      title: 'Chiasm in repeated words',
      text: (v: V) =>
        n(v, 'share') < 0.5
          ? `Two words repeated in a verse come back in the same order more often than mirrored: ${numEn(n(v, 'verses_parallel'))} verses against ${numEn(n(v, 'verses_chiastic'))} (${pct(n(v, 'share'))} of pairs mirrored, p ${fp(n(v, 'p'))}). The figure exists, but it is not the habit.`
          : `Two words repeated in a verse come back mirrored more often than in the same order: ${numEn(n(v, 'verses_chiastic'))} verses against ${numEn(n(v, 'verses_parallel'))} (p ${fp(n(v, 'p'))}).`,
    },
    allusions: {
      title: 'Rare words over a few verses',
      text: (v: V) =>
        `${numEn(n(v, 'pairs'))} pairs of passages share three or more rare words; ${numEn(n(v, 'known'))} are known parallels, and the best new one has q ${x2(n(v, 'best_new_q'))} against shuffled verses.`,
    },
  } satisfies Record<FindingKey, { title: string; text: (v: V) => string }>,
}

export const findHe: typeof findEn = {
  title: 'ממצאים',
  lede: (alpha: number) =>
    `מה ביקש כל ניתוח לבדוק ומה אומרים הנתונים, עם המספרים המכריעים. טענה עומדת כשהמבחן שלה עובר ב־p ≤ ${alpha}; ההכרעות מחושבות מחדש בכל בנייה, וכל אחת מקשרת לעמוד שבו הראיות.`,
  noData: 'אף ניתוח לא חושב בבנייה זו: יש להריץ `bsim all` ואחר כך `bsim build-db`.',
  groups: {
    holds: { title: 'עומדות במבחן', hint: 'מעל המקרה, או שהבדיקה עוברת' },
    fails: { title: 'אינן עומדות במבחן', hint: 'לא טוב מן המקרה, או שהנתונים מצביעים לכיוון ההפוך' },
    lead: { title: 'כיווני חקירה, לא ממצאים', hint: 'מועמדים שאף מבחן עוד אינו מבדיל מן המקרה' },
  },
  items: {
    acrostics: {
      title: 'אקרוסטיכונים אלפביתיים',
      text: (v: V) =>
        `${numHe(n(v, 'found'))} פרקים עוברים על האלף־בית מעבר למקרה; הם כוללים ${pct(n(v, 'recall'))} מן האקרוסטיכונים שבספרות המחקר, ושום דבר אחר.`,
    },
    divisions: {
      title: 'היכן הטקסט מתחלק',
      text: (v: V) =>
        `הפרשיות של הסופרים נופלות היכן שהטקסט עצמו פונה: פתוחות מקבלות ${x2(n(v, 'open'))} וסתומות ${x2(n(v, 'closed'))}, בסולם שבו המקרה ${x2(n(v, 'null'))} וסופי פסוקים בלי סימן ${x2(n(v, 'unmarked'))} (p ${fp(n(v, 'p'))}).`,
    },
    dating: {
      title: 'פרופיל של לשון מאוחרת',
      text: (v: V) =>
        `כשהוא מאומן בלי שמואל, מלכים ודברי הימים, הפרופיל מוצא את צד דברי הימים מאוחר יותר ב־${numHe(n(v, 'later'))} מתוך ${numHe(n(v, 'pairs'))} קטעים מקבילים (p ${fp(n(v, 'p'))}): אותו תוכן בשני מצבים של הלשון. כשכל ספר מושאר בחוץ בתורו, הוא מבחין בין הספרים המאוחרים למוקדמים ב־AUC ${x2(n(v, 'auc'))}.`,
    },
    borrowing: {
      title: 'מי שאל ממי',
      text: (v: V) =>
        `הלשון והכתיב מצביעים על השואל המקובל במחקר ב־${numHe(n(v, 'agree'))} מתוך ${numHe(n(v, 'n'))} מקבילות שהם מכריעים בהן, כשכל זוג ספרים מושאר בחוץ בתורו (${numHe(n(v, 'unclear'))} לא הוכרעו; p ${fp(n(v, 'p'))}).`,
    },
    citations: {
      title: 'הפניות מפורשות',
      text: (v: V) =>
        `„כאשר צוה יהוה את משה” מצביע על הציווי שהוא מקיים: ${pct(n(v, 'share'))} מזוהים למקור אחד, לעומת ${pct(n(v, 'null'))} מפסוקים אקראיים (p ${fp(n(v, 'p'))}). מתוך ${numHe(n(v, 'others'))} הנוסחאות האחרות, ${numHe(n(v, 'others_held'))} טובות מן המקרה.`,
    },
    voices: {
      title: 'קולות הדוברים',
      text: (v: V) =>
        `${numHe(n(v, 'significant'))} מתוך ${numHe(n(v, 'speakers'))} דוברים מדברים אחרת משאר הדוברים בספריהם; בערבוב אקראי של הדוברים עוברים ${numHe(n(v, 'calibration'))}.`,
    },
    clauses: {
      title: 'פסוקיות במהופך',
      text: (v: V) =>
        `${n(v, 'poetry') > n(v, 'prose') ? 'השירה הופכת את סדר שתי פסוקיות מקבילות יותר מן הפרוזה' : 'השירה אינה הופכת את סדר שתי פסוקיות מקבילות יותר מן הפרוזה'}: ${pct(n(v, 'poetry'))} מתוך ${numHe(n(v, 'poetry_n'))} זוגות לעומת ${pct(n(v, 'prose'))} מתוך ${numHe(n(v, 'prose_n'))} (p ${fp(n(v, 'p'))}).`,
    },
    echoes: {
      title: 'מי מהדהד את מי',
      text: (v: V) =>
        `היכן שכתיב המקבילה מצביע על השואל, פרופיל הלשון מצביע לאותו כיוון ב־${numHe(n(v, 'agree'))} מתוך ${numHe(n(v, 'n'))} (p ${fp(n(v, 'p'))}). ${numHe(n(v, 'backward'))} מתוך ${numHe(n(v, 'language'))} הכיוונים שנקבעו בלשון בלבד הולכים נגד סדר הקאנון: כיווני חקירה.`,
    },
    sevens: {
      title: 'שבע',
      text: (v: V) =>
        n(v, 'largest') === 7
          ? `מילים מנחות מופיעות בכפולות של 7 פי ${x2(n(v, 'ratio7'))} מן הצפוי, יותר מכל מחלק אחר.`
          : `מילים מנחות מופיעות בכפולות של 7 פי ${x2(n(v, 'ratio7'))} מן הצפוי — אבל כל מחלק מראה עודף (10: פי ${x2(n(v, 'ratio10'))}; הגדול ביותר, ${numHe(n(v, 'largest'))})${n(v, 'smallest') === 7 ? ', ול־7 הקטן ביותר' : ''}. שום דבר אינו מייחד את 7.`,
    },
    chiasm: {
      title: 'כיאזמוס במילים חוזרות',
      text: (v: V) =>
        n(v, 'share') < 0.5
          ? `שתי מילים החוזרות בפסוק שבות באותו סדר יותר מאשר במהופך: ${numHe(n(v, 'verses_parallel'))} פסוקים לעומת ${numHe(n(v, 'verses_chiastic'))} (${pct(n(v, 'share'))} מן הזוגות במהופך, p ${fp(n(v, 'p'))}). התבנית קיימת, אבל אינה ההרגל.`
          : `שתי מילים החוזרות בפסוק שבות במהופך יותר מאשר באותו סדר: ${numHe(n(v, 'verses_chiastic'))} פסוקים לעומת ${numHe(n(v, 'verses_parallel'))} (p ${fp(n(v, 'p'))}).`,
    },
    allusions: {
      title: 'מילים נדירות על פני פסוקים אחדים',
      text: (v: V) =>
        `${numHe(n(v, 'pairs'))} זוגות קטעים חולקים שלוש מילים נדירות או יותר; ${numHe(n(v, 'known'))} מהם מקבילות ידועות, ולחדש הטוב ביותר q ${x2(n(v, 'best_new_q'))} מול פסוקים מעורבבים.`,
    },
  },
}
