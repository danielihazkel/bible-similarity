import { Link } from 'react-router'
import { structureParams, useStructureRanking } from '../api/hooks'
import type { LeitwortNumbers, StructureRank, StructureSort, UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { SmallScaleView } from './SmallScaleView'

const PAGE_SIZE = 50
const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha']
const SORTS: StructureSort[] = ['semantic_chiasm', 'lexical_chiasm', 'semantic_inclusio', 'lexical_inclusio']
const MIN_VERSES = [5, 8, 12, 20]
// `csv`: the export's column name (English in every interface language); display labels are in the catalog
const COLS = [
  { key: 'semantic_chiasm_pct', csv: 'Chiasm sem', sort: 'semantic_chiasm' },
  { key: 'lexical_chiasm_pct', csv: 'Chiasm lex', sort: 'lexical_chiasm' },
  { key: 'semantic_inclusio_pct', csv: 'Inclusio sem', sort: 'semantic_inclusio' },
  { key: 'lexical_inclusio_pct', csv: 'Inclusio lex', sort: 'lexical_inclusio' },
] as const satisfies readonly { key: keyof StructureRank; csv: string; sort: StructureSort }[]

/** Inner structure: whole passages ranked by inclusio / chiasm, or chiasm at the small scale. */
export function StructurePage() {
  const { m } = useLocale()
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'small' ? 'small' : 'units'
  return (
    <div className="page structure-page">
      <h1>{m.pat.structure.title}</h1>
      <Segmented
        label={m.pat.view}
        value={view}
        options={[
          { value: 'units', label: m.mir.views.units },
          { value: 'small', label: m.mir.views.small },
        ]}
        onChange={(v) => update({ view: v === 'small' ? 'small' : null, page: null }, false)}
      />
      {view === 'small' ? <SmallScaleView /> : <UnitRanking />}
    </div>
  )
}

/** Units ranked by inclusio / chiasm percentiles. */
function UnitRanking() {
  const { m, locale } = useLocale()
  const t = m.pat.structure
  const [params, update] = useQueryParams()
  const rawType = params.get('type') as UnitType | null
  const unitType = rawType && TYPES.includes(rawType) ? rawType : 'chapter'
  const rawBy = params.get('by') as StructureSort | null
  const by = rawBy && SORTS.includes(rawBy) ? rawBy : 'semantic_chiasm'
  const minRaw = Number(params.get('min'))
  const minVerses = MIN_VERSES.includes(minRaw) ? minRaw : 8
  const page = parsePage(params.get('page'))
  const query = { unitType, by, minVerses, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useStructureRanking(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="lede">
        {t.lede[0]}
        <em>{t.lede[1]}</em>
        {t.lede[2]}
        <em>{t.lede[3]}</em>
        {t.lede[4]}
      </p>
      <div className="toolbar">
        <Segmented
          label={m.units.unitType}
          value={unitType}
          onChange={(v) => set({ type: v === 'chapter' ? null : v })}
          options={TYPES.map((v) => ({ value: v, label: m.units.type(v) }))}
        />
        <label className="control">
          <span>{t.sortBy}</span>
          <select value={by} onChange={(e) => set({ by: e.target.value === 'semantic_chiasm' ? null : e.target.value })}>
            {SORTS.map((s) => (
              <option key={s} value={s}>
                {t.sorts[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.atLeast}</span>
          <select value={minVerses} onChange={(e) => set({ min: e.target.value === '8' ? null : e.target.value })}>
            {MIN_VERSES.map((n) => (
              <option key={n} value={n}>
                {t.minVerses(n)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="muted small">{t.note}</p>
      {res.data?.leitwort_numbers && <SevenNote n={res.data.leitwort_numbers} />}

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{t.empty}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.pat.units(res.data.total)} · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
              filename={`structure-${unitType}-p${page}.csv`}
              rows={() =>
                res.data.items.map((r) => ({
                  unit: r.unit.label_en,
                  verses: r.unit.n_verses,
                  ...Object.fromEntries(COLS.map((c) => [c.csv, r[c.key] as number | null])),
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
                  <th>{t.unit}</th>
                  <th className="num">{t.verses}</th>
                  {COLS.map((c) => (
                    <th key={c.key} className={c.sort === by ? 'num on' : 'num'}>
                      {t.cols[c.key]}
                    </th>
                  ))}
                  <th title={t.qTitle}>q</th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((r, i) => (
                  <tr key={r.unit.unit_id}>
                    <td className="muted">{res.data.offset + i + 1}</td>
                    <td>
                      <Link to={unitLink(r.unit.unit_id, '?structure=1')}>{unitLabel(r.unit, locale)}</Link>
                      {locale === 'en' && (
                        <>
                          {' '}
                          <span className="he-label" dir="rtl" lang="he">
                            {r.unit.label_he}
                          </span>
                        </>
                      )}
                    </td>
                    <td className="num">{r.unit.n_verses}</td>
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
    </>
  )
}

function QCell({ q }: { q: number | null | undefined }) {
  const m = useT()
  if (q === null || q === undefined) return <td className="muted">—</td>
  return <td className={`small ${q <= 0.05 ? 'q-strong' : 'muted'}`}>{m.q(q)}</td>
}

/** Do Leitworte occur 7 (or 10) times more often than chance? The count-matched check, with controls. */
function SevenNote({ n }: { n: LeitwortNumbers }) {
  const m = useT()
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
      {m.pat.structure.sevens(
        n.leitworte,
        (n['7'] as Stat).multiples,
        (n['7'] as Stat).expected,
        r7.toFixed(2),
        moduli.filter((d) => d !== '7').join(', '),
        others.length ? `${Math.min(...others).toFixed(2)}–${Math.max(...others).toFixed(2)}×` : null,
        below,
      )}
    </p>
  )
}
