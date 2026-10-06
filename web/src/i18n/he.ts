// The interface's Hebrew messages (DESIGN.md §11.1); same shape as `en.ts`, checked by tsc.
//
// Glossary (keep terms consistent across the viewer):
//   verse פסוק · chapter פרק · pericope פיסקה (פתוחה / סתומה) · parasha פרשה · book ספר
//   lemma ערך (ערך מילוני) · Strong's סטרונג · similarity דמיון · parallel מקבילה
//   lexical מילולי · semantic סמנטי · fused משולב · structural מבני · domain (semantic domain) תחום
//   te'amim טעמים · niqqud ניקוד · colon / verse half צלע · Leitwort מילה מנחה
//   cross-reference הפניה · Sefaria ספריא

import { hebrewNumeral } from '../lib/hebrew'
import type { Messages } from './en'
import { ovHe } from './pages/overview'
import { parHe } from './pages/parallels'
import { patHe } from './pages/patterns'
import { domHe } from './pages/domains'
import { senHe } from './pages/senses'
import { datHe } from './pages/dating'
import { labHe } from './pages/labels'
import { synHe } from './pages/syntax'
import { borHe } from './pages/borrowing'

const num = (n: number) => n.toLocaleString('he-IL')
/** Hebrew counts: one, two (dual-like forms) and many. */
const pl = (n: number, one: string, two: string, many: string) =>
  n === 1 ? one : n === 2 ? two : `${num(n)} ${many}`

const unitTypes: Record<string, string> = { verse: 'פסוק', chapter: 'פרק', pericope: 'פיסקה', parasha: 'פרשה' }
const unitTypesPlural: Record<string, string> = { verse: 'פסוקים', chapter: 'פרקים', pericope: 'פיסקאות', parasha: 'פרשות' }
const similarOf: Record<string, string> = {
  verse: 'פסוקים דומים',
  chapter: 'פרקים דומים',
  pericope: 'פיסקאות דומות',
  parasha: 'פרשות דומות',
}
const unitTypesThis: Record<string, string> = { verse: 'מהפסוק', chapter: 'מהפרק', pericope: 'מהפיסקה', parasha: 'מהפרשה' }

