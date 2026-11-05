// The Hebrew half of `../citations.ts` (loaded with the Hebrew interface only).
import { countHe, numHe, pct } from '../../fmt'
import { citEn, fp } from '../citations'

export const citHe: typeof citEn = {
  title: 'הפניות',
  lede: 'יש פסוקים שאומרים שהם חוזרים על טקסט אחר או מקיימים אותו: "ככתוב בספר תורת משה", "כדבר יהוה אשר דבר ביד עבדו", "כאשר צוה יהוה את משה". לכל אחד מהם המקור מבוקש בין הטקסטים שהוא יכול להפנות אליהם (התורה, או כל מה שקודם לו) לפי מילותיו ולפי משמעותו. מקור נחשב מזוהה כששני החיפושים מסכימים עליו.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim citations` ואחר כך `bsim build-db`.',
  summary: (n: number, resolved: number) =>
    `${countHe(n, 'פסוק אחד עם נוסחת הפניה', 'שני פסוקים עם נוסחת הפניה', 'פסוקים עם נוסחת הפניה')}; ל־${numHe(resolved)} מהם זוהה מקור אחד.`,
  families: {
    written: { label: 'ככתוב', hint: 'ככתוב, ככל הכתוב, כתוב בספר: המקור מבוקש בתורה' },
    word: { label: 'הדבר שהתקיים', hint: 'דבר יהוה אשר דבר (ביד …): המקור מבוקש בכל מה שקודם' },
    command: { label: 'כאשר צוה', hint: 'כאשר צוה יהוה את משה: המקור מבוקש בתורה' },
  },
  familyLine: (label: string, k: number, n: number, share: number, nul: number, p: number | null) =>
    `${label}: ${numHe(k)} מתוך ${numHe(n)} זוהו (${pct(share)}), לעומת ${pct(nul)} מפסוקים אקראיים מאותם ספרים (p ${fp(p)}).`,
  familyNote:
    'ההתאמה הטובה ביותר כשלעצמה מוכיחה מעט: כמעט כל פסוק מוצא פסוק קרוב מבין עשרת אלפים, כי הטקסט חוזר על נוסחאותיו. לכן כל משפחה נמדדת מול פסוקים אקראיים הכפופים לאותם כללים. משפחה שאינה עולה עליהם מפנה ברוב המקרים לחוק או להבטחה באופן כללי, ולא לפסוק אחד.',
  gold: (top1: number, found: number, topK: number, k: number, right: number, resolved: number) =>
    `בדיקה: מתוך ${countHe(found, 'הפניה אחת', 'שתי הפניות', 'הפניות')} שהמחקר מצביע על מקורן, ${numHe(top1)} מוצאות אותו ראשון ו־${numHe(topK)} בין ${numHe(k)} הטובים; ${numHe(right)} מתוך ${numHe(resolved)} המזוהות נכונות.`,
  lag: (verses: number) => `דבר שהתקיים בא בחציון ${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')} אחרי מקורו.`,
  booksTitle: 'מי מפנה אל מי',
  booksLede: 'הפניות מזוהות לפי ספר: הכיוון היחיד בין קטעים שהטקסט עצמו מצהיר עליו.',
  bookPair: (a: string, b: string, n: number) => `${a} ← ${b}: ${numHe(n)}`,
  listTitle: 'כל ההפניות',
  filters: { family: 'נוסחה', any: 'הכול', resolved: 'מזוהות בלבד', book: 'ספר' },
  page: (total: number, page: number, pages: number) =>
    `${countHe(total, 'הפניה אחת', 'שתי הפניות', 'הפניות')} · עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  none: 'אין כאן הפניות.',
  resolvedTag: 'מזוהה',
  unresolvedTag: 'אין מקור יחיד',
  namedTag: (rank: number | null) => (rank == null ? 'המקור הידוע לא נמצא' : rank === 1 ? 'המקור הידוע נמצא' : `המקור הידוע במקום ${rank}`),
  source: 'מקור',
  others: 'מועמדים נוספים:',
  compare: 'השוואה',
}
