// Interface strings of the Divisions page: where the text turns, and where the tradition divided
// it (DESIGN.md §16.29). English first, Hebrew typed against it.

import type { Paragraph, SegmentKind } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const he = (k: Paragraph) => (k === 'pe' ? 'פ' : 'ס')

export const divEn = {
  title: 'Where the text divides',
  lede: (w: number) =>
    `Every boundary between two verses gets a score from the text alone: how much the words (lemmas) and the meaning (verse embeddings) of the ${w} verses before it differ from the ${w} after it, as a percentile within its book. 0.5 is a typical boundary; near 1 are the book's sharpest turns. The divisions the tradition drew are then placed on it: the open (פ) and closed (ס) paragraphs of two manuscript traditions, the chapters (added in the 13th century), the weekly parashot and the style seams.`,
  noData: 'Not computed in this build: run `bsim segments`, then `bsim build-db`.',
  tests: 'Do the divisions follow the text?',
  testsLede:
    'The mean score of the boundaries of each kind, against the same number of boundaries drawn at random in each book (999 draws); p is the share of draws scoring as high. Words and meaning: the two signals alone.',
  cols: { kind: 'Division', n: 'Boundaries', score: 'Score', lex: 'Words', sem: 'Meaning', p: 'p' },
  groups: {
    mam_pe: 'Open paragraph פ (MAM)',
    mam_samekh: 'Closed paragraph ס (MAM)',
    oshb_pe: 'Open paragraph פ (Leningrad)',
    oshb_samekh: 'Closed paragraph ס (Leningrad)',
    agreed: 'A break in both traditions',
    single: 'A break in one tradition only',
    chapter_break: 'Chapter start at a paragraph break',
    chapter_only: 'Chapter start with no paragraph break',
    parasha: 'Start of a weekly parasha',
    seam: 'Style seam',
    unmarked: 'No division',
  } as Record<string, string>,
  peSamekh: (a: string, b: string, p: string) =>
    `Open paragraphs (פ) score ${a}, closed ones (ס) ${b}; with the two labels shuffled among them in each book, p ${p}.`,
  agreedSingle: (a: string, b: string, p: string) =>
    `Breaks that both traditions mark score ${a}, breaks only one of them marks ${b}; p ${p}.`,
  chapter: (a: string, b: string, p: string) =>
    `Chapters that start at a paragraph break score ${a}, chapters that start without one ${b}; p ${p}.`,
  seams: (share: number, nul: number, near: number, p: string) =>
    `${pct(share)} of the style seams lie within ${countEn(near, 'verse', 'verses')} of a paragraph break or a chapter start, against ${pct(nul)} of random boundaries (p ${p}).`,
  agreement: (ref: 'mam' | 'chapter', better: number, books: number, pk: string, pkNull: string) =>
    `As a segmentation: a book's sharpest turns, as many as its ${ref === 'mam' ? 'MAM paragraph breaks' : 'chapters'}, match them better than random boundaries in ${numEn(better)} of ${numEn(books)} books (mean Pk ${pk} against ${pkNull}; lower is closer).`,
  calibration: (score: string, p: string) =>
    `Check of the test: the MAM breaks shuffled inside each book score ${score} (p ${p}), as chance should.`,
  window: (w: number, grid: string) =>
    `Window: ${countEn(w, 'verse', 'verses')} on each side, chosen on the dev books (mean score of the MAM breaks by window: ${grid}).`,
  caveat:
    'Cohesion is one reason to divide a text, not the only one: a list is divided item by item, a reading by the calendar, and a window several verses wide blurs a turn by a verse or two. A low score does not make a division wrong.',
  book: 'Book',
  chapter_: 'Chapter',
  allChapters: 'All chapters',
  bookTitle: 'One book',
  pickBook: 'Choose a book to see the score of each of its boundaries and where its divisions fall.',
  chart: (book: string) => `The score of every boundary in ${book}, with its divisions`,
  legend: { pe: 'Open פ (MAM)', samekh: 'Closed ס (MAM)', chapter: 'Chapter start', other: 'No paragraph break' },
  bookAgreement: (ref: 'mam' | 'chapter', pk: string, pkNull: string, p: string) =>
    `${ref === 'mam' ? 'MAM paragraphs' : 'Chapters'}: Pk ${pk} against ${pkNull} for random boundaries (p ${p}).`,
  bar: (label: string, score: string) => `${label}: score ${score}`,
  listTitle: 'Where the text and the divisions disagree',
  kinds: {
    turn: {
      label: 'Unmarked turns',
      hint: "A book's sharpest turns (score ≥ 0.97) with no paragraph break or chapter within a verse",
    },
    cut: {
      label: 'Chapters in running text',
      hint: 'Chapter starts with no paragraph break in either tradition, where the text runs on (score ≤ 0.25)',
    },
    quiet: {
      label: 'Quiet paragraph breaks',
      hint: 'MAM paragraph breaks where the text hardly changes (score ≤ 0.05): often a list divided item by item',
    },
  } satisfies Record<SegmentKind, { label: string; hint: string }>,
  anyKind: 'Every kind',
  none: 'None here.',
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'boundary', 'boundaries')} · page ${numEn(page)} of ${numEn(pages)}`,
  score: (s: string) => `score ${s}`,
  scoreTitle: "Within-book percentile of the drop in cohesion (1 = the book's sharpest turn)",
  tags: {
    mam: (k: Paragraph) => `MAM ${he(k)}`,
    oshb: (k: Paragraph) => `Leningrad ${he(k)}`,
    chapter: 'chapter start',
    seam: 'style seam',
  },
  boundary: 'the boundary',
}

export const divHe: typeof divEn = {
  title: 'היכן הטקסט מתחלק',
  lede: (w: number) =>
    `כל גבול בין שני פסוקים מקבל ציון מן הטקסט עצמו: עד כמה המילים (הלמות) והמשמעות (וקטורי הפסוקים) של ${numHe(w)} הפסוקים שלפניו שונות מאלה של ${numHe(w)} הפסוקים שאחריו, כאחוזון בתוך ספרו. 0.5 הוא גבול רגיל; קרוב ל־1 הם המפנים החדים ביותר בספר. על הציון הזה מונחות החלוקות שקבעה המסורת: הפרשות הפתוחות (פ) והסתומות (ס) בשתי מסורות כתב יד, הפרקים (שנוספו במאה ה־13), פרשות השבוע ותפרי הסגנון.`,
  noData: 'לא חושב בבנייה זו: הריצו `bsim segments` ואחר כך `bsim build-db`.',
  tests: 'האם החלוקות הולכות אחר הטקסט?',
  testsLede:
    'הציון הממוצע של הגבולות מכל סוג, לעומת אותו מספר גבולות שנבחרו באקראי בכל ספר (999 הגרלות); p הוא חלק ההגרלות שהגיעו לציון גבוה כזה. מילים ומשמעות: כל אחד משני הסימנים לבדו.',
  cols: { kind: 'חלוקה', n: 'גבולות', score: 'ציון', lex: 'מילים', sem: 'משמעות', p: 'p' },
  groups: {
    mam_pe: 'פרשה פתוחה פ (מקרא על פי המסורה)',
    mam_samekh: 'פרשה סתומה ס (מקרא על פי המסורה)',
    oshb_pe: 'פרשה פתוחה פ (כתב יד לנינגרד)',
    oshb_samekh: 'פרשה סתומה ס (כתב יד לנינגרד)',
    agreed: 'הפסקה בשתי המסורות',
    single: 'הפסקה במסורת אחת בלבד',
    chapter_break: 'תחילת פרק בהפסקת פרשה',
    chapter_only: 'תחילת פרק בלי הפסקת פרשה',
    parasha: 'תחילת פרשת שבוע',
    seam: 'תפר סגנוני',
    unmarked: 'ללא חלוקה',
  },
  peSamekh: (a: string, b: string, p: string) =>
    `פרשות פתוחות (פ) מקבלות ${a}, סתומות (ס) ${b}; כשמערבבים את שתי התוויות ביניהן בתוך כל ספר, p ${p}.`,
  agreedSingle: (a: string, b: string, p: string) =>
    `הפסקות ששתי המסורות מסמנות מקבלות ${a}, הפסקות שרק אחת מהן מסמנת ${b}; p ${p}.`,
  chapter: (a: string, b: string, p: string) =>
    `פרקים שמתחילים בהפסקת פרשה מקבלים ${a}, פרקים שמתחילים בלעדיה ${b}; p ${p}.`,
  seams: (share: number, nul: number, near: number, p: string) =>
    `${pct(share)} מתפרי הסגנון נמצאים בטווח ${countHe(near, 'פסוק אחד', 'שני פסוקים', 'פסוקים')} מהפסקת פרשה או מתחילת פרק, לעומת ${pct(nul)} מגבולות אקראיים (p ${p}).`,
  agreement: (ref: 'mam' | 'chapter', better: number, books: number, pk: string, pkNull: string) =>
    `כחלוקה: המפנים החדים ביותר בספר, כמספר ${ref === 'mam' ? 'הפסקות הפרשה שבו' : 'פרקיו'}, תואמים ${ref === 'mam' ? 'להן' : 'להם'} טוב יותר מגבולות אקראיים ב־${numHe(better)} מתוך ${numHe(books)} ספרים (Pk ממוצע ${pk} לעומת ${pkNull}; נמוך יותר קרוב יותר).`,
  calibration: (score: string, p: string) =>
    `בדיקת המבחן: הפסקות הפרשה מעורבבות בתוך כל ספר מקבלות ${score} (p ${p}), כצפוי ממקריות.`,
  window: (w: number, grid: string) =>
    `חלון: ${countHe(w, 'פסוק אחד', 'שני פסוקים', 'פסוקים')} מכל צד, נבחר על ספרי הפיתוח (הציון הממוצע של הפסקות הפרשה לפי חלון: ${grid}).`,
  caveat:
    'לכידות היא סיבה אחת לחלק טקסט ולא היחידה: רשימה מחולקת פריט אחר פריט, קריאה לפי לוח השנה, וחלון רחב של כמה פסוקים מטשטש מפנה בפסוק או שניים. ציון נמוך אינו הופך חלוקה לשגויה.',
  book: 'ספר',
  chapter_: 'פרק',
  allChapters: 'כל הפרקים',
  bookTitle: 'ספר אחד',
  pickBook: 'בחרו ספר כדי לראות את הציון של כל גבול בו והיכן נופלות חלוקותיו.',
  chart: (book: string) => `הציון של כל גבול ב${book}, עם החלוקות`,
  legend: { pe: 'פתוחה פ (מקרא על פי המסורה)', samekh: 'סתומה ס (מקרא על פי המסורה)', chapter: 'תחילת פרק', other: 'ללא הפסקת פרשה' },
  bookAgreement: (ref: 'mam' | 'chapter', pk: string, pkNull: string, p: string) =>
    `${ref === 'mam' ? 'פרשות' : 'פרקים'}: Pk ${pk} לעומת ${pkNull} לגבולות אקראיים (p ${p}).`,
  bar: (label: string, score: string) => `${label}: ציון ${score}`,
  listTitle: 'היכן הטקסט והחלוקות חלוקים',
  kinds: {
    turn: {
      label: 'מפנים לא מסומנים',
      hint: 'המפנים החדים ביותר בספר (ציון 0.97 ומעלה) בלי הפסקת פרשה או פרק בטווח פסוק',
    },
    cut: {
      label: 'פרקים בתוך טקסט רציף',
      hint: 'תחילות פרקים בלי הפסקת פרשה באף אחת מהמסורות, במקום שהטקסט נמשך (ציון 0.25 ומטה)',
    },
    quiet: {
      label: 'הפסקות פרשה שקטות',
      hint: 'הפסקות פרשה במקרא על פי המסורה במקום שהטקסט כמעט אינו משתנה (ציון 0.05 ומטה): לעתים קרובות רשימה המחולקת פריט אחר פריט',
    },
  },
  anyKind: 'כל הסוגים',
  none: 'אין כאן.',
  page: (total: number, page: number, pages: number) =>
    `${countHe(total, 'גבול אחד', 'שני גבולות', 'גבולות')} · עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  score: (s: string) => `ציון ${s}`,
  scoreTitle: 'אחוזון בתוך הספר של הירידה בלכידות (1 = המפנה החד ביותר בספר)',
  tags: {
    mam: (k: Paragraph) => `מקרא על פי המסורה ${he(k)}`,
    oshb: (k: Paragraph) => `לנינגרד ${he(k)}`,
    chapter: 'תחילת פרק',
    seam: 'תפר סגנוני',
  },
  boundary: 'הגבול',
}
