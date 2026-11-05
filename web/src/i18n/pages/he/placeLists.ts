// The Hebrew half of `../placeLists.ts` (loaded with the Hebrew interface only).
import { numHe, pct } from '../../fmt'
import { fp, placesHe, plsEn, townsHe } from '../placeLists'

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
  onMap: (he: string) => `${he} בעמוד ״מקומות על המפה״`,
  districtsTitle: 'ערי יהושע לפי מחוזות',
  districtsLede: 'ערי יהודה באות במחוזות, וכל אחד נחתם ב״ערים … וחצריהן״; וכך ערי השבטים. האם שתי ערים מאותו מחוז קרובות זו לזו יותר משתי ערים של הרשימה כשהמחוזות מעורבבים ביניהן?',
  grouping: 'חלוקה',
  groupings: { judah: 'מחוזות יהודה (יהושע טו:כא–סב)', tribes: 'ערי השבטים (יהושע יח–יט)' },
  districtSummary: (n: number, k: number, within: number, mean: number, p: number, nearest: number) =>
    `${townsHe(n)} ב־${numHe(k)} מחוזות: שתי ערים מאותו מחוז רחוקות זו מזו ${numHe(Math.round(within))} ק״מ בממוצע, לעומת ${numHe(Math.round(mean))} ק״מ כשהמחוזות מעורבבים (p ${fp(p)}); ל־${pct(nearest)} מהערים העיר הקרובה ביותר היא ממחוזן.`,
  districtSure: (n: number, within: number, mean: number, p: number) =>
    `באתרים הוודאיים בלבד (${townsHe(n)}): ${numHe(Math.round(within))} ק״מ לעומת ${numHe(Math.round(mean))} ק״מ (p ${fp(p)}).`,
  districtMap: (label: string) => `ערי ${label} על המפה, צבועות לפי מחוז`,
  dcols: { district: 'מחוז', towns: 'ערים', apart: 'ק״מ ביניהן', random: 'בערבוב', p: 'p', sure: 'אתרים ודאיים בלבד' },
  single: 'עיר אחת',
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
