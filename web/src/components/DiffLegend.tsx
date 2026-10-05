import { useT } from '../context/localeContext'
import { DIFF_OPS } from '../lib/diff'

/** Key to the word-level diff marks of parallel passages. */
export function DiffLegend() {
  const m = useT()
  return (
    <p className="diff-legend" aria-label={m.diff.marks}>
      {DIFF_OPS.map((op) => (
        <span key={op} title={m.diff.ops[op].hint}>
          <span className={`w w-diff-${op}`}>{m.diff.ops[op].label}</span>
        </span>
      ))}
    </p>
  )
}
