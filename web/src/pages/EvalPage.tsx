import { useEval } from '../api/hooks'
import type { MetricSet } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useT } from '../context/localeContext'

const METRICS = [
  { key: 'ndcg@10', label: 'nDCG@10' },
  { key: 'mrr@10', label: 'MRR@10' },
  { key: 'recall@1', label: 'R@1' },
  { key: 'recall@5', label: 'R@5' },
  { key: 'recall@10', label: 'R@10' },
  { key: 'recall@50', label: 'R@50' },
]
const fmt = (v: number | undefined) => (v === undefined ? '–' : v.toFixed(3))

/** How well each system recovers known cross-references (Sefaria links; OpenBible as a check). */
export function EvalPage() {
  const m = useT()
  const res = useEval()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { splits, openbible, final } = res.data
  const splitNames = ['dev', 'test'].filter((s) => s in splits).concat(Object.keys(splits).filter((s) => s !== 'dev' && s !== 'test'))

  return (
    <div className="page eval-page">
      <h1>{m.ov.eval.title}</h1>
      <p className="lede">
        {m.ov.eval.lede}
        <span className="eval-final">{m.ov.eval.served}</span>
        {m.ov.eval.ledeEnd}
      </p>
      {splitNames.length === 0 && <p className="status">{m.ov.eval.none}</p>}
      {splitNames.map((name) => {
        const split = splits[name]
        return (
          <section key={name} aria-label={m.ov.eval.splitLabel(name)}>
            <h2>{m.ov.eval.splits[name] ?? name}</h2>
            {split.evaluated_at && <p className="muted small">{m.ov.eval.evaluated(split.evaluated_at.slice(0, 10))}</p>}
            {Object.entries(split.results).map(([unitType, systems]) => (
              <MetricTable
                key={unitType}
                caption={m.ov.eval.caption(unitType, split.gold?.[unitType])}
                rows={Object.entries(systems).map(([system, metrics]) => ({
                  label: system,
                  served: Object.entries(final[unitType] ?? {})
                    .filter(([, s]) => s === system)
                    .map(([mode]) => mode),
                  metrics,
                }))}
              />
            ))}
          </section>
        )
      })}
      {openbible && (
        <section aria-label="OpenBible">
          <h2>{m.ov.eval.openbible(openbible.split ?? 'dev')}</h2>
          <p className="muted small">
            {m.ov.eval.openbibleLede}
            {openbible.gold?.openbible_also_in_sefaria !== undefined &&
              m.ov.eval.openbibleShare((openbible.gold.openbible_also_in_sefaria * 100).toFixed(1))}
          </p>
          {(['openbible', 'sefaria'] as const).map((gold) => (
            <MetricTable
              key={gold}
              caption={gold === 'openbible' ? m.ov.eval.againstOpenbible : m.ov.eval.againstSefaria}
              rows={Object.entries(openbible.results).map(([mode, r]) => ({
                label: `${mode} (${r.system})`,
                served: [],
                metrics: r[gold],
              }))}
            />
          ))}
        </section>
      )}
    </div>
  )
}

interface Row {
  label: string
  served: string[]
  metrics: MetricSet
}

function MetricTable({ caption, rows }: { caption: string; rows: Row[] }) {
  const m = useT()
  const sorted = [...rows].sort((a, b) => (b.metrics['ndcg@10'] ?? 0) - (a.metrics['ndcg@10'] ?? 0))
  const best = Math.max(...rows.map((r) => r.metrics['ndcg@10'] ?? 0))
  return (
    // focusable so keyboard users can scroll a wide table on a narrow screen
    <div className="table-wrap" tabIndex={0} role="region" aria-label={caption}>
      <table className="rank-table eval-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">{m.ov.eval.system}</th>
            {METRICS.map((x) => (
              <th key={x.key} scope="col" className="num">
                {x.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.label} className={r.served.length ? 'served' : undefined}>
              <th scope="row">
                <code>{r.label}</code>
                {r.served.length > 0 && <span className="eval-final">{m.ov.eval.servedAs(r.served.join(', '))}</span>}
              </th>
              {METRICS.map((x) => (
                <td key={x.key} className={`num${x.key === 'ndcg@10' && r.metrics[x.key] === best ? ' on' : ''}`}>
                  {fmt(r.metrics[x.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
