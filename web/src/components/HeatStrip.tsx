import { Link, useNavigate } from 'react-router'

// Chapters as squares, a row of them per book (the divine names, §16.65; rabbinic reception,
// §16.77): each square a chapter, its colour the page's measure, a click reads it.

export const PER_ROW = 50 // chapters in one row of a book's strip
export const CELL = 10
export const STEP = 12 // a cell and the 2px surface gap after it

export interface HeatCell {
  key: string
  cls: string // the page's class for the cell's colour step
  title: string // its tooltip: the chapter and its measure
  to: string // where a click goes
  cut?: boolean // a mark before it (a book's change point)
}

/** One book's chapters; `prefix` names the page's classes (`{prefix}-cell`, `{prefix}-cut`). */
export function HeatCells({ cells, label, prefix }: { cells: HeatCell[]; label: string; prefix: string }) {
  const navigate = useNavigate()
  const rows = Math.ceil(cells.length / PER_ROW)
  const width = Math.min(cells.length, PER_ROW) * STEP
  return (
    <svg className="heat-cells" viewBox={`0 0 ${width} ${rows * STEP}`} width={width} role="img" aria-label={label}>
      {cells.map((c, i) => {
        const x = (i % PER_ROW) * STEP
        const y = Math.floor(i / PER_ROW) * STEP
        return (
          <g key={c.key}>
            <rect className={`${prefix}-cell ${c.cls}`} x={x} y={y} width={CELL} height={CELL} rx={2} onClick={() => navigate(c.to)}>
              <title>{c.title}</title>
            </rect>
            {c.cut && <rect className={`${prefix}-cut`} x={x - 2} y={y - 1} width={2} height={CELL + 2} />}
          </g>
        )
      })}
    </svg>
  )
}

export interface HeatRow {
  key: number
  name: string // the book's name
  to: string // the book's link
  cells: HeatCell[]
  label: string // the book's strip, for a screen reader
}

/** Every book's strip, its name beside it. */
export function HeatStrip({ rows, prefix }: { rows: HeatRow[]; prefix: string }) {
  return (
    <div className="heat-strip">
      {rows.map((r) => (
        <div key={r.key} className="heat-row">
          <Link className="heat-book" to={r.to}>
            {r.name}
          </Link>
          <HeatCells cells={r.cells} label={r.label} prefix={prefix} />
        </div>
      ))}
    </div>
  )
}
