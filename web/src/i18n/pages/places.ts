// Interface strings of Overview → Places on the map, the map component and the unit page's "Where
// this happens" (DESIGN.md §16.57). English first, Hebrew typed against it.

import type { PlaceKind } from '../../api/types'
import { countEn, countHe, numEn } from '../fmt'
import { register } from '../en'

export const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

export const geoEn = {
  keys: (label: string) => `${label}. Drag to move the map, + and − to zoom; the arrow keys step through the places, most named first, and Enter opens one.`,
  zoom: 'Zoom',
  zoomIn: 'Zoom in',
  zoomOut: 'Zoom out',
  pointTitle: (he: string, n: number) => `${he}: ${countEn(n, 'verse', 'verses')}`,
  idle: 'Point at a place, or step through them with the arrow keys.',
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

register('pl', plEn)
register('geo', geoEn)
