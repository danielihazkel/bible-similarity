import { useEval } from '../api/hooks'
import type { MetricSet } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { unitTypeLabel } from '../lib/format'

const METRICS = [
  { key: 'ndcg@10', label: 'nDCG@10' },
  { key: 'mrr@10', label: 'MRR@10' },
  { key: 'recall@1', label: 'R@1' },
  { key: 'recall@5', label: 'R@5' },
  { key: 'recall@10', label: 'R@10' },
  { key: 'recall@50', label: 'R@50' },
]
const SPLIT_LABELS: Record<string, string> = {
  dev: 'Development books (used to choose models and weights)',
  test: 'Test books (evaluated once, after every choice was made)',
}

const fmt = (v: number | undefined) => (v === undefined ? '–' : v.toFixed(3))

/** How well each system recovers known cross-references (Sefaria links; OpenBible as a check). */
export function EvalPage() {
  const res = useEval()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { splits, openbible, final } = res.data
  const splitNames = ['dev', 'test'].filter((s) => s in splits).concat(Object.keys(splits).filter((s) => s !== 'dev' && s !== 'test'))

  return (
    <div className="page eval-page">
      <h1>Evaluation</h1>
      <p className="lede">
        How often each system ranks a known cross-reference near the top. The gold pairs are Sefaria's links between
        verses or passages of the Tanakh, split by book so that no tested book was seen in training. Known links are a
        biased sample (famous parallels are over-represented), so low scores also mean many hits are simply unlinked.
        Rows marked <span className="eval-final">served</span> are the systems this viewer shows.
      </p>
      {splitNames.length === 0 && <p className="status">No evaluation has been run yet (`bsim eval`).</p>}
      {splitNames.map((name) => {
        const split = splits[name]
        return (
          <section key={name} aria-label={`${name} split`}>
            <h2>{SPLIT_LABELS[name] ?? name}</h2>
            {split.evaluated_at && <p className="muted small">Evaluated {split.evaluated_at.slice(0, 10)}</p>}
            {Object.entries(split.results).map(([unitType, systems]) => (
              <MetricTable
                key={unitType}
                caption={`${unitTypeLabel(unitType)}s${
                  split.gold?.[unitType] ? ` · ${split.gold[unitType].queries} queries, ${split.gold[unitType].pairs} gold pairs` : ''
                }`}
                rows={Object.entries(systems).map(([system, m]) => ({
                  label: system,
                  served: Object.entries(final[unitType] ?? {})
                    .filter(([, s]) => s === system)
                    .map(([mode]) => mode),
                  metrics: m,
                }))}
              />
            ))}
          </section>
        )
      })}
      {openbible && (
        <section aria-label="OpenBible">
          <h2>A second opinion: OpenBible cross-references ({openbible.split ?? 'dev'} books)</h2>
          <p className="muted small">
            Crowd-voted cross-references (at least 5 votes), compared with the Sefaria gold on the same queries.
            {openbible.gold?.openbible_also_in_sefaria !== undefined &&
              ` Only ${(openbible.gold.openbible_also_in_sefaria * 100).toFixed(1)}% of OpenBible pairs are also Sefaria links.`}
          </p>
          {(['openbible', 'sefaria'] as const).map((gold) => (
            <MetricTable
              key={gold}
              caption={gold === 'openbible' ? 'Against OpenBible' : 'Against Sefaria (same books)'}
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
  const sorted = [...rows].sort((a, b) => (b.metrics['ndcg@10'] ?? 0) - (a.metrics['ndcg@10'] ?? 0))
  const best = Math.max(...rows.map((r) => r.metrics['ndcg@10'] ?? 0))
  return (
    // focusable so keyboard users can scroll a wide table on a narrow screen
    <div className="table-wrap" tabIndex={0} role="region" aria-label={caption}>
      <table className="rank-table eval-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">System</th>
            {METRICS.map((m) => (
              <th key={m.key} scope="col" className="num">
                {m.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.label} className={r.served.length ? 'served' : undefined}>
              <th scope="row">
                <code>{r.label}</code>
                {r.served.length > 0 && <span className="eval-final">served: {r.served.join(', ')}</span>}
              </th>
              {METRICS.map((m) => (
                <td key={m.key} className={`num${m.key === 'ndcg@10' && r.metrics[m.key] === best ? ' on' : ''}`}>
                  {fmt(r.metrics[m.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
