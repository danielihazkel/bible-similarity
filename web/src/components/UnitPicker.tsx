import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { getJson } from '../api/client'
import { useBooks, useUnit, useUnits } from '../api/hooks'
import type { ResolveResponse, UnitSummary, UnitType } from '../api/types'
import { unitTypeLabel } from '../lib/format'

const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha', 'verse']

interface Props {
  label: string
  value: string | undefined
  onChange: (unitId: string) => void
}

/**
 * Unit type → book → unit, from /api/books and /api/units/{type}?book=, or a typed reference
 * (`Gen 1:1`, `בראשית א א`, `Ps 23`) resolved by /api/resolve. Type and book follow the selected
 * unit until the user changes them (render with `key={value}` to reset on a new value).
 */
export function UnitPicker({ label, value, onChange }: Props) {
  const current = useUnit(value).data?.unit
  const [typeChoice, setType] = useState<UnitType>()
  const [bookChoice, setBook] = useState<number>()
  const type = typeChoice ?? current?.unit_type ?? 'chapter'
  const book = bookChoice ?? current?.book_id

  const booksQuery = useBooks()
  const books = booksQuery.data ?? []
  const torah = books.filter((b) => b.section === 'Torah').map((b) => b.book_id)
  const visibleBooks = type === 'parasha' ? books.filter((b) => torah.includes(b.book_id)) : books
  // verses: a chapter at a time (a whole book's verses make a select of thousands of options)
  const nChapters = books.find((b) => b.book_id === book)?.n_chapters ?? 0
  const [chapterChoice, setChapter] = useState<number>()
  const chapter = type === 'verse' ? (chapterChoice ?? currentChapter(current) ?? 1) : undefined
  const unitsQuery = useUnits(type, book, chapter)
  const units = unitsQuery.data ?? []

  const queryClient = useQueryClient()
  const [ref, setRef] = useState('')
  const [refStatus, setRefStatus] = useState<string>()
  const goTo = async (e: FormEvent) => {
    e.preventDefault()
    const q = ref.trim()
    if (!q) return
    setRefStatus('Looking up…')
    try {
      const r = await queryClient.fetchQuery({
        queryKey: ['resolve', q],
        queryFn: ({ signal }) => getJson<ResolveResponse>('/resolve', { q }, signal),
        staleTime: Infinity,
      })
      if (r.unit) {
        setRefStatus(undefined)
        onChange(r.unit.unit_id)
      } else setRefStatus(`Not a reference: ${q}`)
    } catch {
      setRefStatus('Could not reach the API')
    }
  }
  const error = booksQuery.isError ? 'Could not load books' : unitsQuery.isError ? 'Could not load units' : undefined

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
      {type === 'verse' && book !== undefined && nChapters > 0 && (
        <select aria-label={`${label} chapter`} value={chapter} onChange={(e) => setChapter(Number(e.target.value))}>
          {Array.from({ length: nChapters }, (_, i) => i + 1).map((c) => (
            <option key={c} value={c}>
              Chapter {c}
            </option>
          ))}
        </select>
      )}
      <select
        aria-label={`${label} unit`}
        value={units.some((u) => u.unit_id === value) ? value : ''}
        disabled={!units.length}
        aria-busy={unitsQuery.isFetching}
        onChange={(e) => e.target.value && onChange(e.target.value)}
      >
        <option value="">{unitsQuery.isFetching ? 'Loading…' : `${unitTypeLabel(type)}…`}</option>
        {units.map((u) => (
          <option key={u.unit_id} value={u.unit_id}>
            {u.label_en}
          </option>
        ))}
      </select>
      <form className="picker-ref" onSubmit={goTo} role="search">
        <input
          type="text"
          aria-label={`${label} reference`}
          placeholder="Gen 1:1 · בראשית א"
          value={ref}
          onChange={(e) => {
            setRef(e.target.value)
            setRefStatus(undefined)
          }}
        />
        <button type="submit">Go</button>
      </form>
      {(error ?? refStatus) && (
        <p className={`picker-status${error ? ' error' : ''}`} role={error ? 'alert' : 'status'}>
          {error ?? refStatus}
        </p>
      )}
    </fieldset>
  )
}

/** The chapter of a verse unit, from its label ("Genesis 1:1" -> 1). */
function currentChapter(u: UnitSummary | undefined): number | undefined {
  if (u?.unit_type !== 'verse') return undefined
  const m = /(\d+):\d+$/.exec(u.label_en)
  return m ? Number(m[1]) : undefined
}
