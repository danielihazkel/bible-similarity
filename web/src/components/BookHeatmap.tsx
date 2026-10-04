import { useState } from 'react'
import type { Book } from '../api/types'

interface Props {
  books: Book[]
  /** Book ids in display order. */
  order: number[]
  /** 0..1 intensity of a cell, or undefined for no data. */
  value: (a: number, b: number) => number | undefined
  title: (a: number, b: number) => string
  selected: string | null
  onSelect: (key: string | null) => void
  label: string
}

/** Book x book SVG heatmap; a cell key is `{a}-{b}` (row book, column book). */
export function BookHeatmap({ books, order, value, title, selected, onSelect, label }: Props) {
  const [hover, setHover] = useState<string>()
  const name = new Map(books.map((b) => [b.book_id, b.name]))
  const cell = 14
  const pad = 96
  const size = pad + order.length * cell
  return (
    <div className="table-wrap">
      <svg width={size + 36} height={size} role="img" aria-label={label}>
        {order.map((id, i) => (
          <text key={`r${id}`} x={pad - 4} y={pad + i * cell + cell * 0.75} textAnchor="end" className="axis">
            {name.get(id)}
          </text>
        ))}
        {order.map((id, j) => (
          <text key={`c${id}`} transform={`translate(${pad + j * cell + cell * 0.7}, ${pad - 4}) rotate(-60)`} className="axis">
            {name.get(id)}
          </text>
        ))}
        {order.map((a, i) =>
          order.map((b, j) => {
            if (a === b) return null
            const key = `${a}-${b}`
            const v = value(a, b)
            return (
              <rect
                key={key}
                x={pad + j * cell}
                y={pad + i * cell}
                width={cell - 1}
                height={cell - 1}
                className={`aff-cell ${selected === key || hover === key ? 'on' : ''}`}
                style={{ fillOpacity: v === undefined ? 0.03 : 0.06 + 0.94 * v }}
                onMouseEnter={() => setHover(key)}
                onMouseLeave={() => setHover(undefined)}
                onClick={() => onSelect(selected === key ? null : key)}
              >
                <title>{title(a, b)}</title>
              </rect>
            )
          }),
        )}
      </svg>
    </div>
  )
}
