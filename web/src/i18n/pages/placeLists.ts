// Interface strings of Overview → Place lists on the ground (DESIGN.md §16.58). English first,
// Hebrew typed against it.

import type { PlaceListKind } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const townsHe = (n: number) => countHe(n, 'עיר אחת', 'שתי ערים', 'ערים')
const placesHe = (n: number) => countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')

export const plsEn = {
  title: 'Place lists on the ground',
  lede: 'The text lists places: the stations of the wilderness, the borders of the land, the towns of Judah and of the tribes, the cities of the table of nations. Are they named in an order that walks the ground? A list’s places, in the order the text names them, make a path; its length is set against the same places in random order. Joshua’s town lists are checked by district as well.',
  noData: 'Not computed in this build: run `bsim place-lists`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (held: number, n: number, heldSure: number, nSure: number, shuffles: number, sure: number) =>
    `${numEn(held)} of ${numEn(n)} lists make a shorter path than random orders of their places (${numEn(shuffles)} orders each); on sure sites alone (an OpenBible vote of at least ${numEn(sure)}), ${numEn(heldSure)} of ${numEn(nSure)}.`,
  caveat: 'Why sure sites alone: an obscure town is often placed by the company it keeps in the list, which would make the test circular. Regions are left out, having no single site.',
  listsTitle: 'The lists',
  cols: { list: 'List', kind: 'Kind', places: 'Places', path: 'Its path', random: 'Random orders', short: 'A short path', order: 'Order', p: 'p', sure: 'Sure sites only' },
  colHints: {
    places: 'Located places of the list, of those it names',
    order: 'How far the text’s path goes from the random orders’ mean towards a short path through the same places: 0 no better than random, 100% as short',
  },
  kinds: { itinerary: 'Itinerary', boundary: 'Boundary', towns: 'Town list', nations: 'Table of nations' } satisfies Record<PlaceListKind, string>,
  km: (n: number) => `${numEn(Math.round(n))} km`,
  placesOf: (n: number, named: number) => (n === named ? numEn(n) : `${numEn(n)} of ${numEn(named)}`),
  order: (x: number) => pct(x),
  p: fp,
  untested: (n: number) => `${countEn(n, 'place', 'places')}: too few`,
  open: (label: string) => `Open ${label}`,
  // one list
  pathTitle: (label: string) => `The path of ${label}`,
  mapLabel: (label: string) => `The places of ${label} on the map, joined in the order the text names them`,
  show: 'Show',
  shows: { text: 'The text’s order', short: 'A short path' },
  pathNote: (n: number, path: number, mean: number, short: number, p: number) =>
    `${countEn(n, 'place', 'places')}: the text’s order walks ${numEn(Math.round(path))} km; random orders of the same places ${numEn(Math.round(mean))} km on average, a short path ${numEn(Math.round(short))} km (p ${fp(p)}).`,
  histTitle: 'The text’s path among random orders',
  histLabel: (path: number, mean: number) =>
    `A histogram of the random orders’ path lengths, centred near ${numEn(Math.round(mean))} km; the text’s path, ${numEn(Math.round(path))} km, is marked.`,
  histText: 'the text',
  histShort: 'short path',
  stepsTitle: 'In the text’s order',
  stepsLede: 'Each place with the km from the one before; a sure site is marked. A long step is a place far from its neighbours in the list: often an identification to doubt.',
  sure: 'sure',
  sureTitle: (score: number) => `A sure site: OpenBible’s vote ${numEn(score)} / 1,000`,
  onMap: (he: string) => `${he} on Places on the map`,
  // districts
  districtsTitle: 'Joshua’s towns by district',
  districtsLede: 'Judah’s towns come in districts, each closed by “cities … with their villages”; the tribes’ towns likewise. Do two towns of one district lie closer than two towns of the list with the districts shuffled over them?',
  grouping: 'Grouping',
  groupings: { judah: 'Judah’s districts (Joshua 15:21–62)', tribes: 'The tribes’ towns (Joshua 18–19)' } as Record<string, string>,
  districtSummary: (n: number, k: number, within: number, mean: number, p: number, nearest: number) =>
    `${countEn(n, 'town', 'towns')} in ${numEn(k)} districts: two towns of one district lie ${numEn(Math.round(within))} km apart on average, against ${numEn(Math.round(mean))} km with the districts shuffled (p ${fp(p)}); ${pct(nearest)} of the towns have a town of their own district nearest.`,
  districtSure: (n: number, within: number, mean: number, p: number) =>
    `On sure sites alone (${countEn(n, 'town', 'towns')}): ${numEn(Math.round(within))} km against ${numEn(Math.round(mean))} km (p ${fp(p)}).`,
  districtMap: (label: string) => `The towns of ${label} on the map, coloured by district`,
  dcols: { district: 'District', towns: 'Towns', apart: 'Km apart', random: 'Shuffled', p: 'p', sure: 'Sure sites only' },
  single: 'one town',
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
}

