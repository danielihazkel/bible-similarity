// Interface strings of Who speaks → To whom: addressees, conversations and the three checks fixed
// in advance (DESIGN.md §16.44). English first, Hebrew typed against it.

import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x1 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(1))
const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)

type Src = 'explicit' | 'vocative' | 'pronoun' | 'turn'

export const dlgEn = {
  lede: 'Who is each quotation said to? The clause that introduces it often says (ויאמר יהוה אל משה); otherwise the quotation may call someone by name (a vocative), the introduction may say only “to him” (אליו), which is read as the other party of the conversation, or say nothing (ויאמר), which is read as an answer to whoever spoke just before. From these: who speaks to whom in each book, the exchanges between two speakers, and three checks fixed before the first run.',
  noData: 'Not computed in this build: run `bsim syntax`, `bsim dialogue`, then `bsim build-db`.',
  summary: (q: number, found: number, by: Record<Src, number>) =>
    `${numEn(q)} quotations; an addressee found for ${numEn(found)}: named in the introduction ${numEn(by.explicit)}, called by name ${numEn(by.vocative)}, “to him” read as the other party ${numEn(by.pronoun)}, an answer to the speaker before ${numEn(by.turn)}.`,
  handCheck: (h: Record<Src, [number, number]>) =>
    `A hand check of 50 quotations drawn after the rules were set: named ${h.explicit[0]} / ${h.explicit[1]}, called by name ${h.vocative[0]} / ${h.vocative[1]}, “to him” ${h.pronoun[0]} / ${h.pronoun[1]}, an answer ${h.turn[0]} / ${h.turn[1]}. The checks below use the first two only; every addressee is the sensitivity check.`,
  sources: { explicit: 'named', vocative: 'called by name', pronoun: '“to him”', turn: 'an answer' } as Record<Src, string>,
  checksTitle: 'Checks fixed in advance',
  verdict: { holds: 'holds', fails: 'does not hold' },
  deference: (up: number, rest: number, count: number, of: number, nul: number | null, p: number | null) =>
    `“Your servant” (עבדך, אמתך, שפחתך) in speech to God or a king: ${up.toFixed(1)} times per 1,000 words (${numEn(count)} in ${numEn(of)} words), against ${rest.toFixed(1)} in speech to anyone else; the difference is ${(up - rest).toFixed(1)}, against ${x1(nul)} with the “up” label shuffled among the quotations of each book (p ${fp(p)}). A known answer: deference to a superior (Revell 1996).`,
  particle: (up: number, rest: number, count: number, of: number, p: number | null) =>
    `נא right after an imperative: ${pct(up)} of the commands to God or a king (${numEn(count)} of ${numEn(of)}), against ${pct(rest)} of the others (p ${fp(p)}). Contested: is נא a mark of politeness (Shulman 1996, Christiansen 2009) or a logical particle, “then” (Lambdin 1971)?`,
  lastWord: (obs: number, n: number, exp: number, p: number) =>
    `In ${numEn(n)} exchanges between God or a king and someone of lower rank, the higher one speaks last in ${numEn(obs)}, against ${exp.toFixed(1)} if the last turn were any of the exchange's turns at random (p ${fp(p)}). An open question.`,
  sensitivity: (d: number, dp: number | null, pr: number, pp: number | null) =>
    `With every addressee, however it was found: “your servant” ${d.toFixed(1)} more per 1,000 words (p ${fp(dp)}); נא ${pct(pr)} more often (p ${fp(pp)}).`,
  described: (opens: number, n: number, exp: number, p: number, longer: number, shorter: number, mh: number | null, ml: number | null, lp: number | null) =>
    `Described, without a verdict: the higher party opens ${numEn(opens)} of the ${numEn(n)} exchanges (${exp.toFixed(1)} expected, p ${fp(p)}); its turns are longer in ${numEn(longer)} and shorter in ${numEn(shorter)} (median ${x1(mh)} against ${x1(ml)} words a turn; sign test p ${fp(lp)}).`,
  booksTitle: 'Who speaks to whom',
  book: 'Book',
  bookOption: (name: string, q: number) => `${name} (${numEn(q)})`,
  network: (book: string) => `Conversations in ${book}`,
  networkLabel: (n: number, book: string) => `The ${n} most active speakers of ${book} and who they speak to; the same pairs are listed in the table below.`,
  pairsTitle: (book: string) => `Pairs in ${book}`,
  cols: { speaker: 'Speaker', addressee: 'To', quotes: 'Quotations', words: 'Words', named: 'Named or called' },
  pairTitle: (s: string, a: string, n: number) => `${s} → ${a}: ${countEn(n, 'quotation', 'quotations')}`,
  filterParty: (who: string) => `Show the exchanges of ${who}`,
  noPairs: 'No addressed speech found in this book.',
  exchangesTitle: 'Exchanges',
  exchangesLede: 'Runs of turns introduced by the narrator between two speakers who both speak; a third speaker, or a turn addressed to someone else, ends one.',
  unequal: 'Only God or a king with someone of lower rank',
  party: (who: string) => `With ${who}`,
  allParties: 'Anyone',
  count: (n: number) => countEn(n, 'exchange', 'exchanges'),
  turns: (n: number, a: string, an: number, b: string, bn: number) => `${countEn(n, 'turn', 'turns')}: ${a} ${an}, ${b} ${bn}`,
  last: (who: string) => `last word: ${who}`,
  read: 'Read with the speakers',
  empty: 'No exchanges match.',
  god: 'God',
}

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
  deference: (up: number, rest: number, count: number, of: number, nul: number | null, p: number | null) =>
    `„עבדך” (או „אמתך”, „שפחתך”) בדיבור אל האל או אל מלך: ${up.toFixed(1)} פעמים לכל 1,000 מילים (${numHe(count)} ב־${numHe(of)} מילים), לעומת ${rest.toFixed(1)} בדיבור אל כל אחד אחר; ההפרש ${(up - rest).toFixed(1)}, לעומת ${x1(nul)} כשהסימון „כלפי מעלה” מעורבב בין הציטוטים של כל ספר (p ${fp(p)}). תשובה ידועה: כבוד כלפי מי שמעליך (Revell 1996).`,
  particle: (up: number, rest: number, count: number, of: number, p: number | null) =>
    `„נא” מיד אחרי ציווי: ${pct(up)} מן הציוויים אל האל או אל מלך (${numHe(count)} מתוך ${numHe(of)}), לעומת ${pct(rest)} מן האחרים (p ${fp(p)}). שנוי במחלוקת: האם „נא” הוא סימן נימוס (Shulman 1996,‏ Christiansen 2009) או מילית לוגית, „אם כן” (Lambdin 1971)?`,
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
