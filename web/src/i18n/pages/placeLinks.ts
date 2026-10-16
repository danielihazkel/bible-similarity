// Interface strings of Overview → Named together, near together? (DESIGN.md §16.61). English
// first, Hebrew typed against it.

import type { DecayVariant, PlaceLinkSort } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const r2 = (x: number) => (Math.abs(x) < 0.005 ? '0.00' : x.toFixed(2))
const kmEn = (n: number) => `${numEn(Math.round(n))} km`
const kmHe = (n: number) => `${numHe(Math.round(n))} ק״מ`
const share = (x: number) => `${(x * 100).toFixed(x < 0.01 ? 2 : 1)}%`
const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

export const plkEn = {
  title: 'Named together, near together?',
  lede: 'Two places are linked when verses name them together more often than chance, and the link is as strong as its G² against independence. Do strongly linked places lie near each other, as places in one story or one district would, or does the text join places regardless of the miles between them?',
  noData: 'Not computed in this build: run `bsim place-links`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (pairs: number, places: number, min: number, rho: number, nullMean: number, q05: number, q95: number, p: number, shuffles: number) =>
    `${numEn(pairs)} pairs of ${numEn(places)} places are named together in ${numEn(min)} verses or more. The stronger the link, the nearer the places: Spearman’s ρ ${r2(rho)} between link strength and distance, against ${r2(nullMean)} with the places’ points shuffled among them (90% of ${numEn(shuffles)} shuffles between ${r2(q05)} and ${r2(q95)}; p ${fp(p)}).`,
  caveat: 'Shuffling the points keeps who is linked with whom, and how strongly; only where the places lie is drawn again.',
  variantsTitle: 'Three ways',
  variants: {
    all: 'Every located place',
    sure: 'Sure sites only',
    no_lists: 'Without the place lists',
  } satisfies Record<DecayVariant, string>,
  variantHints: {
    all: 'The test',
    sure: (score: number) => `Both places with an OpenBible vote of at least ${numEn(score)}`,
    no_lists: (lists: string) => `Leaving out ${lists}, which name neighbours by design`,
  },
  vcols: { variant: 'Places', places: 'Places', pairs: 'Linked pairs', rho: 'ρ', shuffled: 'Shuffled (90%)', p: 'p' },
  rho: r2,
  range: (mean: number, q05: number, q95: number) => `${r2(mean)} (${r2(q05)} to ${r2(q95)})`,
  untested: (n: number) => `${countEn(n, 'pair', 'pairs')}: too few`,
  // the chart
  chartTitle: 'Link strength against distance',
  chartLabel: (n: number) => `A scatter of ${numEn(n)} linked pairs of places: distance across, on a log scale, link strength up, on a log scale. The far pairs are marked.`,
  axisKm: 'km apart',
  axisG2: 'link strength (G²)',
  far: (km: number) => `at least ${kmEn(km)} apart`,
  near: 'nearer',
  // the bins
  binsTitle: 'The decay',
  binsLede: (min: number) => `Every pair of places each named in ${numEn(min)} verses or more, by distance: how many of them are linked, and how strongly.`,
  variant: 'Places',
  bcols: { km: 'Distance', pairs: 'Pairs', linked: 'Linked', share: 'Share linked', g2: 'Median strength' },
  bin: (lo: number, hi: number | null) => (hi == null ? `${numEn(lo)} km and more` : `${numEn(lo)}–${numEn(hi)} km`),
  share,
  g2: (x: number) => x.toFixed(1),
  // leads
  leadsTitle: 'Far apart, named together',
  leadsLede: (km: number, n: number) =>
    `Of the linked pairs, ${numEn(n)} lie at least ${kmEn(km)} apart. The most strongly linked of them are the text’s long reaches: a border from end to end, an empire’s cities, the powers of the age.`,
  // after the two names
  known: (rank: number | null, n: number, top: number, km: number | null) =>
    rank == null
      ? ': not among the far pairs.'
      : `: ${km == null ? '' : `${kmEn(km)} apart, `}rank ${numEn(rank)} of ${numEn(n)} far pairs (a known answer: among the first ${numEn(top)}).`,
  knownMissing: ': not linked.',
  and: 'and',
  leadsMap: 'The far pairs on the map, each joined by a line',
  lcols: { rank: '#', pair: 'Places', together: 'Verses together', g2: 'Strength', km: 'Apart' },
  km: kmEn,
  pairsOf: (he: string) => `Pairs of ${he}`,
  // pairs
  pairsTitle: 'The linked pairs',
  pairsSummary: (n: number) => countEn(n, 'pair', 'pairs'),
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  sort: 'Order',
  sorts: { g2: 'Strongest first', km: 'Farthest first', near: 'Nearest first' } satisfies Record<PlaceLinkSort, string>,
  placeFilter: (he: string) => `Only the pairs of ${he}`,
  allPlaces: 'Show every pair',
  emptyPairs: 'No linked pairs.',
  pairLine: (k: number, g2: number, km: number) => `${countEn(k, 'verse', 'verses')} together · strength ${g2.toFixed(1)} · ${kmEn(km)}`,
  onMap: (he: string) => `${he} on Places on the map`,
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
}

export const plkHe: typeof plkEn = {
  title: 'נזכרים יחד, שוכנים יחד?',
  lede: 'שני מקומות קשורים כשפסוקים מזכירים אותם יחד יותר ממה שהמקרה נותן, וחוזק הקשר הוא ה־G² שלו מול אי־תלות. האם מקומות שקשורים בחוזק שוכנים קרוב זה לזה, כמו מקומות של סיפור אחד או של מחוז אחד, או שהכתוב מצרף מקומות בלי קשר למרחק ביניהם?',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim place-links` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  summary: (pairs: number, places: number, min: number, rho: number, nullMean: number, q05: number, q95: number, p: number, shuffles: number) =>
    `${numHe(pairs)} זוגות של ${numHe(places)} מקומות נזכרים יחד ב־${numHe(min)} פסוקים או יותר. ככל שהקשר חזק יותר, המקומות קרובים יותר: ρ של ספירמן ${r2(rho)} בין חוזק הקשר למרחק, לעומת ${r2(nullMean)} כשנקודות המקומות מעורבבות ביניהם (90% מתוך ${numHe(shuffles)} ערבובים בין ${r2(q05)} ל־${r2(q95)}; p ${fp(p)}).`,
  caveat: 'ערבוב הנקודות שומר על מי קשור עם מי ובאיזה חוזק; רק מקום המקומות נבחר מחדש.',
  variantsTitle: 'שלוש דרכים',
  variants: { all: 'כל מקום שמיקומו ידוע', sure: 'אתרים ודאיים בלבד', no_lists: 'בלי רשימות המקומות' },
  variantHints: {
    all: 'הבדיקה',
    sure: (score: number) => `שני המקומות קיבלו ב־OpenBible ${numHe(score)} קולות לפחות`,
    no_lists: (lists: string) => `בלי ${lists}, שמונים שכנים מעצם טבעם`,
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
  onMap: (he: string) => `${he} במקומות על המפה`,
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
