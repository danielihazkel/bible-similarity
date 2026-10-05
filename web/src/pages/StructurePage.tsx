import { Link } from 'react-router'
import { structureParams, useStructureRanking } from '../api/hooks'
import type { LeitwortNumbers, StructureRank, StructureSort, UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel, unitTypeLabel } from '../lib/format'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha']
const SORTS: { value: StructureSort; label: string }[] = [
  { value: 'semantic_chiasm', label: 'Chiasm (semantic)' },
  { value: 'lexical_chiasm', label: 'Chiasm (lexical)' },
  { value: 'semantic_inclusio', label: 'Inclusio (semantic)' },
  { value: 'lexical_inclusio', label: 'Inclusio (lexical)' },
]
const MIN_VERSES = [5, 8, 12, 20]
const COLS: { key: keyof StructureRank; label: string; sort: StructureSort }[] = [
  { key: 'semantic_chiasm_pct', label: 'Chiasm sem', sort: 'semantic_chiasm' },
  { key: 'lexical_chiasm_pct', label: 'Chiasm lex', sort: 'lexical_chiasm' },
  { key: 'semantic_inclusio_pct', label: 'Inclusio sem', sort: 'semantic_inclusio' },
  { key: 'lexical_inclusio_pct', label: 'Inclusio lex', sort: 'lexical_inclusio' },
]

/** Units ranked by inclusio / chiasm percentiles. */
export function StructurePage() {
  const [params, update] = useQueryParams()
  const rawType = params.get('type') as UnitType | null
  const unitType = rawType && TYPES.includes(rawType) ? rawType : 'chapter'
  const rawBy = params.get('by') as StructureSort | null
  const by = SORTS.some((s) => s.value === rawBy) ? rawBy! : 'semantic_chiasm'
  const minRaw = Number(params.get('min'))
  const minVerses = MIN_VERSES.includes(minRaw) ? minRaw : 8
  const page = parsePage(params.get('page'))
  const query = { unitType, by, minVerses, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useStructureRanking(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page structure-page">
      <h1>Structure</h1>
      <p className="lede">
        Units whose verses frame them (<em>inclusio</em>: the opening returns at the close) or mirror each other (<em>chiasm</em>:
        A B C … C′ B′ A′), each scored against random pairs of the same unit. Open a unit for its heatmap and Leitworte.
      </p>
      <div className="toolbar">
        <Segmented
          label="Unit type"
          value={unitType}
          onChange={(t) => set({ type: t === 'chapter' ? null : t })}
          options={TYPES.map((t) => ({ value: t, label: unitTypeLabel(t) }))}
        />
        <label className="control">
          <span>Sort by</span>
          <select value={by} onChange={(e) => set({ by: e.target.value === 'semantic_chiasm' ? null : e.target.value })}>
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>At least</span>
          <select value={minVerses} onChange={(e) => set({ min: e.target.value === '8' ? null : e.target.value })}>
            {MIN_VERSES.map((n) => (
              <option key={n} value={n}>
                {n} verses
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="muted small">
        Percentiles are per unit; with thousands of units about 5 % reach the 95th by chance. The q column corrects for
        that (Benjamini–Hochberg over all units of the type): only units with q ≤ 0.05 stand out from chance.
      </p>
      {res.data?.leitwort_numbers && <SevenNote n={res.data.leitwort_numbers} />}

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>No scored units.</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} units · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`structure-${unitType}-p${page}.csv`}
              rows={() =>
                res.data.items.map((r) => ({
                  unit: r.unit.label_en,
                  verses: r.unit.n_verses,
                  ...Object.fromEntries(COLS.map((c) => [c.label, r[c.key] as number | null])),
                }))
              }
              all={{ list: 'structure', params: structureParams(query) }}
            />
          </p>
          <div className="table-wrap">
            <table className={`rank-table ${res.isPlaceholderData ? 'stale' : ''}`}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Unit</th>
                  <th>Verses</th>
                  {COLS.map((c) => (
                    <th key={c.key} className={c.sort === by ? 'on' : undefined}>
                      {c.label}
                    </th>
                  ))}
                  <th title="Benjamini–Hochberg q of the sorted score">q</th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((r, i) => (
                  <tr key={r.unit.unit_id}>
                    <td className="muted">{res.data.offset + i + 1}</td>
                    <td>
                      <Link to={unitLink(r.unit.unit_id, '?structure=1')}>{r.unit.label_en}</Link>{' '}
                      <span className="he-label" dir="rtl" lang="he">
                        {r.unit.label_he}
                      </span>
                    </td>
                    <td>{r.unit.n_verses}</td>
                    {COLS.map((c) => {
                      const v = r[c.key] as number | null
                      return (
                        <td key={c.key} className={`num ${c.sort === by ? 'on' : ''} ${v !== null && v >= 0.95 ? 'fact-strong' : ''}`}>
                          {v === null ? '—' : `${Math.round(v * 100)}`}
                        </td>
                      )
                    })}
                    <QCell q={r[`${by}_q` as keyof StructureRank] as number | null | undefined} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}

function QCell({ q }: { q: number | null | undefined }) {
  if (q === null || q === undefined) return <td className="muted">—</td>
  return <td className={`small ${q <= 0.05 ? 'q-strong' : 'muted'}`}>{qLabel(q)}</td>
}

/** Do Leitworte occur 7 (or 10) times more often than chance? The count-matched check, with controls. */
function SevenNote({ n }: { n: LeitwortNumbers }) {
  type Stat = { multiples: number; expected: number }
  const ratio = (m: string) => {
    const s = n[m] as Stat | undefined
    return s && s.expected > 0 ? s.multiples / s.expected : undefined
  }
  const moduli = Object.keys(n).filter((k) => /^\d+$/.test(k))
  const r7 = ratio('7')
  if (r7 === undefined) return null
  const others = moduli.filter((m) => m !== '7').map(ratio).filter((r): r is number => r !== undefined)
  const below = others.filter((r) => r < r7).length
  return (
    <p className="muted small seven-note">
      Sevens: of {n.leitworte.toLocaleString()} chapter Leitworte, {(n['7'] as Stat).multiples} occur a multiple of 7
      times against {(n['7'] as Stat).expected} expected from words with similar counts ({r7.toFixed(2)}×). Other
      divisors ({moduli.filter((m) => m !== '7').join(', ')}) show{' '}
      {others.length ? `${Math.min(...others).toFixed(2)}–${Math.max(...others).toFixed(2)}×` : 'no data'}
      {below === 0 ? ', so nothing singles out 7.' : `; ${below} of them less than 7.`}
    </p>
  )
}
