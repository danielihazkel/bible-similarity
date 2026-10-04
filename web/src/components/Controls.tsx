import type { Exclude, Mode, UnitType } from '../api/types'
import { useTextMode } from '../context/textModeContext'
import { MODE_HINTS, MODE_LABELS } from '../lib/format'
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

export function ModeToggle({ value, onChange }: { value: Mode; onChange: (m: Mode) => void }) {
  return (
    <Segmented
      label="Similarity mode"
      value={value}
      onChange={onChange}
      options={MODES.map((m) => ({ value: m, label: MODE_LABELS[m], title: MODE_HINTS[m] }))}
    />
  )
}

export function KSelect({ value, onChange }: { value: number; onChange: (k: number) => void }) {
  return (
    <label className="control">
      <span>Top</span>
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {K_OPTIONS.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>
    </label>
  )
}

const EXCLUDE_LABELS: Record<Exclude, string> = {
  neighbors: 'Hide neighbours ±2',
  chapter: 'Hide same chapter',
  book: 'Hide same book',
  known: 'Hide Sefaria-linked',
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
          {EXCLUDE_LABELS[e]}
        </label>
      ))}
    </div>
  )
}

export function TextModeToggle() {
  const { mode, setMode } = useTextMode()
  return <Segmented label="Text display" className="he-seg" value={mode} onChange={setMode} options={TEXT_MODES} />
}
