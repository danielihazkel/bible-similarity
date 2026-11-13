import { type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import type { Exclude, Mode, UnitType } from '../api/types'
import { useLocale, useT } from '../context/localeContext'
import { useTextMode } from '../context/textModeContext'
import { useTheme } from '../context/themeContext'
import { LOCALES } from '../i18n'
import { TEXT_MODES } from '../lib/hebrew'
import { bookOption } from '../lib/names'
import { THEMES } from '../lib/theme'
import { allowedExcludes, K_OPTIONS, MODES } from '../lib/urlState'
import '../styles/components/Controls.css'

interface SegmentedProps<T extends string | number> {
  label: string
  value: T
  options: { value: T; label: string; title?: string }[]
  onChange: (v: T) => void
  className?: string
}

/** One choice of a few, as a radio group: Tab reaches the chosen option, the arrow keys (and Home /
 * End) move to another and choose it. */
export function Segmented<T extends string | number>({ label, value, options, onChange, className }: SegmentedProps<T>) {
  // the group's one tab stop: the chosen option, or the first when the value is none of them
  const stop = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  )
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const radios = [...e.currentTarget.querySelectorAll<HTMLButtonElement>('button[role="radio"]')]
    const at = radios.indexOf(e.target as HTMLButtonElement)
    if (at < 0 || e.altKey || e.ctrlKey || e.metaKey) return
    // Left and Right follow the reading direction of the group (the Hebrew text toggle is right to left)
    const forward = getComputedStyle(e.currentTarget).direction === 'rtl' ? 'ArrowLeft' : 'ArrowRight'
    const back = forward === 'ArrowLeft' ? 'ArrowRight' : 'ArrowLeft'
    const n = radios.length
    const next =
      e.key === forward || e.key === 'ArrowDown'
        ? (at + 1) % n
        : e.key === back || e.key === 'ArrowUp'
          ? (at + n - 1) % n
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? n - 1
              : -1
    if (next < 0) return
    e.preventDefault()
    radios[next].focus()
    if (next !== at) onChange(options[next].value)
  }
  return (
    <div className={`segmented ${className ?? ''}`} role="radiogroup" aria-label={label} onKeyDown={onKeyDown}>
      {options.map((o, i) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          tabIndex={i === stop ? 0 : -1}
          className={o.value === value ? 'on' : undefined}
          title={o.title}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** The most options, and the most letters of their labels together, that are still a row of
 * buttons: past either, a choice is a dropdown (DESIGN.md §11). */
const CHOICE_MAX_OPTIONS = 5
const CHOICE_MAX_LETTERS = 48

/** One choice of a toolbar, drawn by the toolbar's one rule: up to five short options are a row of
 * buttons (a `Segmented`, its name shown before it), more or longer ones a dropdown. A page says
 * what the choice is; how it is drawn follows from its options. */
export function Choice<T extends string>({ label, value, options, onChange }: SegmentedProps<T>) {
  const letters = options.reduce((n, o) => n + o.label.length, 0)
  if (options.length <= CHOICE_MAX_OPTIONS && letters <= CHOICE_MAX_LETTERS) {
    return (
      <span className="control choice">
        <span aria-hidden="true">{label}</span>
        <Segmented label={label} value={value} options={options} onChange={onChange} />
      </span>
    )
  }
  return (
    <label className="control choice">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value as T)}>
        {options.map((o) => (
          <option key={o.value} value={o.value} title={o.title}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export function ModeToggle({ value, onChange, modes = MODES }: { value: Mode; onChange: (m: Mode) => void; modes?: Mode[] }) {
  const m = useT()
  return (
    <Segmented
      label={m.modes.label}
      value={value}
      onChange={onChange}
      options={modes.map((v) => ({ value: v, label: m.modes.names[v], title: m.modes.hints[v] }))}
    />
  )
}

export function KSelect({
  value,
  onChange,
  options = K_OPTIONS,
}: {
  value: number
  onChange: (k: number) => void
  options?: readonly number[]
}) {
  const m = useT()
  return (
    <label className="control">
      <span>{m.modes.top}</span>
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {options.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>
    </label>
  )
}

/** A list's book filter: "all books" (null) or one of `books` (every book, or those with data). */
export function BookSelect({
  label,
  all,
  books,
  value,
  onChange,
}: {
  label: string
  all: string
  books: readonly { book_id: number; name: string; he_name: string }[] | undefined
  value: number | string | undefined
  onChange: (book: string | null) => void
}) {
  const { locale } = useLocale()
  return (
    <label className="control">
      <span>{label}</span>
      <select value={value ?? ''} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">{all}</option>
        {books?.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {bookOption(b, locale)}
          </option>
        ))}
      </select>
    </label>
  )
}

export function ExcludeFilters({
  type,
  value,
  onChange,
}: {
  type: UnitType
  value: Exclude[]
  onChange: (v: Exclude[]) => void
}) {
  const m = useT()
  const allowed = allowedExcludes(type)
  return (
    <div className="filters">
      {allowed.map((e) => (
        <label key={e} className="check">
          <input
            type="checkbox"
            checked={value.includes(e)}
            onChange={(ev) => onChange(ev.target.checked ? [...value, e] : value.filter((x) => x !== e))}
          />
          {m.modes.exclude[e]}
        </label>
      ))}
    </div>
  )
}

/** A list's significance filter, the same on every page that has one (DESIGN.md §11): q ≤ 0.05,
 * a list's second step where it has one, and all. `strict` renames the first option where the
 * list's cut is not a q (the strongest of each group of refrains). */
export function SignificanceFilter({
  value,
  second,
  onChange,
  strict,
  strictTitle,
}: {
  value: string
  second?: string
  onChange: (v: string) => void
  strict?: string
  strictTitle?: string
}) {
  const m = useT()
  return (
    <Segmented
      className="significance"
      label={m.filter.significance}
      value={value}
      onChange={onChange}
      options={[
        { value: '0.05', label: strict ?? m.filter.q('0.05'), title: strictTitle ?? m.filter.qTitle },
        ...(second ? [{ value: second, label: m.filter.q(second), title: m.filter.qLooseTitle }] : []),
        { value: 'all', label: m.filter.all, title: m.filter.allTitle },
      ]}
    />
  )
}

/** "Only the known cases" (the ones named in advance, the ones the scholarship lists): one
 * checkbox, the same on every page that has it. */
export function KnownOnly({ checked, onChange, label, title }: { checked: boolean; onChange: (on: boolean) => void; label: string; title?: string }) {
  return (
    <label className="check known-only" title={title}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  )
}

/** The same filters behind one button of a toolbar ("Hide", with the number switched on): the
 * panel opens on a click and closes on Escape (the focus back on the button) or a click outside. */
export function ExcludeMenu({ type, value, onChange }: { type: UnitType; value: Exclude[]; onChange: (v: Exclude[]) => void }) {
  const m = useT()
  const id = useId()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        button.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])
  const on = value.filter((e) => allowedExcludes(type).includes(e)).length
  return (
    <div className={`filter-menu ${open ? 'open' : ''}`} ref={ref}>
      <button type="button" ref={button} className="filter-menu-button" title={m.modes.hideTitle} aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => setOpen((o) => !o)}>
        {m.modes.hide}
        {on > 0 && <span className="filter-menu-count">{on}</span>} <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div id={id} className="filter-menu-panel" role="group" aria-label={m.modes.hide}>
          <ExcludeFilters type={type} value={value} onChange={onChange} />
        </div>
      )}
    </div>
  )
}

export function TextModeToggle() {
  const m = useT()
  const { mode, setMode } = useTextMode()
  return (
    <Segmented
      label={m.site.textDisplay}
      className="he-seg"
      value={mode}
      onChange={setMode}
      options={TEXT_MODES.map((t) => ({ ...t, title: m.modes.textModes[t.value] }))}
    />
  )
}

/** The colour theme: the system's (auto), light or dark. */
export function ThemeToggle() {
  const m = useT()
  const { theme, setTheme } = useTheme()
  return (
    <Segmented
      label={m.site.theme}
      value={theme}
      onChange={setTheme}
      options={THEMES.map((t) => ({ value: t, label: m.site.themes[t], title: t === 'auto' ? m.site.themeAuto : undefined }))}
    />
  )
}

/** English / Hebrew interface (the scripture is Hebrew either way). */
export function LocaleToggle() {
  const m = useT()
  const { locale, setLocale } = useLocale()
  return <Segmented label={m.site.language} className="lang-seg" value={locale} onChange={setLocale} options={LOCALES} />
}
