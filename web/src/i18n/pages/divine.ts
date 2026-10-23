// Interface strings of the divine names page (DESIGN.md §16.65): each chapter's mix of יהוה and
// אלהים, the books whose mix changes, the Elohistic Psalter and the doubled psalms. English
// first, Hebrew typed against it. The names themselves are Hebrew in both.

import type { DivineName } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

/** The names as the text writes them (scripture: the same in both interfaces). */
const NAMES: Record<DivineName, string> = {
  yhwh: 'יהוה',
  elohim: 'אלהים',
  adonai: 'אדני',
  el: 'אל',
  eloah: 'אלוה',
  shaddai: 'שדי',
  yah: 'יה',
  elyon: 'עליון',
  tsevaot: 'צבאות',
}
const pct = (x: number, locale: string) => `${Math.round(x * 100).toLocaleString(locale)}%`
const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const dvEn = {
  title: 'Names of God',
  lede: 'Which name of God each chapter uses: \u2068יהוה\u2069, \u2068אלהים\u2069, \u2068אדני\u2069, \u2068אל\u2069, \u2068אלוה\u2069, \u2068שדי\u2069, \u2068יה\u2069, \u2068עליון\u2069 and \u2068צבאות\u2069, counted from the lemmas. The strip below colours every chapter by the mix of the two commonest, and each book is cut where its mix changes most.',
  names: NAMES,
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  elohistic: {
    title: 'The Elohistic Psalter, found without being named',
    notSplit: 'Psalms was not split in this build.',
    text: (first: number, last: number, named: [number, number], shares: number[], p: number) =>
      `Cut in three where the mix of \u2068יהוה\u2069 and \u2068אלהים\u2069 changes most, Psalms falls into 1–${numEn(first - 1)}, ${numEn(first)}–${numEn(last)} and ${numEn(last + 1)}–150, with \u2068יהוה\u2069 ${shares.map((s) => pct(s, 'en-US')).join(', ')} of the two. The middle part named in advance is ${numEn(named[0])}–${numEn(named[1])}; against the same cut of the psalms shuffled, p ${fp(p)}.`,
  },
  doubled: {
    title: 'The doubled psalms',
    text: (eWard: number, yWard: number, p: number, n: number) =>
      `In ${countEn(n, 'psalm found twice', 'psalms found twice')}, aligned word by word: the copy inside Psalms 42–83 has \u2068אלהים\u2069 where the other has \u2068יהוה\u2069 ${countEn(eWard, 'time', 'times')}, and the reverse ${countEn(yWard, 'time', 'times')} (sign test, p ${fp(p)}).`,
    missing: (refs: string) => `Not in this corpus: ${refs}.`,
  },
  stripTitle: 'Across the canon',
  stripHint: 'Each square is a chapter, coloured by \u2068יהוה\u2069’s share of \u2068יהוה\u2069 and \u2068אלהים\u2069; a bar marks a cut where a book’s mix changes beyond chance (q ≤ 0.05). Select a chapter to read it with the names marked.',
  legend: { label: 'Legend', allE: 'all \u2068אלהים\u2069', even: 'even', allY: 'all \u2068יהוה\u2069', none: 'neither name' },
  chapterTitle: (label: string, y: number, e: number, other: number) =>
    `${label}: \u2068יהוה\u2069 ${numEn(y)}, \u2068אלהים\u2069 ${numEn(e)}${other ? `, other names ${numEn(other)}` : ''}`,
  stripLabel: (book: string) => `${book}: chapters by the mix of the names`,
  booksTitle: 'Books',
  cols: {
    book: 'Book',
    chapters: 'Chapters',
    yhwh: '\u2068יהוה\u2069',
    elohim: '\u2068אלהים\u2069',
    other: 'Other names',
    share: '\u2068יהוה\u2069’s share',
    split: 'Cut at chapters',
    shares: 'Shares by part',
    p: 'p',
    q: 'q',
    chapter: 'Chapter',
    words: 'Words',
    names: 'Names',
    part: 'Part',
  },
  notSplit: '—',
  split: (a: number, b: number) => `${numEn(a)}, ${numEn(b)}`,
  showBook: (book: string) => `The chapters of ${book}`,
  allBooks: 'All books',
  chaptersTitle: (book: string) => `${book}, chapter by chapter`,
  pairsTitle: 'The doubled psalms, name by name',
  pairHead: (e: string, y: string) => `${e} and ${y}`,
  pairCounts: (eWard: number, yWard: number, same: number) =>
    `\u2068אלהים\u2069 for \u2068יהוה\u2069 ${numEn(eWard)}, the reverse ${numEn(yWard)}, the same name ${numEn(same)}`,
  kinds: { e_ward: '\u2068אלהים\u2069 for \u2068יהוה\u2069', y_ward: '\u2068יהוה\u2069 for \u2068אלהים\u2069', same: 'the same', other: 'another name' } as Record<string, string>,
  placeCols: { inside: 'Inside 42–83', outside: 'Its double', kind: 'Change' },
  absent: '(no word)',
  totals: (n: number) => `${countEn(n, 'name', 'names')} in all`,
  method:
    'A word counts for the name of its OSHB lemma (\u2068יהוה\u2069 also where it is pointed as \u2068אלהים\u2069; \u2068אלהים\u2069 also where it means gods, which the lemma does not tell apart). A book with at least 20 of the two names and 9 chapters is cut in three runs of at least 3 chapters where a single rate fits worst, and the gain is set against the best cut of its chapters shuffled 999 times; q corrects for the books tested. The doubled psalms are aligned as the Changes page aligns parallels.',
  notComputed: 'The divine names were not computed in this build: run `bsim divine`, then `bsim build-db`.',
}

