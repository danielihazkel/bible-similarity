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
  const blob = new Blob(['﻿', toCsv(rows)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
