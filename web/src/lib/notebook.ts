// The notebook as a Markdown file (DESIGN.md §16.47): written in the browser, so its wording comes
// from the interface catalogs like everything else on screen.

import type { NotebookCollection, NotebookEntry } from '../api/types'

export interface MarkdownText {
  title: string
  exported: (date: string) => string
  collections: string
}

/** One section per entry: the passage, a verse's text as a quotation, the note, its collections. */
export function notebookMarkdown(
  entries: NotebookEntry[],
  collections: NotebookCollection[],
  heading: string | null,
  t: MarkdownText,
  locale: 'en' | 'he',
  date: string,
): string {
  const name = new Map(collections.map((c) => [c.collection_id, c.name]))
  const out = [`# ${heading ? `${t.title}: ${heading}` : t.title}`, '', t.exported(date), '']
  for (const e of entries) {
    const label = locale === 'he' ? e.unit.label_he : `${e.unit.label_en} · ${e.unit.label_he}`
    out.push(`## ${label}`, '')
    if (e.verse) out.push(`> ${e.verse.text_display}`, '')
    if (e.note.trim()) out.push(e.note.trim(), '')
    const cs = e.collections.map((c) => name.get(c)).filter((c): c is string => !!c)
    if (cs.length) out.push(`*${t.collections}: ${cs.join(', ')}*`, '')
  }
  return out.join('\n')
}

/** Entries whose note or passage label holds the text (case-insensitive; empty: all). */
export function filterEntries(entries: NotebookEntry[], text: string): NotebookEntry[] {
  const q = text.trim().toLowerCase()
  if (!q) return entries
  return entries.filter((e) => [e.note, e.unit.label_en, e.unit.label_he].some((s) => s.toLowerCase().includes(q)))
}
