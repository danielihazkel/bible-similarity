import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { getJson } from '../api/client'
import { useBooks, useResolve, useUnit, useUnits } from '../api/hooks'
import type { ResolveResponse, UnitDetail, UnitType } from '../api/types'
import { useLocale } from '../context/localeContext'
import { matchBooks } from '../lib/books'
import { bookName, bookOption, unitLabel } from '../lib/names'
import '../styles/components/UnitPicker.css'

const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha', 'verse']
const MAX_BOOKS = 4
const DEBOUNCE_MS = 150

interface Props {
  label: string
  value: string | undefined
  onChange: (unitId: string) => void
}

/**
 * Unit type → book → unit, from /api/books and /api/units/{type}?book=, or a typed reference
 * (`Gen 1:1`, `בראשית א א`, `Ps 23`) resolved by /api/resolve. The reference field suggests as it
 * is typed, as the jump box does: the passage the text names so far, and the books a name of which
 * starts so (choosing one writes its name, ready for the chapter). Type and book follow the
 * selected unit until the user changes them (render with `key={value}` to reset on a new value).
 */
export function UnitPicker({ label, value, onChange }: Props) {
  const { m, locale } = useLocale()
  const currentDetail = useUnit(value).data
  const current = currentDetail?.unit
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
  const chapter = type === 'verse' ? (chapterChoice ?? currentChapter(currentDetail) ?? 1) : undefined
  const unitsQuery = useUnits(type, book, chapter)
  const units = unitsQuery.data ?? []

  const queryClient = useQueryClient()
  const [ref, setRef] = useState('')
  const [refStatus, setRefStatus] = useState<string>()
  const goTo = async (e: FormEvent) => {
    e.preventDefault()
    const q = ref.trim()
    if (!q) return
    setRefStatus(m.picker.lookingUp)
    try {
      const r = await queryClient.fetchQuery({
        queryKey: ['resolve', q],
        queryFn: ({ signal }) => getJson<ResolveResponse>('/resolve', { q }, signal),
        staleTime: Infinity,
      })
      if (r.unit) {
        setRefStatus(undefined)
        onChange(r.unit.unit_id)
      } else setRefStatus(m.picker.notRef(q))
    } catch {
      setRefStatus(m.picker.unreachable)
    }
  }
  const error = booksQuery.isError ? m.picker.booksFailed : unitsQuery.isError ? m.picker.unitsFailed : undefined

  // suggestions under the reference field, once the typing pauses
  const listId = useId()
  const refInput = useRef<HTMLInputElement>(null)
  const [settled, setSettled] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(ref.trim()), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [ref])
  const resolved = useResolve(settled)
  const named = settled === ref.trim() && resolved.data?.query === settled ? resolved.data.unit : undefined
  const suggestions: { key: string; label: string; tag?: string; pick: () => void }[] = [
    ...(named
      ? [
          {
            key: named.unit_id,
            label: unitLabel(named, locale),
            pick: () => {
              setRef('')
              setOpen(false)
              onChange(named.unit_id)
            },
          },
        ]
      : []),
    // a book whose name is already written out, with the space after it, is not offered again
    ...matchBooks(books, ref, MAX_BOOKS)
      .filter(({ exact }) => !(exact && /\s$/.test(ref)))
      .map(({ book }) => ({
        key: `book-${book.book_id}`,
        label: bookName(book, locale),
        tag: m.picker.bookTag,
        pick: () => {
          setRef(`${bookName(book, locale)} `)
          setActive(-1)
          refInput.current?.focus()
        },
      })),
  ]
  const listed = open && suggestions.length > 0
  const marked = Math.min(active, suggestions.length - 1)
  const onRefKey = (e: KeyboardEvent) => {
    if (!listed) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = suggestions.length
      setActive(e.key === 'ArrowDown' ? (marked + 1) % n : marked <= 0 ? n - 1 : marked - 1)
    } else if (e.key === 'Enter' && marked >= 0) {
      e.preventDefault()
      suggestions[marked].pick()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
    }
  }

  return (
    <fieldset className="picker">
      <legend>{label}</legend>
      <select aria-label={m.picker.unitType(label)} value={type} onChange={(e) => setType(e.target.value as UnitType)}>
        {TYPES.map((t) => (
          <option key={t} value={t}>
            {m.units.type(t)}
          </option>
        ))}
      </select>
      <select
        aria-label={m.picker.book(label)}
        value={book ?? ''}
        onChange={(e) => setBook(e.target.value === '' ? undefined : Number(e.target.value))}
      >
        <option value="">{m.picker.bookPlaceholder}</option>
        {visibleBooks.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {bookOption(b, locale)}
          </option>
        ))}
      </select>
      {type === 'verse' && book !== undefined && nChapters > 0 && (
        <select aria-label={m.picker.chapter(label)} value={chapter} onChange={(e) => setChapter(Number(e.target.value))}>
          {Array.from({ length: nChapters }, (_, i) => i + 1).map((c) => (
            <option key={c} value={c}>
              {m.units.chapterN(c)}
            </option>
          ))}
        </select>
      )}
      <select
        aria-label={m.picker.unit(label)}
        value={units.some((u) => u.unit_id === value) ? value : ''}
        disabled={!units.length}
        aria-busy={unitsQuery.isFetching}
        onChange={(e) => e.target.value && onChange(e.target.value)}
      >
        <option value="">{unitsQuery.isFetching ? m.status.loading : `${m.units.type(type)}…`}</option>
        {units.map((u) => (
          <option key={u.unit_id} value={u.unit_id}>
            {unitLabel(u, locale)}
          </option>
        ))}
      </select>
      <form className="picker-ref" onSubmit={goTo} role="search">
        <input
          ref={refInput}
          type="text"
          role="combobox"
          aria-label={m.picker.reference(label)}
          aria-expanded={listed}
          aria-controls={listed ? listId : undefined}
          aria-autocomplete="list"
          aria-activedescendant={listed && marked >= 0 ? `${listId}-${marked}` : undefined}
          autoComplete="off"
          spellCheck={false}
          placeholder={m.picker.refPlaceholder}
          value={ref}
          onChange={(e) => {
            setRef(e.target.value)
            setRefStatus(undefined)
            setActive(-1)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onRefKey}
        />
        <button type="submit">{m.picker.go}</button>
        {listed && (
          <div id={listId} className="picker-suggest" role="listbox" aria-label={m.picker.suggestions(label)}>
            {suggestions.map((s, i) => (
              <div
                key={s.key}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === marked}
                className="picker-option"
                onMouseMove={() => i !== marked && setActive(i)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={s.pick}
              >
                <span>{s.label}</span>
                {s.tag && <span className="muted small">{s.tag}</span>}
              </div>
            ))}
          </div>
        )}
      </form>
      {(error ?? refStatus) && (
        <p className={`picker-status${error ? ' error' : ''}`} role={error ? 'alert' : 'status'}>
          {error ?? refStatus}
        </p>
      )}
    </fieldset>
  )
}

/** The chapter of a verse unit (from its verse, not its label: labels differ per language). */
function currentChapter(d: UnitDetail | undefined): number | undefined {
  return d?.unit.unit_type === 'verse' ? d.verses[0]?.chapter : undefined
}
