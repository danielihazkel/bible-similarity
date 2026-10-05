// Interface strings of the Parallels pages: English first, Hebrew typed against it (see ../en.ts).

import type { RewriteOp, SequenceDirection } from '../../api/types'
import { countHe, numEn, numHe } from '../fmt'

type Labelled = { label: string; hint: string }

export const parEn = {
  book: 'Book',
  allBooks: 'All books',
  differentBooks: 'Different books only',
  includeQ: 'Include q > 0.05',
  /** "from → to" between two passages or words */
  arrow: '→',
  pairsPage: (n: number, page: number, pages: number) => `${numEn(n)} pairs · page ${page} of ${pages}`,

  discoveries: {
    title: 'Discoveries',
    ledeBefore: 'The strongest pairs that Sefaria does ',
    ledeNot: 'not',
    ledeAfter:
      ' cross-reference: one unit ranks the other in its top 10, no Sefaria link joins them, and neighbouring verses are left out.',
    none: 'No unlinked pairs match these filters.',
    rankFor: (b: string, rank: number, a: string) => `${b} is #${rank} for ${a}`,
    mutualTitle: "Each is in the other's top 10",
    mutual: 'mutual',
  },

  phrases: {
    title: 'Shared phrases',
    lede: 'Verse pairs whose lemmas line up as a phrase (same words in the same order, small gaps allowed). Rare words weigh more and formulaic phrases barely count, so quotations, allusions and parallel accounts come first.',
    atLeast: 'At least',
    recurringTitle: (n: number) => `Show phrases shared by more than ${n} verses (idioms)`,
    recurring: 'Include recurring phrases',
    none: 'No shared phrases match these filters.',
  },

  sequences: {
    title: 'Parallel sequences',
    lede: 'Passages that run alongside each other verse by verse, in the same order: synoptic accounts (Samuel–Kings and Chronicles), retold stories, a command and its execution, repeated lists. Each chain links similar verse pairs whose positions advance together on both sides; q estimates how often such a chain appears when verse order is shuffled within chapters.',
    order: 'Order',
    orders: {
      forward: { label: 'Same order', hint: 'Both passages advance together' },
      reverse: { label: 'Mirrored', hint: 'One passage runs backwards: A B C … C′ B′ A′' },
      mixed: { label: 'Reordered', hint: 'The same scene told in another order' },
      any: { label: 'Any order', hint: 'Same, mirrored and reordered chains' },
    } satisfies Record<SequenceDirection | 'any', Labelled>,
    significance: 'Significance',
    qOptions: { '0.05': 'q ≤ 0.05 (strong)', '0.2': 'q ≤ 0.2', all: 'All chains' } as Record<string, string>,
    hideRepeatsTitle: 'Hide repeats inside one chapter (lists such as Numbers 7)',
    hideRepeats: 'Hide repeats within a chapter',
    none: 'No sequences match these filters.',
    mirroredHint: ' Mirrored and reordered chains never beat the shuffled-order baseline: choose “All chains”.',
    page: (n: number, page: number, pages: number) => `${numEn(n)} sequences · page ${page} of ${pages}`,
  },

  sequence: {
    notId: 'Not a sequence id.',
    versePairs: (n: number) => `${n} verse pairs`,
    directions: {
      reverse: 'in mirrored order (the right side runs backwards)',
      mixed: 'in another order (the right side jumps back and forth)',
      forward: 'in the same order',
    } as Record<string, string>,
    score: (s: string) => `score ${s}`,
    noneLinked: 'none linked in Sefaria',
    linked: (n: number) => `${n} linked in Sefaria (★)`,
    onlySides: (a: number, b: number) => ` · ${a} verse(s) only on the left, ${b} only on the right`,
    markChanges: 'Mark word changes',
    loose: '≈ loosely parallel, not marked',
    aligned: 'Aligned verses',
    cosineTitle: (cos: string, gold: boolean, loose: boolean) =>
      `Cosine ${cos}${gold ? ' · linked in Sefaria' : ''}${loose ? ' · loosely parallel: too different to mark word by word' : ''}`,
  },

  changes: {
    title: 'How parallels differ',
    lede: 'Every verse pair of a strong parallel sequence aligned word by word, the earlier passage (in canon order) on the left. Counted across the corpus, the changes show habits of the later text: Chronicles writes דויד for דוד, על for אל, אני for אנכי, and often אלהים where Samuel–Kings has יהוה.',
    view: 'View',
    byWord: 'All changes by word',
    rewrites: 'Systematic rewrites',
    kind: 'Kind of change',
    opCount: (label: string, n: number) => `${label} ${numEn(n)}`,
    anyBook: 'Any book',
    earlierIn: 'Earlier passage in',
    laterIn: 'Later passage in',
    none: 'No changes of this kind for these books.',
    page: (n: number, page: number, pages: number) => `${numEn(n)} distinct changes · page ${page} of ${pages}`,
    earlier: 'Earlier',
    later: 'Later',
    times: 'Times',
    sequences: 'Sequences',
    examples: 'Examples',
    openSequence: 'Open the parallel sequence',
  },

  rewrites: {
    intro:
      "A change counts as a habit when it recurs between two books more often than their overall rate of change explains: the later book's word, given the earlier one, compared by log-likelihood (G²), with q corrected for testing every change of every book pair.",
    books: 'Books',
    allPairs: 'All book pairs',
    within: (name: string) => `${name} (repeats within)`,
    pair: (a: string, b: string) => `${a} → ${b}`,
    optionPairs: (n: number) => `${n} verse pairs`,
    change: 'Change',
    any: 'Any',
    ops: {
      substitution: { label: 'Substituted', hint: 'one word regularly replaced by another' },
      omitted: { label: 'Dropped', hint: 'a word the later text regularly leaves out' },
      added: { label: 'Added', hint: 'a word the later text regularly adds' },
    } satisfies Record<RewriteOp, Labelled>,
    none: 'No systematic changes for these filters.',
    page: (n: number, page: number, pages: number) => `${numEn(n)} changes · page ${page} of ${pages}`,
    timesTitle: 'Times this change occurs / words it could apply to',
    qTitle: 'Benjamini–Hochberg q over all book pairs and changes',
    rateTitle: (rate: number) => `${Math.round(rate * 100)}% of the time`,
    profile: 'How these books differ',
    parallelVerses: 'Parallel verses',
    profilePairs: (n: number, aWords: number, bWords: number) => `${n} pairs, ${numEn(aWords)} → ${numEn(bWords)} words`,
    per100Of: (from: string) => `Per 100 words of ${from}`,
    per100: (sub: string, om: string, add: string, form: string, spell: string) =>
      `${sub} substituted · ${om} dropped · ${add} added · ${form} other form · ${spell} spelling`,
    spelling: 'Spelling',
    spellingText: (to: string, from: string, plene: number, defective: number, fuller: number) =>
      `${to} writes a vowel letter (ו / י) ${from} lacks ${plene}× and drops one ${defective}× (${fuller}% fuller)`,
  },

  typeScenes: {
    title: 'Action sequences',
    lede: "Two passages that tell the same actions in the same order, whatever the names and wording: the verbs of every pericope are aligned with those of others (rare verbs count more), and each alignment is compared with the same passages' verbs shuffled. The strongest are court tales (Daniel 3 and 6: accused, thrown in, rescued), ritual procedures and visions retold.",
    note: 'The classic literary type-scenes (meetings at a well, annunciations to barren women) vary their verbs too much to stand out this way: they score little above random pairs of chapters.',
    textualTitle: 'Pairs joined by a parallel sequence: the same text told twice',
    textual: 'Include textual parallels',
    none: 'No aligned passages for these filters.',
    actions: (n: number) => `${n} actions in order`,
    qTitle: 'Expected share of chance alignments among those at least this strong (verb order shuffled inside each passage)',
    textualTag: 'textual parallel',
  },
}

