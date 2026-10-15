// Interface strings of Overview → Places on the map, the map component and the unit page's "Where
// this happens" (DESIGN.md §16.57). English first, Hebrew typed against it.

import type { PlaceKind } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

export const geoEn = {
  keys: (label: string) => `${label}. Drag to move the map, + and − to zoom; the arrow keys step through the places, most named first, and Enter opens one.`,
  zoom: 'Zoom',
  zoomIn: 'Zoom in',
  zoomOut: 'Zoom out',
  pointTitle: (he: string, n: number) => `${he}: ${countEn(n, 'verse', 'verses')}`,
  idle: 'Point at a place, or step through them with the arrow keys.',
}

export const geoHe: typeof geoEn = {
  keys: (label: string) => `${label}. גרירה מזיזה את המפה, + ו־− מגדילים ומקטינים; מקשי החצים עוברים בין המקומות, השכיחים קודם, ו־Enter פותח אחד מהם.`,
  zoom: 'הגדלה',
  zoomIn: 'הגדלה',
  zoomOut: 'הקטנה',
  pointTitle: (he: string, n: number) => `${he}: ${versesHe(n)}`,
  idle: 'הצבעה על מקום, או מעבר ביניהם במקשי החצים.',
}

export const plEn = {
  title: 'Places on the map',
  lede: 'Every place the text names, where it lies. A point is a place, larger the more verses name it, coloured by its kind; choose a book, a chapter or a kind, and open a place for the books that name it and the places named with it.',
  noData: 'Not computed in this build: run `bsim places`, then `bsim build-db`.',
  mapLabel: 'Places of the Bible on a map of the region',
  summary: (n: number, located: number) => `${countEn(n, 'place', 'places')} named, ${numEn(located)} on the map.`,
  inScope: (where: string) => `In ${where}: `,
  kind: 'Kind',
  all: 'All',
  kinds: { town: 'Towns', region: 'Regions', landform: 'Landforms', water: 'Water' } satisfies Record<PlaceKind, string>,
  kindOne: { town: 'Town', region: 'Region', landform: 'Landform', water: 'Water' } satisfies Record<PlaceKind, string>,
  chapter: 'Chapter',
  allChapters: 'All chapters',
  view: 'View',
  views: { land: 'The land', east: 'The Near East', fit: 'These places' },
  listTitle: 'Most named',
  listLede: 'Click a place to open it.',
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
  // the place panel
  panel: 'Place',
  close: 'Close',
  firstNamed: 'first named in',
  names: 'Its names',
  perBook: 'Verses per book',
  bookCount: (book: string, n: number) => `${book}: ${countEn(n, 'verse', 'verses')}`,
  partners: 'Named with',
  partnerTitle: (n: number) => `${countEn(n, 'verse', 'verses')} name both`,
  verses: 'Verses',
  verseCount: (n: number) => countEn(n, 'verse', 'verses'),
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  emptyVerses: 'No verse names this place.',
  // the unit page
  whereTitle: 'Where this happens',
  wherePlaces: (n: number, off: number) => `${countEn(n, 'place', 'places')} named here${off ? `, ${numEn(off)} not on the map` : ''}.`,
  openMap: 'Open on the map',
}

export const plHe: typeof plEn = {
  title: 'מקומות על המפה',
  lede: 'כל מקום שהכתוב מזכיר, והיכן הוא שוכן. כל נקודה היא מקום, גדולה יותר ככל שיותר פסוקים מזכירים אותו, וצבעה לפי סוגו; אפשר לבחור ספר, פרק או סוג, ולפתוח מקום כדי לראות את הספרים שמזכירים אותו ואת המקומות שנזכרים עמו.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim places` ואחר כך `bsim build-db`.',
  mapLabel: 'מקומות המקרא על מפת האזור',
  summary: (n: number, located: number) => `${countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')} נזכרים, ${numHe(located)} מהם על המפה.`,
  inScope: (where: string) => `ב${where}: `,
  kind: 'סוג',
  all: 'הכול',
  kinds: { town: 'ערים', region: 'אזורים', landform: 'תוואי קרקע', water: 'מים' },
  kindOne: { town: 'עיר', region: 'אזור', landform: 'תוואי קרקע', water: 'מים' },
  chapter: 'פרק',
  allChapters: 'כל הפרקים',
  view: 'תצוגה',
  views: { land: 'הארץ', east: 'המזרח הקדום', fit: 'המקומות האלה' },
  listTitle: 'הנזכרים ביותר',
  listLede: 'לחיצה על מקום פותחת אותו.',
  credit: 'מפה: Natural Earth (נחלת הכלל). מקומות: TIPNR של STEPBible ו־OpenBible.info (CC BY 4.0).',
  panel: 'מקום',
  close: 'סגירה',
  firstNamed: 'נזכר לראשונה ב',
  names: 'שמותיו',
  perBook: 'פסוקים בכל ספר',
  bookCount: (book: string, n: number) => `${book}: ${versesHe(n)}`,
  partners: 'נזכר יחד עם',
  partnerTitle: (n: number) => `${versesHe(n)} מזכירים את שניהם`,
  verses: 'פסוקים',
  verseCount: (n: number) => versesHe(n),
  pageOf: (page: number, pages: number) => `עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  emptyVerses: 'אין פסוק שמזכיר את המקום הזה.',
  whereTitle: 'היכן זה קורה',
  wherePlaces: (n: number, off: number) => `${countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')} נזכרים כאן${off ? `, ${numHe(off)} מהם אינם על המפה` : ''}.`,
  openMap: 'פתיחה במפה',
}
