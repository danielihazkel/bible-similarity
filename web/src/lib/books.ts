// Books found by the start of a name: the jump box and the unit picker's reference field share it.

import type { Book } from '../api/types'

/** Books by the start of a name ("gen" → Genesis, "sam" → both Samuels, "שמ" → שמות): the name
 * in either language, a word of the English one, or the OSIS code. `exact`: the whole name. */
export function matchBooks(books: Book[], q: string, max: number): { book: Book; exact: boolean }[] {
  const s = q.trim().toLowerCase()
  if (s.length < 2) return []
  return books
    .flatMap((book) => {
      const en = book.name.toLowerCase()
      const names = [en, book.he_name, book.osis.toLowerCase()]
      const exact = names.includes(s)
      const starts = names.some((n) => n.startsWith(s)) || en.split(' ').some((w) => w.length > 2 && w.startsWith(s))
      return starts ? [{ book, exact }] : []
    })
    .slice(0, max)
}
