import { Link } from 'react-router'
import { useStructureRanking } from '../api/hooks'
import type { StructureRank, StructureSort, UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { unitTypeLabel } from '../lib/format'
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
  const res = useStructureRanking({ unitType, by, minVerses, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
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
        Percentiles are per unit; with thousands of units about 5 % reach the 95th by chance, so read the top of the list as
        candidates.
      </p>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No scored units.</p>
      ) : (
        <>
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