export const plsHe: typeof plsEn = {
  title: 'רשימות המקומות על פני הארץ',
  lede: 'הכתוב מונה מקומות: מסעי המדבר, גבולות הארץ, ערי יהודה וערי השבטים, הערים שבלוח העמים. האם הם נמנים בסדר שהולך על פני הארץ? מקומות הרשימה, בסדר שהכתוב מונה אותם, יוצרים מסלול; אורכו נמדד מול אותם המקומות בסדר אקראי. רשימות הערים שביהושע נבדקות גם לפי מחוזות.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim place-lists` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  summary: (held: number, n: number, heldSure: number, nSure: number, shuffles: number, sure: number) =>
    `${numHe(held)} מתוך ${numHe(n)} רשימות יוצרות מסלול קצר משל סדרים אקראיים של מקומותיהן (${numHe(shuffles)} סדרים לכל אחת); באתרים הוודאיים בלבד (שקיבלו ב־OpenBible ${numHe(sure)} קולות לפחות), ${numHe(heldSure)} מתוך ${numHe(nSure)}.`,
  caveat: 'מדוע אתרים ודאיים בלבד: עיר עלומה ממוקמת לא פעם לפי שכנותיה ברשימה, וזה היה הופך את הבדיקה למעגלית. חבלי ארץ אינם נכללים, שאין להם אתר אחד.',
  listsTitle: 'הרשימות',
  cols: { list: 'רשימה', kind: 'סוג', places: 'מקומות', path: 'המסלול', random: 'סדרים אקראיים', short: 'מסלול קצר', order: 'סדר', p: 'p', sure: 'אתרים ודאיים בלבד' },
  colHints: {
    places: 'מקומות הרשימה שמיקומם ידוע, מתוך אלה שהיא מונה',
    order: 'כמה מתקרב מסלול הכתוב מממוצע הסדרים האקראיים אל מסלול קצר באותם המקומות: 0 אינו טוב מאקראי, 100% קצר כמוהו',
  },
  kinds: { itinerary: 'מסעות', boundary: 'גבול', towns: 'רשימת ערים', nations: 'לוח העמים' },
  km: (n: number) => `${numHe(Math.round(n))} ק״מ`,
  placesOf: (n: number, named: number) => (n === named ? numHe(n) : `${numHe(n)} מתוך ${numHe(named)}`),
  order: (x: number) => pct(x),
  p: fp,
  untested: (n: number) => `${placesHe(n)}: מעט מדי`,
  open: (label: string) => `פתיחת ${label}`,
  pathTitle: (label: string) => `המסלול של ${label}`,
  mapLabel: (label: string) => `מקומות ${label} על המפה, מחוברים בסדר שהכתוב מונה אותם`,
  show: 'הצגה',
  shows: { text: 'סדר הכתוב', short: 'מסלול קצר' },
  pathNote: (n: number, path: number, mean: number, short: number, p: number) =>
    `${placesHe(n)}: סדר הכתוב הולך ${numHe(Math.round(path))} ק״מ; סדרים אקראיים של אותם המקומות ${numHe(Math.round(mean))} ק״מ בממוצע, מסלול קצר ${numHe(Math.round(short))} ק״מ (p ${fp(p)}).`,
  histTitle: 'מסלול הכתוב בין סדרים אקראיים',
  histLabel: (path: number, mean: number) =>
    `היסטוגרמה של אורכי המסלולים בסדרים האקראיים, סביב ${numHe(Math.round(mean))} ק״מ; מסלול הכתוב, ${numHe(Math.round(path))} ק״מ, מסומן.`,
  histText: 'הכתוב',
  histShort: 'מסלול קצר',
  stepsTitle: 'בסדר הכתוב',
  stepsLede: 'כל מקום עם המרחק בק״מ מקודמו; אתר ודאי מסומן. צעד ארוך הוא מקום רחוק משכניו ברשימה: לא פעם זיהוי מפוקפק.',
  sure: 'ודאי',
  sureTitle: (score: number) => `אתר ודאי: ${numHe(score)} קולות מתוך 1,000 ב־OpenBible`,
  onMap: (he: string) => `${he} במקומות על המפה`,
  districtsTitle: 'ערי יהושע לפי מחוזות',
  districtsLede: 'ערי יהודה באות במחוזות, וכל אחד נחתם ב״ערים … וחצריהן״; וכך ערי השבטים. האם שתי ערים מאותו מחוז קרובות זו לזו יותר משתי ערים של הרשימה כשהמחוזות מעורבבים ביניהן?',
  grouping: 'חלוקה',
  groupings: { judah: 'מחוזות יהודה (יהושע טו:כא–סב)', tribes: 'ערי השבטים (יהושע יח–יט)' },
  districtSummary: (n: number, k: number, within: number, mean: number, p: number, nearest: number) =>
    `${townsHe(n)} ב־${numHe(k)} מחוזות: שתי ערים מאותו מחוז רחוקות זו מזו ${numHe(Math.round(within))} ק״מ בממוצע, לעומת ${numHe(Math.round(mean))} ק״מ כשהמחוזות מעורבבים (p ${fp(p)}); ל־${pct(nearest)} מהערים העיר הקרובה ביותר היא ממחוזן.`,
  districtSure: (n: number, within: number, mean: number, p: number) =>
    `באתרים הוודאיים בלבד (${townsHe(n)}): ${numHe(Math.round(within))} ק״מ לעומת ${numHe(Math.round(mean))} ק״מ (p ${fp(p)}).`,
  districtMap: (label: string) => `ערי ${label} על המפה, צבועות לפי מחוז`,
  dcols: { district: 'מחוז', towns: 'ערים', apart: 'ק״מ ביניהן', random: 'מעורבב', p: 'p', sure: 'אתרים ודאיים בלבד' },
  single: 'עיר אחת',
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
