// Interface strings of this week's parasha (DESIGN.md §11.1): the coming Shabbat's reading, its
// haftarah and what the analyses found in it. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

export type WkPlace = 'abroad' | 'israel'

export const wkEn = {
  title: 'This week’s parasha',
  lede: 'The Torah portion read on the coming Shabbat, with its haftarah and what the site’s analyses found in it. The calendar is computed here, for Israel or abroad; pick any date to see its Shabbat.',
  place: { label: 'Reading', abroad: 'Abroad', israel: 'In Israel' },
  dateLabel: 'Date',
  prev: 'Previous Shabbat',
  next: 'Next Shabbat',
  today: 'This week',
  shabbat: (gregorian: string, hebrew: string) => `Shabbat, ${gregorian} · ${hebrew}`,
  festival: (gregorian: string) => `This Shabbat a festival’s reading replaces the weekly portion. The next weekly portion is read on Shabbat, ${gregorian}:`,
  together: 'Two portions are read together this week.',
  read: 'Read it',
  unitPage: 'Similar passages',
  haftarah: 'Haftarah',
  haftarahOf: (refs: string) => `The haftarah: ${refs}`,
  sephardi: (refs: string) => `Sephardi custom: ${refs}`,
  theme: { admonition: 'one of the three of admonition, fixed by the calendar', consolation: 'one of the seven of consolation, fixed by the calendar' } as Record<string, string>,
  rank: (r: number) => `Among the 380 chapters of the Prophets, the site’s fused ranking for this portion puts it ${numEn(r)}${r === 1 ? 'st' : r === 2 ? 'nd' : r === 3 ? 'rd' : 'th'}.`,
  haftarotLink: 'Haftarot and their portions',
  noHaftarah: 'The haftarot were not computed in this build.',
  foundTitle: 'What the analyses found here',
  homeTitle: 'This week',
  homeLine: (names: string, gregorian: string) => `${names}, read on Shabbat ${gregorian}`,
  homeFestival: (names: string, gregorian: string) => `A festival this Shabbat; next, ${names} on ${gregorian}`,
  open: 'This week’s parasha',
}

register('wk', wkEn)
