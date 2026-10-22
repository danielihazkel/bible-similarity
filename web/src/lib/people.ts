// People of the family tree in a list of matches (`/genealogy/lookup`): what tells namesakes apart.

import type { PersonMatch } from '../api/types'
import type { Messages } from '../i18n'

/** The parent a person is drawn under (or the eponym of their tribe, or the spouse beside them), and
 * the verse that first names them: "son of Gilead · first in Judges 11:1". */
export function personAbout(x: PersonMatch, t: Messages['gt'], locale: 'en' | 'he'): string {
  const of = x.of_he
  const rel =
    !of || !x.relation
      ? undefined
      : x.relation === 'spouse'
        ? x.sex === 'm'
          ? t.husbandOf(of)
          : t.wifeOf(of)
        : x.relation === 'tribe'
          ? t.lineOf(of)
          : x.sex === 'f'
            ? t.daughterOf(of)
            : x.sex === 'm'
              ? t.sonOf(of)
              : t.childOf(of)
  const first = locale === 'he' ? x.first_label_he : x.first_label
  return [rel, first ? t.firstIn(first) : undefined].filter(Boolean).join(' · ')
}
