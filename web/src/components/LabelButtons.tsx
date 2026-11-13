import { useQueryClient } from '@tanstack/react-query'
import { changeLabel, pairKey, useLabels, useSetLabel } from '../api/hooks'
import type { LabelValue } from '../api/types'
import { useT } from '../context/localeContext'
import { showToast } from '../lib/toast'
import '../i18n/pages/labels'
import '../styles/components/LabelButtons.css'

const VALUES: LabelValue[] = ['real', 'not', 'unsure']

/**
 * Real / not / unsure for a proposed pair (DESIGN.md §16.25). Clicking the current label clears it,
 * and the toaster offers to put it back, with its note (M177); a failure is said there too.
 * `mode` / `score` record which list proposed the pair. Hidden while labels load or when the
 * server keeps them read-only and the pair has none.
 */
export function LabelButtons({ a, b, mode, score }: { a: string; b: string; mode?: string; score?: number }) {
  const m = useT()
  const t = m.lab
  const labels = useLabels()
  const set = useSetLabel()
  const client = useQueryClient()
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
          onClick={() => {
            if (value !== v) return set.mutate({ a_id: a, b_id: b, label: v, note: current?.note ?? '', mode, score })
            // cleared: what it was can be put back for a few seconds, the row gone or not
            const was = current
            void set
              .mutateAsync({ a_id: a, b_id: b, label: null })
              .then(() =>
                showToast(t.removed, {
                  key: `label:${pairKey(a, b)}`,
                  action: was && {
                    label: m.toast.undo,
                    run: () => void changeLabel(client, { a_id: a, b_id: b, label: was.label, note: was.note, mode: was.mode ?? undefined, score: was.score ?? undefined }),
                  },
                }),
              )
              .catch(() => {}) // said by the toaster
          }}
        >
          {t.values[v]}
        </button>
      ))}
    </span>
  )
}
