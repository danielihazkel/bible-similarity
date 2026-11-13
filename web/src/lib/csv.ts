export type CsvRow = Record<string, string | number | boolean | null | undefined>

// what an export leaves out (the texts), and what names a nested object: as the server's
// `/export/{list}.csv` does (`api/routes/export.py`), so a page's rows and a whole list's match
const SKIPPED = new Set(['verse', 'verses', 'a_verse', 'b_verse', 'text_display', 'display_tokens', 'matrix', 'marks'])
const LABELS = ['label_en', 'he_lemma', 'label', 'ref', 'letter']

function labelOf(v: Record<string, unknown>): unknown {
  for (const k of LABELS) if (k in v) return v[k]
  return undefined
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

/** One item of a list as a CSV row: a unit becomes its label, a lemma its Hebrew form, a verse its
 * reference where the item has no label of its own; other nested objects become `outer.inner` columns, lists their values joined by `; `;
 * verse texts are left out. */
export function flattenItem(item: Record<string, unknown>, prefix = ''): CsvRow {
  const out: CsvRow = {}
  // an item with no label of its own is named by its verse: the verse's reference is its key
  const byVerse = !['label_en', 'label', 'ref'].some((k) => k in item)
  for (const [k, v] of Object.entries(item)) {
    const name = prefix + k
    if (byVerse && k === 'verse' && isRecord(v) && 'ref' in v) {
      out[name] = v.ref as CsvRow[string]
      continue
    }
    if (SKIPPED.has(k)) continue
    if (isRecord(v)) {
      const label = labelOf(v)
      if (label !== undefined) out[name] = label as CsvRow[string]
      else Object.assign(out, flattenItem(v, `${name}.`))
    } else if (Array.isArray(v)) {
      const parts = v.flatMap((x) => (isRecord(x) ? (labelOf(x) !== undefined ? [labelOf(x)] : []) : Array.isArray(x) ? [] : [x]))
      if (parts.length) out[name] = parts.map(String).join('; ')
    } else out[name] = v as CsvRow[string]
  }
  return out
}

/** The rows of a page of a list: every row has every column (an item may lack a field another has). */
export function flattenItems(items: unknown[]): CsvRow[] {
  const rows = items.map((i) => flattenItem(i as Record<string, unknown>))
  const columns = [...new Set(rows.flatMap((r) => Object.keys(r)))]
  return rows.map((r) => Object.fromEntries(columns.map((c) => [c, r[c]])))
}

/** RFC 4180 CSV: a header from the first row's keys, quotes where needed, CRLF line ends. */
export function toCsv(rows: CsvRow[]): string {
  if (rows.length === 0) return ''
  const cols = Object.keys(rows[0])
  const cell = (v: CsvRow[string]) => {
    const s = v === null || v === undefined ? '' : String(v)
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [cols.join(','), ...rows.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\r\n') + '\r\n'
}

/** Save rows as a UTF-8 CSV (with a BOM, so spreadsheet apps read the Hebrew correctly). */
export function downloadCsv(filename: string, rows: CsvRow[]): void {
  downloadText(filename, ['﻿', toCsv(rows)], 'text/csv;charset=utf-8')
}

/** Save text as a file in the browser. */
export function downloadText(filename: string, parts: string[], type: string): void {
  const blob = new Blob(parts, { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** A cell's text as shown, without what only a popover shows (`data-nocsv`: a term's entry). */
function shown(c: HTMLTableCellElement): string {
  if (!c.querySelector('[data-nocsv]')) return c.textContent?.trim() ?? ''
  const k = c.cloneNode(true) as HTMLElement
  k.querySelectorAll('[data-nocsv]').forEach((e) => e.remove())
  return k.textContent?.trim() ?? ''
}

/** The rows of a rendered table as CSV rows: the last header row names the columns (a repeated
 * name gets a number), each body row's cells give their text as shown. */
export function tableRows(table: HTMLTableElement): CsvRow[] {
  const head = table.tHead?.rows[table.tHead.rows.length - 1]
  const seen = new Map<string, number>()
  const names = [...(head?.cells ?? [])].map((c, i) => {
    const base = shown(c) || `column ${i + 1}`
    const n = (seen.get(base) ?? 0) + 1
    seen.set(base, n)
    return n > 1 ? `${base} ${n}` : base
  })
  const body = [...table.tBodies].flatMap((b) => [...b.rows])
  return body.map((r) => {
    const row: CsvRow = {}
    ;[...r.cells].forEach((c, i) => {
      row[names[i] ?? `column ${i + 1}`] = shown(c)
    })
    return row
  })
}