export const dvHe: typeof dvEn = {
  title: 'שמות האל',
  lede: 'באיזה שם של האל משתמש כל פרק: יהוה, אלהים, אדני, אל, אלוה, שדי, יה, עליון וצבאות, נמנים לפי הערכים המילוניים. הרצועה שלמטה צובעת כל פרק לפי התמהיל של שני השמות השכיחים, וכל ספר נחתך במקום שבו התמהיל שלו משתנה יותר מכול.',
  names: NAMES,
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'מתאשר',
  fails: 'אינו מתאשר',
  elohistic: {
    title: 'ספר התהלים האלוהיסטי, נמצא בלי שנאמר היכן',
    notSplit: 'ספר תהלים לא נחתך בבנייה הזו.',
    text: (first: number, last: number, named: [number, number], shares: number[], p: number) =>
      `כשהוא נחתך לשלושה במקום שבו התמהיל של יהוה ואלהים משתנה יותר מכול, ספר תהלים מתחלק ל־1–${numHe(first - 1)}, ${numHe(first)}–${numHe(last)} ו־${numHe(last + 1)}–150, ושיעור יהוה מבין השניים ${shares.map((s) => pct(s, 'he-IL')).join(', ')}. החלק האמצעי שנקבע מראש הוא ${numHe(named[0])}–${numHe(named[1])}; מול אותו חיתוך של המזמורים בסדר מעורבב, p ${fp(p)}.`,
  },
  doubled: {
    title: 'המזמורים הכפולים',
    text: (eWard: number, yWard: number, p: number, n: number) =>
      `ב${countHe(n, 'מזמור אחד שמופיע פעמיים', 'שני מזמורים שמופיעים פעמיים', 'מזמורים שמופיעים פעמיים')}, מיושרים מילה מול מילה: בעותק שבתוך תהלים מב–פג כתוב אלהים במקום שבו בעותק השני כתוב יהוה ${countHe(eWard, 'פעם אחת', 'פעמיים', 'פעמים')}, וההפך ${countHe(yWard, 'פעם אחת', 'פעמיים', 'פעמים')} (מבחן הסימן, p ${fp(p)}).`,
    missing: (refs: string) => `אינם בקורפוס הזה: ${refs}.`,
  },
  stripTitle: 'לאורך המקרא',
  stripHint: 'כל ריבוע הוא פרק, צבוע לפי שיעור יהוה מבין יהוה ואלהים; קו מסמן חיתוך שבו התמהיל של ספר משתנה מעבר למקרה (q ≤ 0.05). בחרו פרק כדי לקרוא אותו כשהשמות מסומנים.',
  legend: { label: 'מקרא', allE: 'כולו אלהים', even: 'שווה בשווה', allY: 'כולו יהוה', none: 'אף אחד מהשמות' },
  chapterTitle: (label: string, y: number, e: number, other: number) =>
    `${label}: יהוה ${numHe(y)}, אלהים ${numHe(e)}${other ? `, שמות אחרים ${numHe(other)}` : ''}`,
  stripLabel: (book: string) => `${book}: הפרקים לפי תמהיל השמות`,
  booksTitle: 'ספרים',
  cols: {
    book: 'ספר',
    chapters: 'פרקים',
    yhwh: 'יהוה',
    elohim: 'אלהים',
    other: 'שמות אחרים',
    share: 'שיעור יהוה',
    split: 'נחתך בפרקים',
    shares: 'שיעור בכל חלק',
    p: 'p',
    q: 'q',
    chapter: 'פרק',
    words: 'מילים',
    names: 'שמות',
    part: 'חלק',
  },
  notSplit: '—',
  split: (a: number, b: number) => `${numHe(a)}, ${numHe(b)}`,
  showBook: (book: string) => `פרקי ${book}`,
  allBooks: 'כל הספרים',
  chaptersTitle: (book: string) => `${book}, פרק אחר פרק`,
  pairsTitle: 'המזמורים הכפולים, שם אחר שם',
  pairHead: (e: string, y: string) => `${e} ו־${y}`,
  pairCounts: (eWard: number, yWard: number, same: number) =>
    `אלהים במקום יהוה ${numHe(eWard)}, ההפך ${numHe(yWard)}, אותו שם ${numHe(same)}`,
  kinds: { e_ward: 'אלהים במקום יהוה', y_ward: 'יהוה במקום אלהים', same: 'אותו שם', other: 'שם אחר' },
  placeCols: { inside: 'בתוך מב–פג', outside: 'הכפיל שלו', kind: 'שינוי' },
  absent: '(אין מילה)',
  totals: (n: number) => `${countHe(n, 'שם אחד', 'שני שמות', 'שמות')} בסך הכול`,
  method:
    'מילה נמנית לשם של הערך המילוני שלה ב־OSHB (יהוה גם כשהוא מנוקד כאלהים; אלהים גם כשפירושו אלים, שהערך אינו מבחין בו). ספר שיש בו לפחות 20 מופעים של שני השמות ו־9 פרקים נחתך לשלושה רצפים של 3 פרקים לפחות, במקום שבו שיעור אחד מתאים הכי פחות, והרווח נבחן מול החיתוך הטוב ביותר של פרקיו בסדר מעורבב 999 פעמים; q מתקן לריבוי הספרים שנבדקו. המזמורים הכפולים מיושרים כמו שעמוד השינויים מיישר מקבילות.',
  notComputed: 'שמות האל לא חושבו בבנייה הזו: הריצו `bsim divine` ואז `bsim build-db`.',
}
