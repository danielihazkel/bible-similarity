// The Hebrew half of `../dialogue.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { dlgEn, fp, pct, x1 } from '../dialogue'
import type { Src } from '../dialogue'

export const dlgHe: typeof dlgEn = {
  lede: 'אל מי נאמר כל ציטוט? הפסוקית המציגה אומרת זאת פעמים רבות (ויאמר יהוה אל משה). אחרת הציטוט עשוי לקרוא למישהו בשמו (פנייה). הפסוקית המציגה עשויה לומר רק „אליו”, וזה מתפרש כצד השני של השיחה. ואם אינה אומרת דבר (ויאמר), הציטוט מתפרש כתשובה למי שדיבר ממש לפני כן. מכאן: מי מדבר אל מי בכל ספר, השיחות בין שני דוברים, ושלוש בדיקות שנקבעו לפני ההרצה הראשונה.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim syntax`, `bsim dialogue`, ואחר כך `bsim build-db`.',
  summary: (q: number, found: number, by: Record<Src, number>) =>
    `${numHe(q)} ציטוטים; נמען נמצא ל־${numHe(found)}: נקוב בפסוקית המציגה ${numHe(by.explicit)}, נקרא בשמו ${numHe(by.vocative)}, „אליו” כצד השני ${numHe(by.pronoun)}, תשובה לדובר הקודם ${numHe(by.turn)}.`,
  handCheck: (h: Record<Src, [number, number]>) =>
    `בדיקה ידנית של 50 ציטוטים שנבחרו אחרי שנקבעו הכללים: נקוב ${h.explicit[0]} / ${h.explicit[1]}, נקרא בשמו ${h.vocative[0]} / ${h.vocative[1]}, „אליו” ${h.pronoun[0]} / ${h.pronoun[1]}, תשובה ${h.turn[0]} / ${h.turn[1]}. הבדיקות שלהלן משתמשות בשני הראשונים בלבד; כל הנמענים יחד הם בדיקת הרגישות.`,
  sources: { explicit: 'נקוב', vocative: 'נקרא בשמו', pronoun: '„אליו”', turn: 'תשובה' },
  checksTitle: 'בדיקות שנקבעו מראש',
  verdict: { holds: 'מתקיימת', fails: 'אינה מתקיימת' },
  deference: (up: number, rest: number, count: number, of: number, obs: number, nul: number | null, p: number | null) =>
    `„עבדך” (או „אמתך”, „שפחתך”) בדיבור אל האל או אל מלך: ${up.toFixed(1)} פעמים לכל 1,000 מילים (${numHe(count)} ב־${numHe(of)} מילים), לעומת ${rest.toFixed(1)} בדיבור אל כל אחד אחר. בהשוואה בתוך כל ספר ההפרש ${obs.toFixed(1)}, לעומת ${x1(nul)} כשהסימון „כלפי מעלה” מעורבב בין הציטוטים של כל ספר (p ${fp(p)}). תשובה ידועה: כבוד כלפי מי שמעליך (Revell 1996).`,
  particle: (up: number, rest: number, count: number, of: number, p: number | null) =>
    `„נא” מיד אחרי ציווי: ${pct(up)} מן הציוויים אל האל או אל מלך (${numHe(count)} מתוך ${numHe(of)}), לעומת ${pct(rest)} מן האחרים (בהשוואה בתוך כל ספר, p ${fp(p)}). שנוי במחלוקת: האם „נא” הוא סימן נימוס (Shulman 1996,‏ Christiansen 2009) או מילית לוגית, „אם כן” (Lambdin 1971)?`,
  knownOnly: 'נספרים רק ציטוטים שדוברם ידוע: לתפילה שאין בה דובר נקוב אין מעמד להשוות.',
  lastWord: (obs: number, n: number, exp: number, p: number) =>
    `ב־${numHe(n)} שיחות בין האל או מלך לבין מי שמעמדו נמוך ממנו, העליון מדבר אחרון ב־${numHe(obs)}, לעומת ${exp.toFixed(1)} אילו התור האחרון היה תור מקרי מתורי השיחה (p ${fp(p)}). שאלה פתוחה.`,
  sensitivity: (d: number, dp: number | null, pr: number, pp: number | null) =>
    `עם כל הנמענים, בכל דרך שנמצאו: „עבדך” ${d.toFixed(1)} יותר לכל 1,000 מילים (p ${fp(dp)}); „נא” ב־${pct(pr)} יותר מן הציוויים (p ${fp(pp)}).`,
  described: (opens: number, n: number, exp: number, p: number, longer: number, shorter: number, mh: number | null, ml: number | null, lp: number | null) =>
    `תיאור, בלי הכרעה: העליון פותח ${numHe(opens)} מתוך ${numHe(n)} השיחות (${exp.toFixed(1)} צפויות, p ${fp(p)}); תוריו ארוכים יותר ב־${numHe(longer)} וקצרים יותר ב־${numHe(shorter)} (חציון ${x1(mh)} לעומת ${x1(ml)} מילים לתור; מבחן הסימן p ${fp(lp)}).`,
  booksTitle: 'מי מדבר אל מי',
  book: 'ספר',
  bookOption: (name: string, q: number) => `${name} (${numHe(q)})`,
  network: (book: string) => `שיחות ב${book}`,
  networkLabel: (n: number, book: string) => `${numHe(n)} הדוברים הפעילים ביותר ב${book} ואל מי הם מדברים; אותם זוגות מפורטים בטבלה שלהלן.`,
  pairsTitle: (book: string) => `זוגות ב${book}`,
  cols: { speaker: 'דובר', addressee: 'אל', quotes: 'ציטוטים', words: 'מילים', named: 'נקוב או נקרא' },
  pairTitle: (s: string, a: string, n: number) => `${s} ← ${a}: ${countHe(n, 'ציטוט אחד', 'שני ציטוטים', 'ציטוטים')}`,
  filterParty: (who: string) => `הצגת השיחות של ${who}`,
  noPairs: 'לא נמצא דיבור עם נמען בספר זה.',
  exchangesTitle: 'שיחות',
  exchangesLede: 'רצפים של תורי דיבור שהמספר מציג, בין שני דוברים שמדברים שניהם; דובר שלישי, או תור המופנה אל מישהו אחר, מסיימים שיחה.',
  unequal: 'רק האל או מלך עם מי שמעמדו נמוך ממנו',
  party: (who: string) => `עם ${who}`,
  allParties: 'כל אחד',
  count: (n: number) => countHe(n, 'שיחה אחת', 'שתי שיחות', 'שיחות'),
  turns: (n: number, a: string, an: number, b: string, bn: number) =>
    `${countHe(n, 'תור אחד', 'שני תורים', 'תורים')}: ${a} ${numHe(an)}, ${b} ${numHe(bn)}`,
  last: (who: string) => `המילה האחרונה: ${who}`,
  read: 'קריאה עם הדוברים',
  empty: 'אין שיחות מתאימות.',
  god: 'האל',
}
