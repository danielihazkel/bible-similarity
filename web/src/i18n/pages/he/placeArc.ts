// The Hebrew half of `../placeArc.ts` (loaded with the Hebrew interface only).
import { hebrewNumeral } from '../../../lib/hebrew'
import { countHe, numHe } from '../../fmt'
import { chaptersHe, fp, kmHe, paEn } from '../placeArc'

export const paHe: typeof paEn = {
  title: 'הקשת הגאוגרפית',
  lede: 'היכן מתרחש כל פרק? מרכז הפרק הוא ממוצע המקומות שהוא מזכיר, כל אחד פעם אחת בכל פסוק, והפיזור שלו הוא המרחק הממוצע של המקומות האלה מהמרכז. האם פרקים סמוכים נשארים קרובים זה לזה, האם המרכז זז לאן שהסיפור הולך, והאם הנבואות על הגויים משתרעות על פני שטח רחב משאר פרקי הנביאים?',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim place-arc` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  summary: (placed: number, chapters: number, mean: number, nullMean: number, p: number, shuffles: number) =>
    `${numHe(placed)} מתוך ${numHe(chapters)} פרקים מזכירים די מקומות כדי למקם אותם. בתוך ספר, פרקים ממוקמים סמוכים רחוקים זה מזה ${kmHe(mean)} בממוצע, לעומת ${kmHe(nullMean)} כשפרקי כל ספר מעורבבים (${numHe(shuffles)} סדרים; p ${fp(p)}).`,
  booksHeld: (held: number, n: number) => `${numHe(held)} מתוך ${numHe(n)} הספרים שיש בהם די פרקים ממוקמים עומדים בכך בפני עצמם.`,
  caveat: (min: number) =>
    `פרק ממוקם כשהוא מזכיר מקומות ${min === 1 ? 'פעם אחת' : `${numHe(min)} פעמים`} לפחות (מקום נספר פעם אחת בכל פסוק). כל מקום שהפרק מזכיר מושך את מרכזו: מקום שנזכר אגב, תרשיש, או מצרים בזכר יציאת מצרים, כמו מקום ההתרחשות עצמו.`,
  bookTitle: (book: string) => `המסלול של ${book}`,
  book: 'ספר',
  bookNote: (n: number, chapters: number, mean: number, nullMean: number, p: number) =>
    `${numHe(n)} מתוך ${numHe(chapters)} פרקים ממוקמים: ${kmHe(mean)} מפרק לפרק בממוצע, לעומת ${kmHe(nullMean)} בסדר מעורבב (p ${fp(p)}).`,
  bookUntested: (n: number, chapters: number) => `${numHe(n)} מתוך ${numHe(chapters)} פרקים ממוקמים: מעט מדי לבדיקה.`,
  mapLabel: (book: string) => `מרכזי פרקי ${book} על המפה, מחוברים לפי הסדר`,
  pointTitle: (label: string, n: number, spread: number) =>
    `${label}: ${countHe(n, 'אזכור אחד', 'שני אזכורים', 'אזכורים')}, פיזור ${kmHe(spread)}`,
  chaptersTitle: 'פרק אחר פרק',
  chaptersLede: 'כל פרק ממוקם עם המקום הנזכר בו ביותר, המרחק בק״מ מהפרק הממוקם שלפניו והפיזור שלו. שלושת הצעדים הארוכים ביותר מסומנים.',
  step: (km: number) => kmHe(km),
  stepFrom: (km: number, prev: number) => `${kmHe(km)} מפרק ${hebrewNumeral(prev)}`,
  spread: (km: number) => `פיזור ${kmHe(km)}`,
  oracleTag: 'נבואה על הגויים',
  onMap: (label: string) => `${label} במקומות על המפה`,
  chapterNumber: (n: number) => hebrewNumeral(n),
  booksTitle: 'ספר אחר ספר',
  cols: { book: 'ספר', placed: 'פרקים ממוקמים', step: 'צעד ממוצע', shuffled: 'מעורבב', ratio: 'יחס', p: 'p' },
  colHints: { ratio: 'מסלול הספר חלקי ממוצע הסדרים המעורבבים: מתחת ל־1, פרקים סמוכים קרובים יותר ממה שהמקרה נותן' },
  placedOf: (n: number, chapters: number) => `${numHe(n)} מתוך ${numHe(chapters)}`,
  untested: 'מעט מדי',
  open: (book: string) => `הצגת ${book} על המפה`,
  ratio: (x: number) => x.toFixed(2),
  km: kmHe,
  movesTitle: 'מעברים ידועים',
  movesLede: 'ארבעה מעברים שהסיפור עושה. מעבר עומד כשמרכז הקטע שאחריו קרוב לאזור שהסיפור הולך אליו יותר ממרכז הקטע שלפניו, והקטע שלפניו קרוב יותר לאזור שהוא עוזב. בדיקה של המרכזים, לא תגלית.',
  movesSummary: (held: number, n: number) => `${numHe(held)} מתוך ${numHe(n)} מעברים עומדים.`,
  moves: { abram: 'אברם לכנען', descent: 'הירידה למצרים', exodus: 'היציאה ממצרים', exile: 'הגלות לבבל' },
  regions: { mesopotamia: 'ארם נהרים ובבל', canaan: 'כנען', egypt: 'מצרים', wilderness: 'המדבר' },
  mcols: { move: 'מעבר', before: 'לפני', after: 'אחרי', km: 'בין המרכזים' },
  endNote: (from: number, fromRegion: string, to: number, toRegion: string) => `${kmHe(from)} מ${fromRegion}, ${kmHe(to)} מ${toRegion}`,
  unplaced: 'מעט מדי מקומות',
  movesMap: 'המעברים הידועים על המפה: כל אחד ממרכז הקטע שלפניו אל מרכז הקטע שאחריו',
  moveTitle: (move: string, label: string) => `${move}: ${label}`,
  oraclesTitle: 'הנבואות על הגויים',
  oraclesLede: (refs: string) =>
    `הנבואות על הגויים (${refs}) מזכירות את ארצות העמים ואת עריהם. האם פרקיהן משתרעים על פני שטח רחב משאר פרקי הנביאים? פיזור, וטווח (מרחק המרכז מירושלים), כל אחד מול התוויות כשהן מעורבבות בין הפרקים הממוקמים של הנביאים, חד־צדדי.`,
  oracleVerdict: (alpha: number) => `עומדת כשאחד המדדים רחב יותר ב־p ≤ ${alpha}.`,
  ocols: { measure: 'מדד', oracles: 'הנבואות', others: 'שאר פרקי הנביאים', shuffled: 'מעורבב', p: 'p' },
  measures: { spread: 'פיזור', reach: 'טווח מירושלים' },
  meanMedian: (mean: number, median: number, n: number) => `${kmHe(mean)} (חציון ${kmHe(median)}; ${chaptersHe(n)})`,
  oracleChapters: 'פרקי הנבואות',
  chcols: { chapter: 'פרק', place: 'הנזכר ביותר', places: 'מקומות', spread: 'פיזור', reach: 'טווח' },
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
