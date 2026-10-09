import { useState } from 'react'
import type { Book } from '../api/types'
import { useLocale } from '../context/localeContext'
import { bookName } from '../lib/names'

interface HeatmapProps<K extends string | number> {
  /** Row / column labels by key. */
  names: Map<K, string>
  /** Keys in display order. */
  order: K[]
  /** 0..1 intensity of a cell, or undefined for no data. */
  value: (a: K, b: K) => number | undefined
  title: (a: K, b: K) => string
  selected: string | null
  onSelect: (key: string | null) => void
  label: string
}

interface Props extends Omit<HeatmapProps<number>, 'names'> {
  books: Book[]
}

/** The heatmap over books, labelled with their names in the interface language. */
export function BookHeatmap({ books, ...rest }: Props) {
  const { locale } = useLocale()
  return <Heatmap names={new Map(books.map((b) => [b.book_id, bookName(b, locale)]))} {...rest} />
}

/**
 * Key x key SVG heatmap; a cell key is `{a}-{b}` (row key, column key). With keyboard focus the
 * arrow keys move a cursor over the cells (its title is announced) and Enter / Space selects.
 */
export function Heatmap<K extends string | number>({ names: name, order, value, title, selected, onSelect, label }: HeatmapProps<K>) {
  const { m } = useLocale()
  const [hover, setHover] = useState<string>()
  const [cursor, setCursor] = useState<[number, number]>()
  const n = order.length
  const cursorKey = cursor && `${order[cursor[0]]}-${order[cursor[1]]}`
  const onKey = (e: React.KeyboardEvent<SVGSVGElement>) => {
    const move = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key]
    if (move && n > 1) {
      e.preventDefault()
      setCursor((c) => {
        if (!c) return [0, 1]
        let [i, j] = [(c[0] + move[0] + n) % n, (c[1] + move[1] + n) % n]
        if (i === j) [i, j] = [(i + move[0] + n) % n, (j + move[1] + n) % n] // skip the diagonal
        return [i, j]
      })
    } else if ((e.key === 'Enter' || e.key === ' ') && cursorKey) {
      e.preventDefault()
      onSelect(selected === cursorKey ? null : cursorKey)
    }
  }
  const cell = 14
  const pad = 96
  const size = pad + order.length * cell
  return (
    // left to right in either interface language (rows and columns keep their order)
    <div className="table-wrap" dir="ltr">
      <svg
        width={size + 36}
        height={size}
        role="img"
        aria-label={m.ov.chart.heatmapKeys(label)}
        tabIndex={0}
        onKeyDown={onKey}
        onBlur={() => setCursor(undefined)}
      >
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
                className={`aff-cell ${selected === key || hover === key || cursorKey === key ? 'on' : ''}`}
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
      {cursor && (
        <p className="sr-only" aria-live="polite">
          {title(order[cursor[0]], order[cursor[1]])}
        </p>
      )}
    </div>
  )
}
