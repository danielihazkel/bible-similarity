import { type CsvRow, downloadCsv } from '../lib/csv'

/** "Export page (CSV)": the rows currently listed, with their links' references. */
export function ExportCsv({ filename, rows }: { filename: string; rows: () => CsvRow[] }) {
  return (
    <button type="button" className="linkish export-csv" onClick={() => downloadCsv(filename, rows())}>
      Export page (CSV)
    </button>
  )
}
