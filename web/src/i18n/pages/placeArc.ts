// Interface strings of Overview → The geographic arc (DESIGN.md §16.60). English first, Hebrew
// typed against it.

import { hebrewNumeral } from '../../lib/hebrew'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const chaptersHe = (n: number) => countHe(n, 'פרק אחד', 'שני פרקים', 'פרקים')
const kmEn = (n: number) => `${numEn(Math.round(n))} km`
const kmHe = (n: number) => `${numHe(Math.round(n))} ק״מ`

export const paEn = {
  title: 'The geographic arc',
  lede: 'Where does each chapter take place? A chapter’s centre is the mean of the places it names, each counted once per verse, and its spread how far those places lie from the centre on average. Do consecutive chapters stay close, does the centre move where the story goes, and do the oracles against the nations range wider than the rest of the prophets?',
  noData: 'Not computed in this build: run `bsim place-arc`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (placed: number, chapters: number, mean: number, nullMean: number, p: number, shuffles: number) =>
    `${numEn(placed)} of ${numEn(chapters)} chapters name places enough to be placed. Within a book, consecutive placed chapters lie ${kmEn(mean)} apart on average, against ${kmEn(nullMean)} with each book’s chapters shuffled (${numEn(shuffles)} orders; p ${fp(p)}).`,
  booksHeld: (held: number, n: number) => `${numEn(held)} of the ${numEn(n)} books with enough placed chapters hold on their own.`,
  caveat: (min: number) =>
    `A chapter is placed when it names places in ${countEn(min, 'mention', 'mentions')} or more (a place counts once per verse). Every place it names pulls on its centre: a place named in passing, Tarshish or Egypt in a memory of the exodus, as much as the scene’s own.`,
  // one book
  bookTitle: (book: string) => `The path of ${book}`,
  book: 'Book',
  bookNote: (n: number, chapters: number, mean: number, nullMean: number, p: number) =>
    `${numEn(n)} of ${numEn(chapters)} chapters placed: ${kmEn(mean)} from one to the next on average, against ${kmEn(nullMean)} in shuffled order (p ${fp(p)}).`,
  bookUntested: (n: number, chapters: number) => `${numEn(n)} of ${numEn(chapters)} chapters placed: too few to test.`,
  mapLabel: (book: string) => `The centres of the chapters of ${book} on the map, joined in order`,
  pointTitle: (label: string, n: number, spread: number) => `${label}: ${countEn(n, 'mention', 'mentions')}, spread ${kmEn(spread)}`,
  chaptersTitle: 'Chapter by chapter',
  chaptersLede: 'Each placed chapter with the place it names most, the km from the placed chapter before and its spread. The three longest steps are marked.',
  step: (km: number) => kmEn(km),
  stepFrom: (km: number, prev: number) => `${kmEn(km)} from ch. ${numEn(prev)}`,
  spread: (km: number) => `spread ${kmEn(km)}`,
  oracleTag: 'oracle',
  onMap: (label: string) => `${label} on Places on the map`,
  chapterNumber: (n: number) => numEn(n),
  booksTitle: 'Book by book',
  cols: { book: 'Book', placed: 'Placed chapters', step: 'Mean step', shuffled: 'Shuffled', ratio: 'Ratio', p: 'p' },
  colHints: { ratio: 'The book’s path over the shuffled orders’ mean: below 1, consecutive chapters lie closer than chance' },
  placedOf: (n: number, chapters: number) => `${numEn(n)} of ${numEn(chapters)}`,
  untested: 'too few',
  open: (book: string) => `Show ${book} on the map`,
  ratio: (x: number) => x.toFixed(2),
  km: kmEn,
  // known moves
  movesTitle: 'Known moves',
  movesLede: 'Four moves the story makes. A move holds when the centre of the span after lies nearer the region the story goes to than the centre of the span before, and the span before nearer the region it leaves. A check of the centres, not a discovery.',
  movesSummary: (held: number, n: number) => `${numEn(held)} of ${numEn(n)} moves hold.`,
  moves: { abram: 'Abram to Canaan', descent: 'Down to Egypt', exodus: 'Out of Egypt', exile: 'Carried to Babylon' } as Record<string, string>,
  regions: { mesopotamia: 'Mesopotamia', canaan: 'Canaan', egypt: 'Egypt', wilderness: 'the wilderness' } as Record<string, string>,
  mcols: { move: 'Move', before: 'Before', after: 'After', km: 'Centres apart' },
  endNote: (from: number, fromRegion: string, to: number, toRegion: string) => `${kmEn(from)} from ${fromRegion}, ${kmEn(to)} from ${toRegion}`,
  unplaced: 'too few places',
  movesMap: 'The known moves on the map: each from the centre of the span before to the centre of the span after',
  moveTitle: (move: string, label: string) => `${move}: ${label}`,
  // the oracles
  oraclesTitle: 'The oracles against the nations',
  oraclesLede: (refs: string) =>
    `The oracles against the nations (${refs}) name the nations’ lands and cities. Do their chapters range wider than the other chapters of the prophets? Spread, and reach (the centre’s km from Jerusalem), each against the labels shuffled over the placed chapters of the prophets, one-sided.`,
  oracleVerdict: (alpha: number) => `Holds when either measure is wider at p ≤ ${alpha}.`,
  ocols: { measure: 'Measure', oracles: 'Oracles', others: 'Other prophetic chapters', shuffled: 'Shuffled', p: 'p' },
  measures: { spread: 'Spread', reach: 'Reach from Jerusalem' } as Record<string, string>,
  meanMedian: (mean: number, median: number, n: number) => `${kmEn(mean)} (median ${kmEn(median)}; ${countEn(n, 'chapter', 'chapters')})`,
  oracleChapters: 'The oracles’ chapters',
  chcols: { chapter: 'Chapter', place: 'Named most', places: 'Places', spread: 'Spread', reach: 'Reach' },
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
}

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
  chaptersLede: 'כל פרק ממוקם עם המקום שהוא מזכיר הכי הרבה, המרחק בק״מ מהפרק הממוקם שלפניו והפיזור שלו. שלושת הצעדים הארוכים ביותר מסומנים.',
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
    `הנבואות על הגויים (${refs}) מזכירות את ארצות העמים ואת עריהם. האם פרקיהן משתרעים על פני שטח רחב משאר פרקי הנביאים? פיזור, וטווח (מרחק המרכז מירושלים), כל אחד מול התוויות מעורבבות בין הפרקים הממוקמים של הנביאים, חד־צדדי.`,
  oracleVerdict: (alpha: number) => `עומדת כשאחד המדדים רחב יותר ב־p ≤ ${alpha}.`,
  ocols: { measure: 'מדד', oracles: 'הנבואות', others: 'שאר פרקי הנביאים', shuffled: 'מעורבב', p: 'p' },
  measures: { spread: 'פיזור', reach: 'טווח מירושלים' },
  meanMedian: (mean: number, median: number, n: number) => `${kmHe(mean)} (חציון ${kmHe(median)}; ${chaptersHe(n)})`,
  oracleChapters: 'פרקי הנבואות',
  chcols: { chapter: 'פרק', place: 'הנזכר ביותר', places: 'מקומות', spread: 'פיזור', reach: 'טווח' },
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
}
