// The Hebrew half of `../divine.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { NAMES, dvEn, fp, pct } from '../divine'

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
