import { pairKey, useLabels, useSetLabel } from '../api/hooks'
import type { LabelValue } from '../api/types'
import { useT } from '../context/localeContext'

const VALUES: LabelValue[] = ['real', 'not', 'unsure']

/**
 * Real / not / unsure for a proposed pair (DESIGN.md §16.25). Clicking the current label clears it.
 * `mode` / `score` record which list proposed the pair. Hidden while labels load or when the
 * server keeps them read-only and the pair has none.
 */
export function LabelButtons({ a, b, mode, score }: { a: string; b: string; mode?: string; score?: number }) {
  const t = useT().lab
  const labels = useLabels()
  const set = useSetLabel()
  if (!labels.data) return null
  const current = labels.data.items.find((l) => pairKey(l.a.unit_id, l.b.unit_id) === pairKey(a, b))
  // the value just sent shows at once, before the list is refetched
  const pending = set.isPending && set.variables && pairKey(set.variables.a_id, set.variables.b_id) === pairKey(a, b)
  const value = pending ? set.variables.label : (current?.label ?? null)
  if (!labels.data.writable) {
    return value ? <span className={`label-tag ${value}`}>{t.values[value]}</span> : null
  }
  return (
    <span className="label-buttons" role="group" aria-label={t.group}>
      {VALUES.map((v) => (
        <button
          key={v}
          type="button"
          className={`label-${v} ${value === v ? 'on' : ''}`}
          aria-pressed={value === v}
          title={t.titles[v]}
          onClick={() =>
            set.mutate(
              value === v
                ? { a_id: a, b_id: b, label: null }
                : { a_id: a, b_id: b, label: v, note: current?.note ?? '', mode, score },
            )
          }
        >
          {t.values[v]}
        </button>
      ))}
      {set.error && (
        <span role="alert" className="error small">
          {t.saveFailed(set.error.message)}
        </span>
      )}
    </span>
  )
}
