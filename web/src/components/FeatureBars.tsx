import type { StyloFeature } from '../api/types'
import { useT } from '../context/localeContext'

/** Over- / under-used style features as signed z bars (Style page, speaker voices). */
export function FeatureBars({ title, items }: { title: string; items: StyloFeature[] }) {
  const m = useT()
  const max = Math.max(...items.map((f) => Math.abs(f.z)), 1)
  return (
    <>
      <p className="muted small">{title}</p>
      <ul className="feature-bars">
        {items.map((f) => (
          <li key={f.feature} title={m.ov.style.feature(f.feature, (f.rate * 100).toFixed(2), f.z.toFixed(1))}>
            <span dir="rtl" lang="he" className="he">
              {f.label}
            </span>
            <span className="bar-track">
              <span className={`bar-fill ${f.z < 0 ? 'neg' : ''}`} style={{ width: `${(Math.abs(f.z) / max) * 100}%` }} />
            </span>
            <span className="bar-n">{f.z > 0 ? '+' : ''}{f.z.toFixed(1)}</span>
          </li>
        ))}
      </ul>
    </>
  )
}
