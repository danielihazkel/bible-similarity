import { type HTMLAttributes, type ReactNode, useRef } from 'react'
import { useT } from '../context/localeContext'
import { downloadCsv, tableRows } from '../lib/csv'

/** A table in its scroll wrapper, with "Export table (CSV)" above it: what the table shows. The
 * wrapper keeps the attributes a scrollable table needs (`tabIndex`, `role`, `aria-label`). */
export function TableCsv({
  name,
  children,
  ...wrapper
}: { name: string; children: ReactNode } & HTMLAttributes<HTMLDivElement>) {
  const m = useT()
  const wrap = useRef<HTMLDivElement>(null)
  const save = () => {
    const table = wrap.current?.querySelector('table')
    if (table) downloadCsv(`${name}.csv`, tableRows(table))
  }
  return (
    <>
      <p className="table-csv">
        <button type="button" className="linkish export-csv" onClick={save}>
          {m.csv.table}
        </button>
      </p>
      <div className="table-wrap" ref={wrap} {...wrapper}>
        {children}
      </div>
    </>
  )
}