export const he: Messages = {
  locale: 'he',
  num,
  pct: (x: number) => `${Math.round(x * 100)}%`,

  cv: (c: number, v: number) => `${hebrewNumeral(c)}:${hebrewNumeral(v)}`,

  site: {
    name: 'מקבילות בתנ״ך',
    skip: 'דילוג לתוכן',
    menu: 'תפריט',
    mainNav: 'ראשי',
    copyLink: 'העתקת קישור',
    copied: 'הועתק',
    copyLinkTitle: 'העתקת קישור לתצוגה הזאת',
    textDisplay: 'תצוגת הטקסט',
    language: 'שפת הממשק',
    footer: {
      display: 'טקסט התצוגה: ספריא,',
      mam: 'מקרא על פי המסורה',
      lemmas: 'ערכים ומורפולוגיה:',
      wlc: '(WLC בנחלת הכלל, מורפולוגיה CC BY 4.0). הפניות: ספריא; OpenBible.info ‏(CC-BY) להערכה. לשימוש אישי ולמחקר.',
      lexicon: 'מובני מילים ותחומי משמעות: SDBH של חבר אגודות התנ״ך (CC BY-SA 4.0); סוגי שמות: OpenScriptures HebrewLexicon ‏(CC BY 4.0).',
      syntax: 'פסוקיות, צירופים ודיבור: ETCBC, ‏BHSA ‏(CC BY-NC 4.0).',
    },
    notFound: 'הדף לא נמצא.',
    backToBooks: 'חזרה לספרים',
  },

  nav: {
    browse: 'עיון',
    search: 'חיפוש',
    compare: 'השוואה',
    about: 'אודות',
    parallels: 'מקבילות',
    patterns: 'דפוסים',
    overview: 'מבט־על',
    discoveries: { label: 'תגליות', hint: 'זוגות חזקים שאין להם קישור בספריא' },
    labels: { label: 'הסימונים שלך', hint: 'זוגות ששפטת: מערך זהב שלישי' },
    borrowing: { label: 'מי שאל ממי', hint: 'איזה צד של מקבילה נראה מאוחר' },
    phrases: { label: 'צירופים', hint: 'רצפי מילים משותפים' },
    sequences: { label: 'רצפים', hint: 'קטעים מקבילים פסוק אחר פסוק' },
    changes: { label: 'שינויים', hint: 'במה נבדלים קטעים מקבילים' },
    typescenes: { label: 'רצפי פעולות', hint: 'אותן פעולות באותו סדר' },
    structure: { label: 'מבנה', hint: 'מסגרת, כיאזם, מילים מנחות' },
    acrostics: { label: 'אקרוסטיכונים', hint: 'שורות לפי סדר הא״ב' },
    poetry: { label: 'שירה', hint: 'צלעות פסוק מקבילות' },
    wordplay: { label: 'משחקי לשון', hint: 'מילים בעלות צליל דומה' },
    names: { label: 'שמות', hint: 'אנשים ומקומות' },
    domains: { label: 'תחומים', hint: 'מילים לפי משמעות: שדות סמנטיים' },
    map: { label: 'מפה', hint: 'יחידות לפי משמעות, קרבה בין ספרים' },
    network: { label: 'רשת', hint: 'קהילות הדים, הקטעים המהדהדים ביותר' },
    style: { label: 'סגנון', hint: 'סטילומטריה ומעברי סגנון' },
    shifts: { label: 'תזוזות', hint: 'מילים שמשמשות אחרת לאורך התנ״ך' },
    language: { label: 'לשון', hint: 'פרופיל עברית מקראית מאוחרת לכל פרק' },
    speech: { label: 'מי מדבר', hint: 'סיפור ודיבור ישיר, והדוברים' },
    eval: { label: 'הערכה', hint: 'עד כמה נמצאות הפניות ידועות' },
  },

  status: {
    loading: 'טוען…',
    notFound: 'לא נמצא:',
    unreachable: (msg: string) => `אין גישה ל־API ‏(${msg}). האם \`bsim serve\` פועל?`,
    apiUnreachable: 'אין גישה ל־API',
    couldNotLoad: (what: string) => `לא ניתן לטעון את ${what}`,
    staleChunk: 'לא ניתן לטעון את הדף: הממשק עודכן מאז שהלשונית נפתחה.',
    crashed: (msg: string | undefined) => `משהו השתבש בהצגת הדף${msg ? `: ${msg}` : ''}.`,
    reload: 'טעינה מחדש',
  },

  pager: {
    label: 'עמודים',
    previous: '→ הקודם',
    next: 'הבא ←',
    page: 'עמוד',
    of: (n: number) => `מתוך ${n}`,
    pageOf: (n: number) => `עמוד (מתוך ${n})`,
    go: 'מעבר',
    pastEnd: (page: number, last: number) =>
      `עמוד ${page} נמצא אחרי סוף הרשימה (${last === 1 ? 'עמוד אחד' : `${last} עמודים`}).`,
    lastPage: 'מעבר לעמוד האחרון',
  },

  units: {
    type: (t: string) => unitTypes[t] ?? t,
    plural: (t: string) => unitTypesPlural[t] ?? t,
    noun: (t: string) => unitTypes[t] ?? t,
    verses: (n: number) => pl(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
    chapterN: (n: number) => `פרק ${n}`,
    chaptersShort: (n: number) => `${n} פרקים`,
    sections: { Torah: 'תורה', Prophets: 'נביאים', Writings: 'כתובים' },
    tabs: { chapters: 'פרקים', verses: 'פסוקים', parashot: 'פרשות', pericopes: 'פיסקאות' },
    markers: { pe: 'פ פתוחה', samekh: 'ס סתומה' },
    unknownBook: 'ספר לא מוכר.',
    unitType: 'סוג יחידה',
    similarVerses: (ref: string) => `${ref}: פסוקים דומים`,
    book: 'ספר',
    books: 'ספרים',
    context: 'הקשר',
  },

  modes: {
    label: 'סוג דמיון',
    names: { lexical: 'מילולי', semantic: 'סמנטי', fused: 'משולב', structural: 'מבני', domain: 'תחומים' },
    hints: {
      lexical: 'ניסוח משותף: BM25 / TF-IDF על ערכי OSHB, נוסחאות במשקל מופחת',
      semantic: 'משמעות משותפת: שיכוני BEREL מכווננים (CSLS)',
      fused: 'שניהם יחד, במיזוג דירוגים הדדי משוקלל',
      structural: 'אותה תבנית דקדוקית, בכל מילים: BM25 / TF-IDF על n-גרמים של צורות (חלק דיבר, בניין וזמן, מצב)',
      domain: 'אותם תחומי משמעות, בכל מילים: BM25 / TF-IDF על התחום הסמנטי של כל מילה בהקשרה לפי SDBH',
    },
    score: (mode: string) => `ציון ${mode}`,
    top: 'מובילים',
    exclude: {
      neighbors: 'הסתרת שכנים ±2',
      chapter: 'הסתרת אותו פרק',
      book: 'הסתרת אותו ספר',
      known: 'הסתרת המקושרים בספריא',
    },
    textModes: { teamim: 'ניקוד וטעמים', niqqud: 'ניקוד בלבד', consonants: 'אותיות בלבד' },
  },

  rank: {
    lex: 'מיל׳',
    sem: 'סמ׳',
    notInTop: (label: string, k: number) => `${label}: לא בין ${k} המובילים`,
    rank: (label: string, rank: number, score: string) => `${label}: מקום ${rank}, ציון ${score}`,
  },

  q: (q: number) => (q < 0.001 ? 'q < 0.001' : `q = ${q < 0.01 ? q.toFixed(3) : q.toFixed(2)}`),
  granularity: { verse: 'פסוק אחר פסוק', colon: 'צלע אחר צלע' },

  diff: {
    marks: 'סימוני שינויים',
    ops: {
      substitution: { label: 'הוחלף', hint: 'מילה (ערך) אחרת באותו מקום' },
      added: { label: 'נוסף', hint: 'רק בקטע המאוחר' },
      omitted: { label: 'הושמט', hint: 'רק בקטע המוקדם' },
      moved: { label: 'הוזז', hint: 'הושמט במקום אחד ונוסף במקום אחר' },
      form: { label: 'צורה אחרת', hint: 'אותו ערך, בתחילית, סיומת או נטייה אחרת' },
      spelling: { label: 'כתיב', hint: 'אותה מילה, בכתיב מלא או חסר (ו / י)' },
    },
    tooDifferent: 'שונים מדי לסימון מילה במילה.',
    tooDifferentShare: (share: number) =>
      `שונים מדי לסימון מילה במילה (${Math.round(share * 100)}% מהמילים שומרות על הערך).`,
    keepShare: (share: number) => `${Math.round(share * 100)}% מהמילים שומרות על הערך; A נקרא כקטע המוקדם.`,
    loadFailed: 'לא ניתן לטעון את השינויים.',
    aligning: 'מיישר מילים…',
  },

  hit: {
    phraseTitle: (n: number, score: string) => `צירוף משותף מיושר: ${n} ערכים, ציון ${score}`,
    phrase: (n: number) => `צירוף · ${n}`,
    unpin: 'ביטול נעיצה',
    changes: 'שינויים',
    sharedWords: 'מילים משותפות',
    keepChanges: 'השארת השינויים מסומנים',
    keepShared: 'השארת המילים המשותפות מודגשות',
    compare: 'השוואה',
    compareTitle: 'השוואה זה לצד זה',
    moreVerses: (n: number) => ` … (${n} פסוקים)`,
    markBy: 'סימון מילים לפי',
  },

  lemmas: {
    finding: 'מחפש מילים משותפות…',
    none: 'אין ערכי תוכן משותפים.',
    shared: 'ערכים משותפים',
    strongs: (lemma: string, formula: boolean) => `סטרונג ${lemma}${formula ? ' (רק בתוך נוסחה חוזרת)' : ''}`,
    allVerses: (lemma: string) => `סטרונג ${lemma}: כל הפסוקים`,
    strongsTag: (lemma: string) => `סטרונג ${lemma}`,
  },

  word: {
    panel: 'ניתוח מילה',
    close: 'סגירה',
    unaligned: 'אין מילת OSHB המיושרת למילה הזאת.',
    verses: (n: number) => `${n} פסוקים`,
    clickHint: 'לחיצה על מילה מציגה את המורפולוגיה והקונקורדנציה שלה.',
    pause: 'הפסק',
    ketiv: 'כתיב',
  },

  link: {
    untyped: 'ללא סוג',
    verseTitle: (types: string) => `ספריא מקשרת בין הפסוקים (${types})`,
    passageTitle: (types: string) => `קישור של ספריא ברמת הקטע מכסה את הזוג (${types})`,
    verse: 'קישור בספריא',
    passage: 'קטע בספריא',
  },

  picker: {
    lookingUp: 'מחפש…',
    notRef: (q: string) => `לא הפניה: ${q}`,
    unreachable: 'אין גישה ל־API',
    booksFailed: 'לא ניתן לטעון את הספרים',
    unitsFailed: 'לא ניתן לטעון את היחידות',
    unitType: (label: string) => `${label}: סוג יחידה`,
    book: (label: string) => `${label}: ספר`,
    chapter: (label: string) => `${label}: פרק`,
    unit: (label: string) => `${label}: יחידה`,
    reference: (label: string) => `${label}: הפניה`,
    bookPlaceholder: 'ספר…',
    refPlaceholder: 'בראשית א · Gen 1:1',
    go: 'מעבר',
  },

  filter: {
    onlyTouching: 'רק אלה הנוגעים ב',
    showAll: 'הצגת הכול',
  },

  csv: { page: 'ייצוא העמוד (CSV)', all: 'ייצוא הכול (CSV)' },

  keypad: { label: 'מקלדת עברית', space: 'רווח', backspace: 'מחיקה' },

  cards: {
    phraseScore: 'ציון היישור: ערכים תואמים במשקל idf, פחות קנסות על פערים ואי־התאמות',
    lemmas: (n: number) => `${n} ערכים`,
    recursTitle: 'פסוקים החולקים בדיוק את רצף הערכים הזה',
    recurs: (n: number) => `חוזר ב־${n} פסוקים`,
    qTitle: 'השיעור הצפוי של שרשראות מקריות מבין השרשראות החזקות לפחות כמו זו (סדר הפסוקים מעורבב בתוך הפרקים)',
    chainScore: 'ציון השרשרת: משקלי הזוגות פחות עלויות הפערים',
    seqVerses: (n: number, direction?: string) =>
      `${n} פסוקים ${direction === 'reverse' ? 'בסדר הפוך' : direction === 'mixed' ? 'בסדר משתנה' : 'באותו סדר'}`,
    goldTitle: 'זוגות פסוקים מיושרים שספריא כבר מקשרת',
    notLinked: 'אין קישור בספריא',
    linksOf: (gold: number, n: number) => `ספריא מקשרת ${gold}/${n}`,
    sideBySide: 'זה לצד זה',
    wordplayKinds: {
      substitution: 'אות אחת הוחלפה',
      metathesis: 'אותיות התחלפו',
      extension: 'אות אחת נוספה',
    },
    adjacent: 'סמוכות',
    apart: (gap: number) => `במרחק ${gap} מילים`,
    wordplayScore: 'הנדירות הממוצעת (idf) של שתי המילים, פחות המרחק',
  },

  books: {
    title: 'עיון',
    lede: 'בחרו ספר, ואחר כך פרק, פרשה או פיסקה. כל יחידה מציגה את היחידות הדומות לה ביותר בניסוח, במשמעות או בשניהם.',
  },

  unit: {
    halvesTitle: 'חלוקת כל פסוק בהפסקים העיקריים (אתנחתא; עולה ויורד בתהלים, משלי ואיוב)',
    halves: 'צלעות הפסוק (טעמים)',
    clausesTitle: 'חלוקה גם בהפסקים החלשים (זקף, סגולתא, טפחא; רביע וצינור בשירה)',
    clauses: 'חלוקה עדינה יותר',
    loadingHalves: 'טוען את צלעות הפסוקים…',
    theHalves: 'צלעות הפסוקים',
    parallelHalves: '∥ מסמן פסוקים שצלעותיהם מקבילות כבשירה',
    shareOf: (share: number, type: string) => ` · ${Math.round(share * 100)}% ${unitTypesThis[type] ?? type}`,
    source: 'טקסט המקור',
    names: 'שמות: ',
    namesLabel: 'אנשים ומקומות',
    theNames: 'השמות ביחידה',
    nameTitle: (here: number | null, all: number) => `${here} כאן, ${all} בסך הכול`,
    network: (rank: number, of: number, type: string, partners: number, cross: number) =>
      `רשת ההדים: במקום ה־${rank} בהדים מבין ${of} ${unitTypesPlural[type] ?? type} · ${partners} הדים, ${Math.round(cross * 100)}% לספרים אחרים · `,
    community: (n: number) => `הקהילה שלו (${n})`,
    structure: 'מבנה: מסגרת, כיאזם, מילים מנחות',
    similar: 'יחידות דומות',
    similarOf: (type: string) => similarOf[type] ?? `${type} דומים`,
    keys: 'מקשים:',
    keysNext: 'התוצאה הבאה / הקודמת',
    keysMarked: ' (מילותיה מסומנות)',
    noResults: 'לא נותרו תוצאות אחרי הסינון.',
    sharedPhrases: 'צירופים משותפים',
    theSharedPhrases: 'הצירופים המשותפים',
    phrasesLede: 'פסוקים החולקים עם הפסוק הזה רצף מיושר של ערכים (למילים נדירות משקל רב יותר)',
    strongestShown: (n: number) => `; מוצגים ${n} החזקים ביותר`,
    wordplay: 'משחקי לשון',
    theWordplay: 'משחקי הלשון',
    wordplayLede: 'מילים בעלות צליל דומה הסמוכות זו לזו, הנדירות תחילה.',
    allHere: (n: number) => `כל ה־${n} כאן`,
    inWordplay: 'ברשימת משחקי הלשון',
    runs: 'רצפים מקבילים',
    runsLabel: 'רצפים מקבילים',
    theSequences: 'הרצפים המקבילים',
    runsLede: (q: number) => `קטעים ההולכים בעקבות הקטע הזה פסוק אחר פסוק באותו סדר (q ≤ ${q}).`,
    inSequences: 'ברשימת הרצפים',
    acrostic: 'אקרוסטיכון',
    acrosticLetters: (n: number, first: string, last: string) => `: ${n} אותיות לפי סדר הא״ב, ${first}–${last}`,
    skipped: (n: number) => ` (${n} חסרות)`,
    peAyin: ', פ לפני ע',
    markLetters: 'סימון האותיות',
    allAcrostics: 'כל האקרוסטיכונים',
    nextVerseTitle: (p: string) => `מקביל לפסוק הבא (בית אחד על פני שני פסוקים): p = ${p}`,
    halvesTip: (p: string, cos: string, shared: number | null, shape: string, balance: string) =>
      `צלעות מקבילות: p = ${p} · משמעות ${cos} · ערכים משותפים ${shared} · דקדוק ${shape} · איזון ${balance}`,
    previous: '→ הקודם',
    next: 'הבא ←',
  },

  search: {
    title: 'חיפוש',
    book: 'ספר',
    allBooks: 'כל הספרים',
    hint: 'קלט מנוקד או לא מנוקד; ההתאמה המילולית מסירה תחיליות (ו ה ב כ ל מ ש).',
    encoderFailed: (err: string) => `טעינת המקודד הסמנטי בשרת נכשלה (${err}); זמין רק חיפוש מילולי.`,
    searchLexically: 'חיפוש מילולי',
    encoderLoading: (mode: string) =>
      `המקודד הסמנטי עדיין נטען בשרת; חיפוש ${mode} יענה ברגע שיהיה מוכן (החיפוש המילולי כבר עובד).`,
    reference: 'הפניה:',
    notRef: 'לא הפניה; חיפוש חופשי דורש אותיות עבריות.',
    waiting: 'ממתין למקודד הסמנטי…',
    searching: 'מחפש…',
    normalized: 'מנורמל:',
    terms: 'מונחים מילוליים:',
    noMatches: 'אין התאמות.',
    placeholder: 'חיפוש בתנ״ך… או הפניה: בראשית א א',
    inputLabel: 'טקסט עברי לחיפוש או הפניה',
    submit: 'חיפוש',
    hideKeyboard: 'הסתרת המקלדת',
    showKeyboard: 'מקלדת עברית',
  },

  compare: {
    title: 'השוואה',
    lede: 'כל פסוק מוצמד לפסוק הדומה לו ביותר ביחידה האחרת (קוסינוס של השיכונים הסמנטיים). העבירו את העכבר מעל פסוק כדי לראות את בן זוגו ואת המילים המשותפות.',
    swap: 'החלפת A ו־B',
    choose: 'בחרו שתי יחידות, או השתמשו ב„השוואה” בכל תוצאה.',
    bmaHint: '½ (ממוצע הקוסינוס הטוב ביותר A→B + ממוצע הקוסינוס הטוב ביותר B→A)',
    lowHigh: 'נמוך ← גבוה',
    cosine: 'קוסינוס',
    changes: 'שינויים מ־A ל־B',
    unitSide: (side: string) => `יחידה ${side}`,
    bestIn: (label: string) => `ההתאמה הטובה ביותר ב${label}`,
  },

  concordance: {
    occurrences: (words: number, verses: number, books: number) =>
      `${num(words)} מופעים ב־${num(verses)} פסוקים, ${books} ספרים.`,
    byBook: 'לפי ספר',
    allBooks: 'הצגת כל הספרים',
    onlyBook: 'רק הספר הזה',
    verses: 'פסוקים',
    versesIn: (book: string) => `פסוקים ב${book}`,
  },
  par: parHe,
  pat: patHe,
  dom: domHe,
  sen: senHe,
  dat: datHe,
  lab: labHe,
  syn: synHe,
  bor: borHe,
  ov: ovHe,
}
