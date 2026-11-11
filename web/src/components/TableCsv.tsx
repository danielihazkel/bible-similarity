import { type HTMLAttributes, type ReactNode, type RefObject, useEffect, useRef, useState } from 'react'
import { useT } from '../context/localeContext'
import { downloadCsv, tableRows } from '../lib/csv'
import '../styles/components/TableCsv.css'

/** The heading a table stands under: the nearest one before it in the page. */
function headingBefore(el: Element): string {
  for (let node: Element | null = el; node && node.tagName !== 'MAIN'; node = node.parentElement) {
    for (let sib = node.previousElementSibling; sib; sib = sib.previousElementSibling) {
      const h = sib.matches('h1, h2, h3, h4, h5, h6') ? sib : [...sib.querySelectorAll('h1, h2, h3, h4, h5, h6')].pop()
      const text = h?.textContent?.trim()
      if (text) return text
    }
  }
  return ''
}

/**
 * A table's scroll wrapper (`.table-wrap`). A wrapper that scrolls sideways has to be reachable
 * from the keyboard (WCAG 2.1.1; axe `scrollable-region-focusable`): while the table is wider
 * than its wrapper, the wrapper is a tab stop and a region named after the heading above it. A
 * table that fits adds no tab stop. A caller's own `tabIndex`, `role` and `aria-label` win.
 */
export function TableWrap({
  children,
  wrapRef,
  ...given
}: { children: ReactNode; wrapRef?: RefObject<HTMLDivElement | null> } & HTMLAttributes<HTMLDivElement>) {
  const m = useT()
  const own = useRef<HTMLDivElement>(null)
  const ref = wrapRef ?? own
  // the region's name while the wrapper scrolls, `null` while the table fits
  const [name, setName] = useState<string | null>(null)
  // measured again after every render (new rows, another table) and on every resize; the
  // observer reports once on `observe`, so the first measure needs no call of its own
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => setName(el.scrollWidth > el.clientWidth + 1 ? headingBefore(el) || m.csv.region : null))
    observer.observe(el)
    if (el.firstElementChild) observer.observe(el.firstElementChild)
    return () => observer.disconnect()
  })
  const region = name === null ? {} : { tabIndex: 0, role: 'region', 'aria-label': name }
  return (
    <div className="table-wrap" ref={ref} {...region} {...given}>
      {children}
    </div>
  )
}

/** A table in its scroll wrapper, with "Export table (CSV)" above it: what the table shows. The
 * wrapper keeps the attributes a scrollable table needs (`tabIndex`, `role`, `aria-label`), and
 * takes them by itself while the table is wider than the page (`TableWrap`). */
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
      <TableWrap wrapRef={wrap} {...wrapper}>
        {children}
      </TableWrap>
    </>
  )
}
