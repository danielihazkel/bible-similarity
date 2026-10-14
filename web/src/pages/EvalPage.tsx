import { Fragment } from 'react'
import { useEval } from '../api/hooks'
import type { EncoderEval, EtcbcEval, Gain, MetricSet, SupervisionEval, UnitListEval } from '../api/types'
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
  const { splits, openbible, etcbc, supervision, encoders, units, final } = res.data
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
      {etcbc && <EtcbcSection etcbc={etcbc} />}
      {supervision && <SupervisionSection sup={supervision} />}
      {encoders && <EncodersSection enc={encoders} />}
      {units && <UnitListsSection ux={units} />}
    </div>
  )
}

const p100 = (x: number | null | undefined) => (x == null ? '–' : (x * 100).toFixed(1))

function EtcbcSection({ etcbc }: { etcbc: EtcbcEval }) {
  const m = useT()
  const t = m.ov.eval
  const c = etcbc.coverage
  const bands = Object.entries(etcbc.bands ?? {})
    .map(([b, v]) => `${b} % ${v['recall@10'] == null ? '–' : v['recall@10'].toFixed(2)} (${v.pairs})`)
    .join(', ')
  return (
    <section aria-label="ETCBC">
      <h2>{t.etcbc(etcbc.split ?? 'dev')}</h2>
      <p className="muted small">
        {etcbc.stats && t.etcbcLede(etcbc.stats.parallels, etcbc.stats.formula_pairs, etcbc.max_partners ?? 5)}
        {etcbc.gold && t.etcbcShare(p100(etcbc.gold.etcbc_also_in_sefaria), p100(etcbc.gold.etcbc_also_in_openbible))}
      </p>
      {(['etcbc', 'sefaria'] as const).map((gold) => (
        <MetricTable
          key={gold}
          caption={gold === 'etcbc' ? t.againstEtcbc : t.againstSefaria}
          rows={Object.entries(etcbc.results).map(([mode, r]) => ({
            label: `${mode} (${r.system})`,
            served: [],
            metrics: r[gold],
          }))}
        />
      ))}
      {bands && <p className="small">{t.etcbcBands(bands)}</p>}
      {c && (
        <p className="small">
          {t.etcbcCoverage(p100(c.in_fused_top10), p100(c.in_phrase), p100(c.in_sequence), p100(c.sequence_pairs_in_etcbc), c.sequence_pairs ?? 0)}
        </p>
      )}
    </section>
  )
}

