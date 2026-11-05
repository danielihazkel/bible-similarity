import { describe, expect, it } from 'vitest'
import { en } from '../i18n/en'
import { isGroup, matchPages, NAV, navFor, PERSONAL_PAGES } from './nav'

const pages = (entries: ReturnType<typeof navFor>) =>
  entries.flatMap((e) => (isGroup(e) ? [...e.items, ...(e.sections ?? []).flatMap((s) => s.items)] : [e])).map((p) => p.to)

describe('the nav on a server without your labels and notebook (a public deploy)', () => {
  it('is the whole nav where they are on', () => {
    expect(navFor(true)).toBe(NAV)
  })

  it('leaves them out of the links, the groups and their sections', () => {
    const all = pages(NAV)
    const shown = pages(navFor(false))
    expect([...PERSONAL_PAGES].every((p) => all.includes(p))).toBe(true)
    expect(shown.filter((p) => PERSONAL_PAGES.has(p))).toEqual([])
    expect(new Set(shown)).toEqual(new Set(all.filter((p) => !PERSONAL_PAGES.has(p))))
  })

  it('and out of the jump box', () => {
    expect(matchPages(en, 'notebook', 5).map((p) => p.to)).toContain('/notebook')
    expect(matchPages(en, 'notebook', 5, false).map((p) => p.to)).not.toContain('/notebook')
    expect(matchPages(en, 'labels', 5, false).map((p) => p.to)).not.toContain('/labels')
  })
})
