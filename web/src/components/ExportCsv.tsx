import { apiUrl, type Params } from '../api/client'
import { useT } from '../context/localeContext'
import { type CsvRow, downloadCsv } from '../lib/csv'

/**
 * "Export page (CSV)": the rows currently listed, with their links' references; with `all`, also
 * "Export all": every row under the same filters, written by the API (`/api/export/{list}.csv`).
 */
export function ExportCsv({
  filename,
  rows,
  all,
}: {
  filename: string
  rows: () => CsvRow[]
  all?: { list: string; params: Params }
}) {
  const m = useT()
  const { limit: _limit, offset: _offset, ...filters } = all?.params ?? {}
  return (
    <>
      <button type="button" className="linkish export-csv" onClick={() => downloadCsv(filename, rows())}>
        {m.csv.page}
      </button>
      {all && (
        <>
          {' · '}
          <a className="export-csv" href={apiUrl(`/export/${all.list}.csv`, filters)} download>
            {m.csv.all}
          </a>
        </>
      )}
    </>
  )
}
