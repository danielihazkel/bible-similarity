import { useQueryClient } from '@tanstack/react-query'
import { type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { getJson } from '../api/client'
import { useBooks, useLemmaLookup, usePersonLookup, usePlaceLookup, useResolve, useServer } from '../api/hooks'
import type { Book, LemmaLookup, LemmaStat, PersonLookup, PersonMatch, PlaceLookup, PlaceMatch, ResolveResponse, UnitSummary } from '../api/types'
import { useLocale } from '../context/localeContext'
import type { Messages } from '../i18n'
import { matchBooks } from '../lib/books'
import { personLink, placeLink, unitLink } from '../lib/links'
import { ALL_PAGES, matchPages, NAV_PAGE, navText, PERSONAL_PAGES } from '../lib/nav'
import { bookName, unitLabel } from '../lib/names'
import { personAbout } from '../lib/people'
import { passageOf, type Recent, usePins, useRecent } from '../lib/recent'
import '../i18n/pages/genealogy'
import '../i18n/pages/places'
import '../styles/components/JumpBox.css'

const MAX_WORDS = 6
const MAX_PLACES = 4
const MAX_PEOPLE = 4
const MAX_PAGES = 6
const MAX_BOOKS = 4
const MAX_RECENT = 5
const DEBOUNCE_MS = 150

type Kind = 'pinned' | 'recentPassages' | 'recentPages' | 'gematria' | 'passage' | 'books' | 'places' | 'words' | 'people' | 'pages' | 'search'
interface Option {
  kind: Kind
  to: string
  label: string
  detail?: string
  hebrew?: boolean
}

// `= 318`, `=אליעזר`: a letter value (Patterns → Gematria)
const GEMATRIA = /^=\s*(\S.*)$/

/** A place named by the whole query comes before the words, unless a word that is not one of its
 * names is commoner (עין the eye before עין the town; ירושלם the city before its name). */
function placesFirst(places: PlaceMatch[], lemmas: LemmaStat[]): boolean {
  const top = places[0]
  if (!top?.exact) return false
  const other = lemmas.find((l) => !top.lemmas.includes(l.lemma))
  return !other || other.n_verses <= top.n_verses
}

/** Nothing typed yet: the pinned pages, the passages and pages opened last (not the one on screen),
 * and the index of every page. */
function startOptions(m: Messages, locale: 'en' | 'he', pins: string[], recent: Recent, pathname: string, personal: boolean): Option[] {
  const page = (kind: Kind) => (to: string): Option[] => {
    const p = personal || !PERSONAL_PAGES.has(to) ? NAV_PAGE.get(to) : undefined
    if (!p) return []
    const { label, hint } = navText(m, p.key)
    return [{ kind, to, label, detail: hint }]
  }
  const here = passageOf(pathname)?.id
  return [
    ...pins.flatMap(page('pinned')),
    ...recent.passages
      .filter((p) => passageOf(p.to)?.id !== here)
      .slice(0, MAX_RECENT)
      .map((p) => ({
        kind: 'recentPassages' as const,
        to: p.to,
        label: locale === 'he' ? p.he : p.en,
        detail: passageOf(p.to)?.view === 'read' ? m.jump.inReader : undefined,
      })),
    ...recent.pages
      .filter((to) => to !== pathname && !pins.includes(to))
      .slice(0, MAX_RECENT)
      .flatMap(page('recentPages')),
    { kind: 'pages', to: ALL_PAGES, label: m.site.allPages },
  ]
}

/** Every choice for a query, best first: a letter value (`= …`), the passage it names, a book named
 * in full, the places and the words (a place named exactly first, to the map), the people (to the
 * family tree), the books a name of which starts so, the pages, a text search. */
function buildOptions(
  m: Messages,
  locale: 'en' | 'he',
  q: string,
  unit: UnitSummary | null | undefined,
  lemmas: LemmaStat[],
  places: PlaceMatch[],
  people: PersonMatch[] = [],
  personal = true,
  books: Book[] = [],
): Option[] {
  const t = m.jump
  if (!q.trim()) return []
  const found = matchBooks(books, q, MAX_BOOKS)
  const volumes = found.map(({ book }) => ({
    kind: 'books' as const,
    to: `/browse/${book.book_id}`,
    label: bookName(book, locale),
    // the Hebrew name isolated, so the count after it stays in its place in a left-to-right line
    detail: locale === 'he' ? m.units.chaptersShort(book.n_chapters) : `\u2068${book.he_name}\u2069 · ${m.units.chaptersShort(book.n_chapters)}`,
  }))
  // a book named in full comes before the words; by the start of its name, after them
  const named = found.some((f) => f.exact)
  const gm = GEMATRIA.exec(q.trim())?.[1]
  const words = lemmas.slice(0, MAX_WORDS).map((l) => ({
    kind: 'words' as const,
    to: `/lemma/${encodeURIComponent(l.lemma)}`,
    label: l.he_lemma,
    detail: `${l.lemma} · ${t.verses(l.n_verses)}`,
    hebrew: true,
  }))
  const sites = places.slice(0, MAX_PLACES).map((p) => ({
    kind: 'places' as const,
    to: placeLink(p.place_id),
    label: p.he,
    detail: t.place(p.kind ? m.pl.kindOne[p.kind] : null, t.verses(p.n_verses), locale === 'he' ? p.first_label_he : p.first_label),
    hebrew: true,
  }))
  const persons = people.slice(0, MAX_PEOPLE).map((x) => ({
    kind: 'people' as const,
    to: personLink(x.person_id),
    label: x.he,
    detail: personAbout(x, m.gt, locale) || undefined,
    hebrew: true,
  }))
  return [
    ...(gm ? [{ kind: 'gematria' as const, to: `/gematria?q=${encodeURIComponent(gm)}`, label: t.gematriaOf(gm) }] : []),
    ...(unit ? [{ kind: 'passage' as const, to: unitLink(unit.unit_id), label: unitLabel(unit, locale) }] : []),
    ...(named ? volumes : []),
    ...(placesFirst(places, lemmas) ? [...sites, ...words] : [...words, ...sites]),
    ...persons,
    ...(named ? [] : volumes),
    ...matchPages(m, q, MAX_PAGES, personal).map((p) => ({ kind: 'pages' as const, to: p.to, label: p.label, detail: p.hint })),
    { kind: 'search', to: `/search?q=${encodeURIComponent(q.trim())}`, label: t.searchFor(q.trim()) },
  ]
}

/** Ctrl+K: a passage by its reference, a book by the start of its name, a word by its form or
 * Strong's number, a place by its name (to the map), a person by their name (to the family tree), a
 * page by its name, or else a search of the text; before anything is typed, the pinned pages and
 * what was opened last. A modal combobox: arrows move, Enter opens, Escape closes. */
export function JumpBox({ onClose }: { onClose: () => void }) {
  const t = useLocale().m.jump
  return (
    <div
      className="jump-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="jump" role="dialog" aria-modal="true" aria-label={t.label}>
        <JumpField onDone={onClose} />
      </div>
    </div>
  )
}

/** The jump box's field and its list of choices. In the box (the default) the list is always there,
 * with the pinned and recent pages before anything is typed, and the field holds the focus.
 * `inline` (the start page): the list drops under the field while something is typed in it, Escape
 * clears the field, and Tab moves on. */
export function JumpField({ onDone, inline = false }: { onDone?: () => void; inline?: boolean }) {
  const { m, locale } = useLocale()
  const t = m.jump
  const navigate = useNavigate()
  const client = useQueryClient()
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const [q, setQ] = useState('')
  const [settled, setSettled] = useState('')
  const [active, setActive] = useState(0)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(q.trim()), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [q])
  // in the box, focus moves in on open and back to where it was on close
  useEffect(() => {
    if (inline) return
    const before = document.activeElement as HTMLElement | null
    input.current?.focus()
    return () => before?.focus?.()
  }, [inline])

  const { personal } = useServer()
  const { pathname } = useLocation()
  const pins = usePins()
  const recent = useRecent()
  const books = useBooks().data ?? []
  const resolve = useResolve(settled)
  const lemmas = useLemmaLookup(settled)
  const places = usePlaceLookup(settled)
  const people = usePersonLookup(settled)
  const unit = resolve.data?.query === settled ? resolve.data.unit : undefined
  const words = lemmas.data?.query === settled ? lemmas.data.items : []
  const sites = places.data?.query === settled ? places.data.items : []
  const persons = people.data?.query === settled ? people.data.items : []
  const options = buildOptions(m, locale, settled === q.trim() ? q : '', unit, words, sites, persons, personal, books)
  // the start page lists the pinned and recent ones itself
  const shown = !q.trim()
    ? inline
      ? []
      : startOptions(m, locale, pins, recent, pathname, personal)
    : options.length > 0
      ? options
      : buildOptions(m, locale, q, undefined, [], [], [], personal, books)
  const current = Math.min(active, shown.length - 1)

  const go = (o: Option | undefined) => {
    if (!o) return
    setQ('')
    onDone?.()
    navigate(o.to)
  }
  // Enter before the lookups have caught up with the typing: look the query up now
  const goNow = async () => {
    const s = q.trim()
    if (!s) return
    const [r, l, p, f] = await Promise.all([
      client.fetchQuery({ queryKey: ['resolve', s], queryFn: ({ signal }) => getJson<ResolveResponse>('/resolve', { q: s }, signal) }),
      client.fetchQuery({ queryKey: ['lemma-lookup', s], queryFn: ({ signal }) => getJson<LemmaLookup>('/lemmas', { q: s }, signal) }),
      client.fetchQuery({ queryKey: ['place-lookup', s], queryFn: ({ signal }) => getJson<PlaceLookup>('/places/lookup', { q: s }, signal) }),
      client.fetchQuery({ queryKey: ['person-lookup', s], queryFn: ({ signal }) => getJson<PersonLookup>('/genealogy/lookup', { q: s }, signal) }),
    ]).catch(() => [undefined, undefined, undefined, undefined] as const)
    go(buildOptions(m, locale, s, r?.unit, l?.items ?? [], p?.items ?? [], f?.items ?? [], personal, books)[0])
  }

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (inline && !q) return
      e.preventDefault()
      if (inline) setQ('')
      else onDone?.()
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = shown.length
      if (n) setActive((current + (e.key === 'ArrowDown' ? 1 : n - 1)) % n)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (settled === q.trim() && !resolve.isFetching && !lemmas.isFetching && !places.isFetching && !people.isFetching) go(shown[current])
      else void goNow()
    } else if (e.key === 'Tab' && !inline) {
      e.preventDefault() // the input is the dialog's one stop; the list is reached with the arrows
    }
  }

  // the groups in the order of their options (places before or after the words)
  const groups = [...new Set(shown.map((o) => o.kind))]
  const heading: Record<Kind, string> = {
    pinned: t.pinned,
    recentPassages: t.recentPassages,
    recentPages: t.recentPages,
    gematria: t.gematria,
    passage: t.passage,
    books: t.books,
    places: t.places,
    words: t.words,
    people: t.people,
    pages: t.pages,
    search: t.search,
  }
  const optionId = (i: number) => `${id}-o${i}`
  // inline, the list is there while something is typed in the focused field
  const listed = shown.length > 0 && (!inline || open)
  const field = (
    <input
      ref={input}
      className="jump-input"
      type="text"
      role="combobox"
      aria-label={t.label}
      aria-expanded={listed}
      aria-controls={listed || !inline ? `${id}-list` : undefined}
      aria-autocomplete="list"
      aria-activedescendant={listed ? optionId(current) : undefined}
      placeholder={t.placeholder}
      value={q}
      spellCheck={false}
      autoComplete="off"
      onChange={(e) => {
        setQ(e.target.value)
        setActive(0)
        setOpen(true)
      }}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onKeyDown={onKey}
    />
  )
  const list = (
    <div id={`${id}-list`} className="jump-list" role="listbox" aria-label={t.label}>
      {groups.map((g) => {
        const items = shown.map((o, i) => [o, i] as const).filter(([o]) => o.kind === g)
        if (items.length === 0) return null
        return (
          <div key={g} role="group" aria-labelledby={`${id}-${g}`}>
            <div id={`${id}-${g}`} className="jump-heading" role="presentation">
              {heading[g]}
            </div>
            {items.map(([o, i]) => (
              <div
                key={o.to}
                id={optionId(i)}
                role="option"
                aria-selected={i === current}
                className="jump-option"
                onMouseMove={() => i !== current && setActive(i)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => go(o)}
              >
                <span className={o.hebrew ? 'he' : undefined} dir={o.hebrew ? 'rtl' : undefined} lang={o.hebrew ? 'he' : undefined}>
                  {o.label}
                </span>
                {o.detail && <span className="muted small">{o.detail}</span>}
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
  const keys = (
    <p className="jump-keys muted small" aria-hidden="true">
      {inline ? t.keysInline : t.keys}
    </p>
  )
  if (!inline)
    return (
      <>
        {field}
        {list}
        {keys}
      </>
    )
  return (
    <div className="jump-inline">
      {field}
      {listed && (
        <div className="jump-pop">
          {list}
          {keys}
        </div>
      )}
    </div>
  )
}
