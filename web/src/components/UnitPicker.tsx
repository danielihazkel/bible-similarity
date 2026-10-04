import { useState } from 'react'
import { useBooks, useUnit, useUnits } from '../api/hooks'
import type { UnitType } from '../api/types'
import { unitTypeLabel } from '../lib/format'

const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha', 'verse']

interface Props {
  label: string
  value: string | undefined
  onChange: (unitId: string) => void
}

/**
 * Unit type → book → unit, from /api/books and /api/units/{type}?book=. Type and book follow the
 * selected unit until the user changes them (render with `key={value}` to reset on a new value).
 */
export function UnitPicker({ label, value, onChange }: Props) {
  const current = useUnit(value).data?.unit
  const [typeChoice, setType] = useState<UnitType>()
  const [bookChoice, setBook] = useState<number>()
  const type = typeChoice ?? current?.unit_type ?? 'chapter'
  const book = bookChoice ?? current?.book_id

  const books = useBooks().data ?? []
  const torah = books.filter((b) => b.section === 'Torah').map((b) => b.book_id)
  const visibleBooks = type === 'parasha' ? books.filter((b) => torah.includes(b.book_id)) : books
  const units = useUnits(type, book).data ?? []

  return (
    <fieldset className="picker">
      <legend>{label}</legend>
      <select aria-label={`${label} unit type`} value={type} onChange={(e) => setType(e.target.value as UnitType)}>
        {TYPES.map((t) => (
          <option key={t} value={t}>
            {unitTypeLabel(t)}
          </option>
        ))}
      </select>
      <select
        aria-label={`${label} book`}
        value={book ?? ''}
        onChange={(e) => setBook(e.target.value === '' ? undefined : Number(e.target.value))}
      >
        <option value="">Book…</option>
        {visibleBooks.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {b.name} · {b.he_name}
          </option>
        ))}
      </select>
      <select
        aria-label={`${label} unit`}
        value={units.some((u) => u.unit_id === value) ? value : ''}
        disabled={!units.length}
        onChange={(e) => e.target.value && onChange(e.target.value)}
      >
        <option value="">{unitTypeLabel(type)}…</option>
        {units.map((u) => (
          <option key={u.unit_id} value={u.unit_id}>
            {u.label_en}
          </option>
        ))}
      </select>
    </fieldset>
  )
}
