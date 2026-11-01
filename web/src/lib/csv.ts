export type CsvRow = Record<string, string | number | boolean | null | undefined>

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

/** The rows of a rendered table as CSV rows: the last header row names the columns (a repeated
 * name gets a number), each body row's cells give their text as shown. */
export function tableRows(table: HTMLTableElement): CsvRow[] {
  const head = table.tHead?.rows[table.tHead.rows.length - 1]
  const seen = new Map<string, number>()
  const names = [...(head?.cells ?? [])].map((c, i) => {
    const base = c.textContent?.trim() || `column ${i + 1}`
    const n = (seen.get(base) ?? 0) + 1
    seen.set(base, n)
    return n > 1 ? `${base} ${n}` : base
  })
  const body = [...table.tBodies].flatMap((b) => [...b.rows])
  return body.map((r) => {
    const row: CsvRow = {}
    ;[...r.cells].forEach((c, i) => {
      row[names[i] ?? `column ${i + 1}`] = c.textContent?.trim() ?? ''
    })
    return row
  })
}