export const parHe: typeof parEn = {
  book: 'ספר',
  allBooks: 'כל הספרים',
  differentBooks: 'רק בין ספרים שונים',
  includeQ: 'כולל q > 0.05',
  arrow: '←',
  pairsPage: (n: number, page: number, pages: number) =>
    `${countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות')} · עמוד ${page} מתוך ${pages}`,

  discoveries: {
    title: 'תגליות',
    ledeBefore: 'הזוגות החזקים ביותר ש',
    ledeNot: 'אין',
    ledeAfter:
      ' להם הפניה בספריא: יחידה אחת מדרגת את האחרת בין 10 הדומות לה ביותר, שום קישור של ספריא אינו מחבר ביניהן, ופסוקים סמוכים אינם נכללים.',
    none: 'אין זוגות לא מקושרים התואמים את הסינון.',
    rankFor: (b: string, rank: number, a: string) => `${b} במקום ${rank} אצל ${a}`,
    mutualTitle: 'כל אחת בין 10 הדומות ביותר לאחרת',
    mutual: 'הדדי',
  },

  phrases: {
    title: 'צירופים משותפים',
    lede: 'זוגות פסוקים שערכיהם מתיישרים לצירוף (אותן מילים באותו סדר, עם פערים קטנים). למילים נדירות משקל רב יותר וצירופים נוסחתיים כמעט אינם נחשבים, ולכן ציטוטים, רמיזות ותיאורים מקבילים באים ראשונים.',
    atLeast: 'לפחות',
    recurringTitle: (n: number) => `הצגת צירופים המשותפים ליותר מ־${n} פסוקים (ניבים)`,
    recurring: 'כולל צירופים חוזרים',
    none: 'אין צירופים משותפים התואמים את הסינון.',
  },

  sequences: {
    title: 'רצפים מקבילים',
    lede: 'קטעים ההולכים זה לצד זה פסוק אחר פסוק, באותו סדר: תיאורים סינופטיים (שמואל–מלכים ודברי הימים), סיפורים המסופרים שוב, ציווי וביצועו, רשימות חוזרות. כל שרשרת מחברת זוגות פסוקים דומים שמקומם מתקדם יחד בשני הצדדים; q מעריך באיזו תדירות מופיעה שרשרת כזאת כשסדר הפסוקים מעורבב בתוך הפרקים.',
    order: 'סדר',
    orders: {
      forward: { label: 'אותו סדר', hint: 'שני הקטעים מתקדמים יחד' },
      reverse: { label: 'סדר הפוך', hint: 'קטע אחד הולך לאחור: A B C … C′ B′ A′' },
      mixed: { label: 'סדר משתנה', hint: 'אותה סצנה מסופרת בסדר אחר' },
      any: { label: 'כל סדר', hint: 'שרשראות באותו סדר, בסדר הפוך ובסדר משתנה' },
    },
    significance: 'מובהקות',
    qOptions: { '0.05': 'q ≤ 0.05 (חזק)', '0.2': 'q ≤ 0.2', all: 'כל השרשראות' },
    hideRepeatsTitle: 'הסתרת חזרות בתוך פרק אחד (רשימות כמו במדבר ז)',
    hideRepeats: 'הסתרת חזרות בתוך פרק',
    none: 'אין רצפים התואמים את הסינון.',
    mirroredHint: ' שרשראות בסדר הפוך או משתנה אינן עוברות לעולם את קו הבסיס של סדר מעורבב: בחרו „כל השרשראות”.',
    page: (n: number, page: number, pages: number) =>
      `${countHe(n, 'רצף אחד', 'שני רצפים', 'רצפים')} · עמוד ${page} מתוך ${pages}`,
  },

  sequence: {
    notId: 'אין זה מזהה של רצף.',
    versePairs: (n: number) => countHe(n, 'זוג פסוקים אחד', 'שני זוגות פסוקים', 'זוגות פסוקים'),
    // the ladder's columns follow the page direction: in Hebrew the later passage is on the left
    directions: {
      reverse: 'בסדר הפוך (הצד השמאלי הולך לאחור)',
      mixed: 'בסדר אחר (הצד השמאלי קופץ הלוך ושוב)',
      forward: 'באותו סדר',
    },
    score: (s: string) => `ציון ${s}`,
    noneLinked: 'אף אחד אינו מקושר בספריא',
    linked: (n: number) => `${n} מקושרים בספריא (★)`,
    onlySides: (a: number, b: number) => ` · ${a} פסוקים רק בצד הימני, ${b} רק בשמאלי`,
    markChanges: 'סימון שינויי מילים',
    loose: '≈ מקביל באופן רופף, לא מסומן',
    aligned: 'פסוקים מיושרים',
    cosineTitle: (cos: string, gold: boolean, loose: boolean) =>
      `קוסינוס ${cos}${gold ? ' · מקושר בספריא' : ''}${loose ? ' · מקביל באופן רופף: שונים מדי לסימון מילה במילה' : ''}`,
  },

  changes: {
    title: 'במה נבדלות המקבילות',
    lede: 'כל זוג פסוקים ברצף מקביל חזק מיושר מילה במילה, והקטע המוקדם (לפי סדר הספרים) מימין. כשסופרים אותם בכל המקרא, השינויים מגלים את הרגלי הטקסט המאוחר: דברי הימים כותב דויד במקום דוד, על במקום אל, אני במקום אנכי, ולא פעם אלהים במקום שבו בשמואל–מלכים כתוב יהוה.',
    view: 'תצוגה',
    byWord: 'כל השינויים לפי מילה',
    rewrites: 'שכתובים שיטתיים',
    kind: 'סוג השינוי',
    opCount: (label: string, n: number) => `${label} ${numHe(n)}`,
    anyBook: 'כל ספר',
    earlierIn: 'הקטע המוקדם ב',
    laterIn: 'הקטע המאוחר ב',
    none: 'אין שינויים מסוג זה בספרים האלה.',
    page: (n: number, page: number, pages: number) =>
      `${countHe(n, 'שינוי אחד', 'שני שינויים', 'שינויים שונים')} · עמוד ${page} מתוך ${pages}`,
    earlier: 'מוקדם',
    later: 'מאוחר',
    times: 'פעמים',
    sequences: 'רצפים',
    examples: 'דוגמאות',
    openSequence: 'פתיחת הרצף המקביל',
  },

  rewrites: {
    intro:
      'שינוי נחשב להרגל כשהוא חוזר בין שני ספרים יותר ממה ששיעור השינויים הכללי שלהם מסביר: מילת הספר המאוחר, בהינתן המילה המוקדמת, נבחנת ביחס הנראות (G²), ו־q מתוקן לבדיקת כל שינוי בכל זוג ספרים.',
    books: 'ספרים',
    allPairs: 'כל זוגות הספרים',
    within: (name: string) => `${name} (חזרות בתוכו)`,
    pair: (a: string, b: string) => `${a} ← ${b}`,
    optionPairs: (n: number) => countHe(n, 'זוג פסוקים אחד', 'שני זוגות פסוקים', 'זוגות פסוקים'),
    change: 'שינוי',
    any: 'כל שינוי',
    ops: {
      substitution: { label: 'הוחלף', hint: 'מילה המוחלפת בקביעות במילה אחרת' },
      omitted: { label: 'הושמט', hint: 'מילה שהטקסט המאוחר משמיט בקביעות' },
      added: { label: 'נוסף', hint: 'מילה שהטקסט המאוחר מוסיף בקביעות' },
    },
    none: 'אין שינויים שיטתיים התואמים את הסינון.',
    page: (n: number, page: number, pages: number) =>
      `${countHe(n, 'שינוי אחד', 'שני שינויים', 'שינויים')} · עמוד ${page} מתוך ${pages}`,
    timesTitle: 'מספר הפעמים שהשינוי מופיע / המילים שהוא יכול לחול עליהן',
    qTitle: 'q של בנג׳מיני–הוכברג על פני כל זוגות הספרים והשינויים',
    rateTitle: (rate: number) => `ב־${Math.round(rate * 100)}% מהמקרים`,
    profile: 'במה נבדלים הספרים האלה',
    parallelVerses: 'פסוקים מקבילים',
    profilePairs: (n: number, aWords: number, bWords: number) =>
      `${countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות')}, ${numHe(aWords)} ← ${numHe(bWords)} מילים`,
    per100Of: (from: string) => `ל־100 מילים של ${from}`,
    per100: (sub: string, om: string, add: string, form: string, spell: string) =>
      `${sub} הוחלפו · ${om} הושמטו · ${add} נוספו · ${form} בצורה אחרת · ${spell} בכתיב`,
    spelling: 'כתיב',
    spellingText: (to: string, from: string, plene: number, defective: number, fuller: number) =>
      `${to} כותב אם קריאה (ו / י) שחסרה ב${from} ${plene} פעמים ומשמיט אחת ${defective} פעמים (${fuller}% מלא יותר)`,
  },

  typeScenes: {
    title: 'רצפי פעולות',
    lede: 'שני קטעים המספרים אותן פעולות באותו סדר, יהיו השמות והניסוח אשר יהיו: הפעלים של כל פיסקה מיושרים עם אלה של פיסקאות אחרות (לפעלים נדירים משקל רב יותר), וכל יישור מושווה לפעלי אותם קטעים בסדר מעורבב. החזקים ביותר הם סיפורי חצר (דניאל ג ו־ו: הלשנה, השלכה, הצלה), נהלי פולחן וחזיונות המסופרים שוב.',
    note: 'סצנות הטיפוס הספרותיות הקלאסיות (פגישות ליד הבאר, בשורות לעקרות) מגוונות את הפעלים יותר מדי כדי לבלוט כך: ציונן גבוה רק מעט מזה של זוגות פרקים אקראיים.',
    textualTitle: 'זוגות המחוברים ברצף מקביל: אותו טקסט המסופר פעמיים',
    textual: 'כולל מקבילות טקסטואליות',
    none: 'אין קטעים מיושרים התואמים את הסינון.',
    actions: (n: number) => `${n} פעולות באותו סדר`,
    qTitle: 'השיעור הצפוי של יישורים מקריים מבין היישורים החזקים לפחות כמו זה (סדר הפעלים מעורבב בתוך כל קטע)',
    textualTag: 'מקבילה טקסטואלית',
  },
}
