// The notebook as a study page (DESIGN.md §16.47, D151): one standalone HTML file, written in the
// browser like the Markdown, to send, keep or print. Its wording comes from the interface catalogs,
// its direction from the interface language; the verses in the text display chosen on screen.

import type { NotebookCollection, NotebookEntry } from '../api/types'
import { displayForm, joinTokens, type TextMode } from './hebrew'
import { unitLink } from './links'

export interface StudyPageText {
  title: string
  exported: (date: string) => string
  collections: string
  /** the passage's page on the site the file came from */
  open: string
  /** where the verses come from, and their licence (CC-BY-SA asks for it to travel with them) */
  source: string
  madeWith: (site: string) => string
}

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

/** A note's paragraphs (a blank line between them), each line kept. */
const paragraphs = (note: string) =>
  note
    .trim()
    .split(/\n\s*\n/)
    .map((p) => `<p>${esc(p.trim()).replace(/\n/g, '<br>')}</p>`)
    .join('\n')

// light, on white, the Hebrew in the fonts a reader likely has; a page break never inside an entry
const STYLE = `
:root { color-scheme: light; }
body { margin: 0 auto; max-width: 46rem; padding: 2rem 1.25rem 3rem; background: #fff; color: #2a2218;
  font: 16px/1.55 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
h1 { font-size: 1.6rem; margin: 0 0 0.2rem; }
.meta, .cols, footer { color: #6b5d49; font-size: 0.85rem; }
.desc { margin: 0.6rem 0 0; }
ol { list-style: none; padding: 0; margin: 1.5rem 0 0; }
li { border-top: 1px solid #e2d7c3; padding: 1rem 0; break-inside: avoid; }
h2 { font-size: 1.1rem; margin: 0 0 0.4rem; }
h2 a { color: #8a5a1f; text-decoration: underline; text-underline-offset: 0.15em; }
.he-label { font-weight: normal; color: #6b5d49; }
blockquote { margin: 0.4rem 0 0.6rem; padding: 0.4rem 0.8rem; border-inline-start: 3px solid #e2d7c3;
  font-family: 'Ezra SIL', 'SBL Hebrew', 'Noto Serif Hebrew', 'Times New Roman', serif; font-size: 1.35rem; line-height: 1.8; }
.note p { margin: 0.3rem 0; }
footer { border-top: 1px solid #e2d7c3; margin-top: 1.5rem; padding-top: 0.8rem; }
@media print { body { padding: 0; } a { color: inherit; } }
`

/**
 * The entries as a standalone page: the heading (the collection's name and description, if one
 * is chosen), the day, each passage linked to its page on `site`, a verse's text as shown on
 * screen (`mode`), the note, the collections; the verses' source at the foot.
 */
export function studyPage(
  entries: NotebookEntry[],
  collections: NotebookCollection[],
  current: NotebookCollection | undefined,
  t: StudyPageText,
  locale: 'en' | 'he',
  date: string,
  site: string,
  mode: TextMode,
): string {
  const name = new Map(collections.map((c) => [c.collection_id, c.name]))
  const title = current ? `${t.title}: ${current.name}` : t.title
  const items = entries.map((e) => {
    const label =
      locale === 'he'
        ? esc(e.unit.label_he)
        : `${esc(e.unit.label_en)} <span class="he-label" lang="he" dir="rtl">${esc(e.unit.label_he)}</span>`
    const href = esc(site + unitLink(e.unit.unit_id))
    const verse = e.verse
      ? `<blockquote lang="he" dir="rtl">${esc(joinTokens(e.verse.display_tokens.map((w) => displayForm(w, mode))))}</blockquote>`
      : ''
    const note = e.note.trim() ? `<div class="note" dir="auto">${paragraphs(e.note)}</div>` : ''
    const cs = e.collections.map((c) => name.get(c)).filter((c): c is string => !!c)
    const cols = cs.length ? `<p class="cols">${esc(t.collections)}: ${cs.map(esc).join(', ')}</p>` : ''
    return `<li>\n<h2><a href="${href}" title="${esc(t.open)}">${label}</a></h2>\n${verse}\n${note}\n${cols}\n</li>`
  })
  return `<!doctype html>
<html lang="${locale}" dir="${locale === 'he' ? 'rtl' : 'ltr'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>${STYLE}</style>
</head>
<body>
<header>
<h1>${esc(title)}</h1>
<p class="meta">${esc(t.exported(date))}</p>
${current?.description?.trim() ? `<div class="desc" dir="auto">${paragraphs(current.description)}</div>` : ''}
</header>
<ol>
${items.join('\n')}
</ol>
<footer>
<p>${esc(t.source)}</p>
<p>${esc(t.madeWith(site))}</p>
</footer>
</body>
</html>
`
}
