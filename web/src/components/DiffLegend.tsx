import { DIFF_LABELS, DIFF_OPS } from '../lib/diff'

/** Key to the word-level diff marks of parallel passages. */
export function DiffLegend() {
  return (
    <p className="diff-legend" aria-label="Change marks">
      {DIFF_OPS.map((op) => (
        <span key={op} title={DIFF_LABELS[op].hint}>
          <span className={`w w-diff-${op}`}>{DIFF_LABELS[op].label}</span>
        </span>
      ))}
    </p>
  )
}
