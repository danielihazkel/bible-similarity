// The Hebrew half of `../placeLinks.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, kmHe, plkEn, r2, share, versesHe } from '../placeLinks'

export const plkHe: typeof plkEn = {
  title: 'נזכרים יחד, שוכנים יחד?',
  lede: 'שני מקומות קשורים כשפסוקים מזכירים אותם יחד יותר ממה שהמקרה נותן, וחוזק הקשר הוא ה־G² שלו מול אי־תלות. האם מקומות שקשורים בחוזק שוכנים קרוב זה לזה, כמו מקומות של סיפור אחד או של מחוז אחד, או שהכתוב מצרף מקומות בלי קשר למרחק ביניהם?',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim place-links` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  summary: (pairs: number, places: number, min: number, rho: number, nullMean: number, q05: number, q95: number, p: number, shuffles: number) =>
    `${numHe(pairs)} זוגות של ${numHe(places)} מקומות נזכרים יחד ב־${numHe(min)} פסוקים או יותר. ככל שהקשר חזק יותר, המקומות קרובים יותר: ρ של ספירמן ${r2(rho)} בין חוזק הקשר למרחק, לעומת ${r2(nullMean)} כשנקודות המקומות מעורבבות ביניהם (90% מתוך ${numHe(shuffles)} ערבובים בין ${r2(q05)} ל־${r2(q95)}; p ${fp(p)}).`,
  caveat: 'ערבוב הנקודות שומר על מי קשור עם מי ובאיזה חוזק; רק מיקום המקומות נבחר מחדש.',
  variantsTitle: 'שלוש דרכים',
  variants: { all: 'כל מקום שמיקומו ידוע', sure: 'אתרים ודאיים בלבד', no_lists: 'בלי רשימות המקומות' },
  variantHints: {
    all: 'הבדיקה',
    sure: (score: number) => `לשני המקומות ציון OpenBible של ${numHe(score)} לפחות`,
    no_lists: (lists: string) => `בלי ${lists}, שמפרטים מקומות שכנים מעצם טבעם`,
  },
  vcols: { variant: 'מקומות', places: 'מקומות', pairs: 'זוגות קשורים', rho: 'ρ', shuffled: 'מעורבב (90%)', p: 'p' },
  rho: r2,
  range: (mean: number, q05: number, q95: number) => `${r2(mean)} (${r2(q05)} עד ${r2(q95)})`,
  untested: (n: number) => `${countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות')}: מעט מדי`,
  chartTitle: 'חוזק הקשר מול המרחק',
  chartLabel: (n: number) => `פיזור של ${numHe(n)} זוגות מקומות קשורים: המרחק לרוחב, בסולם לוגריתמי, חוזק הקשר לגובה, בסולם לוגריתמי. הזוגות הרחוקים מסומנים.`,
  axisKm: 'ק״מ ביניהם',
  axisG2: 'חוזק הקשר (G²)',
  far: (km: number) => `${kmHe(km)} ביניהם לפחות`,
  near: 'קרובים יותר',
  binsTitle: 'הדעיכה',
  binsLede: (min: number) => `כל זוג מקומות שכל אחד מהם נזכר ב־${numHe(min)} פסוקים או יותר, לפי המרחק: כמה מהם קשורים, ובאיזה חוזק.`,
  variant: 'מקומות',
  bcols: { km: 'מרחק', pairs: 'זוגות', linked: 'קשורים', share: 'שיעור הקשורים', g2: 'חוזק חציוני' },
  bin: (lo: number, hi: number | null) => (hi == null ? `${numHe(lo)} ק״מ ויותר` : `${numHe(lo)}–${numHe(hi)} ק״מ`),
  share,
  g2: (x: number) => x.toFixed(1),
  leadsTitle: 'רחוקים זה מזה, נזכרים יחד',
  leadsLede: (km: number, n: number) =>
    `מבין הזוגות הקשורים, ${numHe(n)} רחוקים זה מזה ${kmHe(km)} לפחות. החזקים שבהם הם מרחביו הגדולים של הכתוב: גבול מקצה לקצה, ערי אימפריה, המעצמות של התקופה.`,
  known: (rank: number | null, n: number, top: number, km: number | null) =>
    rank == null
      ? ': אינם בין הזוגות הרחוקים.'
      : `: ${km == null ? '' : `${kmHe(km)} ביניהם, `}במקום ${numHe(rank)} מתוך ${numHe(n)} זוגות רחוקים (תשובה ידועה: בין ${numHe(top)} הראשונים).`,
  knownMissing: ': אינם קשורים.',
  and: 'ו',
  leadsMap: 'הזוגות הרחוקים על המפה, כל זוג מחובר בקו',
  lcols: { rank: '#', pair: 'מקומות', together: 'פסוקים משותפים', g2: 'חוזק', km: 'מרחק' },
  km: kmHe,
  pairsOf: (he: string) => `הזוגות של ${he}`,
  pairsTitle: 'הזוגות הקשורים',
  pairsSummary: (n: number) => countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות'),
  pageOf: (page: number, pages: number) => `עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  sort: 'סדר',
  sorts: { g2: 'החזקים קודם', km: 'הרחוקים קודם', near: 'הקרובים קודם' },
  placeFilter: (he: string) => `רק הזוגות של ${he}`,
  allPlaces: 'הצגת כל הזוגות',
  emptyPairs: 'אין זוגות קשורים.',
  pairLine: (k: number, g2: number, km: number) => `${versesHe(k)} יחד · חוזק ${g2.toFixed(1)} · ${kmHe(km)}`,
  onMap: (he: string) => `${he} בעמוד „מקומות על המפה”`,
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
