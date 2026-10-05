import type { Exclude, Mode, UnitType } from '../api/types'
import { useLocale, useT } from '../context/localeContext'
import { useTextMode } from '../context/textModeContext'
import { LOCALES } from '../i18n'
import { TEXT_MODES } from '../lib/hebrew'
import { allowedExcludes, K_OPTIONS, MODES } from '../lib/urlState'

interface SegmentedProps<T extends string | number> {
  label: string
  value: T
  options: { value: T; label: string; title?: string }[]
  onChange: (v: T) => void
  className?: string
}

export function Segmented<T extends string | number>({ label, value, options, onChange, className }: SegmentedProps<T>) {
  return (
    <div className={`segmented ${className ?? ''}`} role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
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

/** English / Hebrew interface (the scripture is Hebrew either way). */
export function LocaleToggle() {
  const m = useT()
  const { locale, setLocale } = useLocale()
  return <Segmented label={m.site.language} className="lang-seg" value={locale} onChange={setLocale} options={LOCALES} />
}