const gain = (g: Gain) => {
  const f = (x: number) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(3)}`
  return `${f(g.mean)} [${f(g.lo)}, ${f(g.hi)}]`
}

/** The encoder retrained with more supervision (§16.41): each variant's gain over the model in use. */
function SupervisionSection({ sup }: { sup: SupervisionEval }) {
  const m = useT()
  const t = m.ov.eval
  const golds = Object.keys(sup.queries)
  const variants = Object.entries(sup.results)
  return (
    <section aria-label={t.supLabel}>
      <h2>{t.sup(sup.split ?? 'dev')}</h2>
      <p className="muted small">
        {t.supLede(sup.metric, sup.noise ?? '–')}
        {sup.chosen ? t.supChosen(sup.chosen) : t.supNone}
      </p>
      {(['fused', 'semantic'] as const).map((list) => (
        <div key={list} className="table-wrap" tabIndex={0} role="region" aria-label={t.supList[list]}>
          <table className="rank-table eval-table">
            <caption>{t.supCaption(t.supList[list], sup.baseline, golds.map((g) => `${t.gold[g] ?? g} ${(sup.baseline_scores[list]?.[g] ?? 0).toFixed(3)}`).join(', '))}</caption>
            <thead>
              <tr>
                <th scope="col">{t.supVariant}</th>
                <th scope="col">{t.supRows}</th>
                {golds.map((g) => (
                  <th key={g} scope="col" className="num">
                    {t.gold[g] ?? g}
                  </th>
                ))}
                {list === 'fused' && <th scope="col">{t.supAdopt}</th>}
              </tr>
            </thead>
            <tbody>
              {variants.map(([name, r]) => (
                <tr key={name} className={r.adopt ? 'served' : undefined}>
                  <th scope="row">
                    <code>{name}</code>
                  </th>
                  <td className="small">
                    {Object.entries(r.rows_by_source)
                      .map(([s, n]) => t.supSource(s, n))
                      .join(' · ')}
                  </td>
                  {golds.map((g) => {
                    const x = r.gains[g]?.[list]
                    return (
                      <td key={g} className={`num${x && x.lo > 0 ? ' on' : ''}`} title={x ? t.supCounts(x.better, x.worse, x.queries) : undefined}>
                        {x ? gain(x) : '–'}
                      </td>
                    )
                  })}
                  {list === 'fused' && <td>{r.adopt ? t.supYes : t.supNo}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  )
}

/** Newer encoders against the model in use (§16.48): each candidate's gain, the rule's verdict. */
function EncodersSection({ enc }: { enc: EncoderEval }) {
  const t = useT().ov.eval
  const golds = Object.keys(enc.queries)
  const candidates = Object.entries(enc.results)
  const zero = candidates.filter(([, r]) => r.kind === 'zero_shot' && r.vs_reference)
  const cell = (x: Gain | undefined) => (
    <td className={`num${x && x.lo > 0 ? ' on' : ''}`} title={x ? t.supCounts(x.better, x.worse, x.queries) : undefined}>
      {x ? gain(x) : '–'}
    </td>
  )
  const scores = (s: Record<string, number> | undefined) => golds.map((g) => `${t.gold[g] ?? g} ${(s?.[g] ?? 0).toFixed(3)}`).join(', ')
  const head = (adopt: boolean) => (
    <thead>
      <tr>
        <th scope="col">{t.encCandidate}</th>
        <th scope="col">{t.encModel}</th>
        {golds.map((g) => (
          <th key={g} scope="col" className="num">
            {t.gold[g] ?? g}
          </th>
        ))}
        {adopt && <th scope="col">{t.supAdopt}</th>}
      </tr>
    </thead>
  )
  return (
    <section aria-label={t.encLabel}>
      <h2>{t.enc(enc.split ?? 'dev')}</h2>
      <p className="muted small">
        {t.encLede(enc.metric, `${enc.noise_bar.toFixed(4)}`)}
        {enc.chosen ? t.encChosen(enc.chosen) : t.encNone}
      </p>
      {(['fused', 'semantic'] as const).map((list) => (
        <div key={list} className="table-wrap" tabIndex={0} role="region" aria-label={t.encList[list]}>
          <table className="rank-table eval-table">
            <caption>{t.supCaption(t.encList[list], enc.baseline, scores(enc.baseline_scores[list]))}</caption>
            {head(list === 'fused')}
            <tbody>
              {candidates.map(([name, r]) => (
                <tr key={name} className={r.adopt ? 'served' : undefined}>
                  <th scope="row">
                    <code>{name}</code>
                  </th>
                  <td className="small">
                    <span dir="ltr">{r.model}</span> · {t.encKind[r.kind] ?? r.kind}
                  </td>
                  {golds.map((g) => (
                    <Fragment key={g}>{cell(r.gains[g]?.[list])}</Fragment>
                  ))}
                  {list === 'fused' && <td>{r.adopt ? t.supYes : t.supNo}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {zero.length > 0 && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.encZeroLabel}>
          <table className="rank-table eval-table">
            <caption>{t.encZero(enc.reference, scores(enc.reference_scores.semantic))}</caption>
            {head(false)}
            <tbody>
              {zero.map(([name, r]) => (
                <tr key={name}>
                  <th scope="row">
                    <code>{name}</code>
                  </th>
                  <td className="small" dir="ltr">
                    {r.model}
                  </td>
                  {golds.map((g) => (
                    <Fragment key={g}>{cell(r.vs_reference?.[g])}</Fragment>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

/** A third fusion list for chapters and pericopes (§16.50): each family's gains, the verdict. */
function UnitListsSection({ ux }: { ux: UnitListEval }) {
  const m = useT()
  const t = m.ov.eval
  const types = Object.entries(ux.unit_types)
  const cell = (x: Gain | undefined) => (
    <td className={`num${x && x.lo > 0 ? ' on' : ''}`} title={x ? t.supCounts(x.better, x.worse, x.queries) : undefined}>
      {x ? gain(x) : '–'}
    </td>
  )
  const family = (name: string) => t.unitFamilies[name] ?? name
  return (
    <section aria-label={t.unitLabel}>
      <h2>{t.unit(ux.split ?? 'dev')}</h2>
      <p className="muted small">{t.unitLede(ux.metric)}</p>
      <ul className="muted small">
        {types.map(([type, r]) => (
          <li key={type}>{t.unitVerdict(type, r.chosen ? family(r.chosen) : null)}</li>
        ))}
      </ul>
      {types.map(([type, r]) => {
        const golds = Object.keys(r.queries)
        const scores = golds.map((g) => `${t.gold[g] ?? g} ${(r.baseline_scores[g] ?? 0).toFixed(3)}`).join(', ')
        const families = Object.entries(r.families)
        return (
          <Fragment key={type}>
            <div className="table-wrap" tabIndex={0} role="region" aria-label={t.unitCaption(type, scores)}>
              <table className="rank-table eval-table">
                <caption>{t.unitCaption(type, scores)}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.unitFamily}</th>
                    <th scope="col">{t.unitSelected}</th>
                    <th scope="col" className="num">
                      {t.unitCrossFitted}
                    </th>
                    {golds.map((g) => (
                      <th key={g} scope="col" className="num">
                        {t.gold[g] ?? g}
                      </th>
                    ))}
                    <th scope="col">{t.supAdopt}</th>
                  </tr>
                </thead>
                <tbody>
                  {families.map(([name, f]) => (
                    <tr key={name} className={f.adopt ? 'served' : undefined}>
                      <th scope="row">{family(name)}</th>
                      <td className="small">
                        <code>{f.selected}</code>
                      </td>
                      {cell(f.cross_fitted_gain)}
                      {golds.map((g) => (
                        <Fragment key={g}>{cell(f.gains[g])}</Fragment>
                      ))}
                      <td>{f.adopt ? t.supYes : t.supNo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-wrap" tabIndex={0} role="region" aria-label={t.unitAloneCaption(type)}>
              <table className="rank-table eval-table">
                <caption>{t.unitAloneCaption(type)}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.unitFamily}</th>
                    <th scope="col">{t.unitList}</th>
                    <th scope="col" className="num">
                      {t.unitUnits}
                    </th>
                    {golds.map((g) => (
                      <th key={g} scope="col" className="num">
                        {t.gold[g] ?? g}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {families.flatMap(([name, f]) =>
                    Object.entries(f.alone).map(([variant, a]) => (
                      <tr key={`${name}/${variant}`}>
                        <th scope="row">{family(name)}</th>
                        <td className="small">
                          <code>{variant}</code>
                        </td>
                        <td className="num">{m.num(a.units_with_list)}</td>
                        {golds.map((g) => (
                          <td key={g} className="num">
                            {(a.scores[g] ?? 0).toFixed(3)}
                          </td>
                        ))}
                      </tr>
                    )),
                  )}
                </tbody>
              </table>
            </div>
          </Fragment>
        )
      })}
    </section>
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
