// The guided tours' steps (DESIGN.md §11): each a page of the site, its captions in the catalogs
// (`i18n/pages/tours.ts`). A step's page carries `?tour=<key>&step=<n>`, which shows the tour bar.
import type { TourKey } from '../i18n/pages/tours'

export const TOURS: Record<TourKey, string[]> = {
  parallels: ['/compare?a=c%3A26%3A14&b=c%3A26%3A53', '/divine?book=26', '/synopses', '/sums?step=yes'],
  numbers: ['/chronology', '/sums?list=ezra2', '/masorah', '/gematria?q=318'],
  poetry: ['/poetry?view=pairs', '/acrostics', '/read/c%3A26%3A22?layers=mood%2Cspeakers', '/refrains'],
  stories: ['/frameworks', '/retold', '/etiologies', '/haftarot?p=p%3AVayera'],
}

export const TOUR_KEYS = Object.keys(TOURS) as TourKey[]

export const isTour = (k: string | null): k is TourKey => k !== null && k in TOURS

/** The address of a tour's step (1-based): its page with the tour's parameters. */
export function tourHref(key: TourKey, step: number): string {
  const route = TOURS[key][step - 1]
  return `${route}${route.includes('?') ? '&' : '?'}tour=${key}&step=${step}`
}
