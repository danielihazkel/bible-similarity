import { Link } from 'react-router'
import { useBooks, useChanges, changesParams } from '../api/hooks'
import { UnitFilter } from '../components/UnitFilter'
import type { ChangeGroup, DiffOp } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { Segmented } from '../components/Controls'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { DIFF_OPS } from '../lib/diff'
import { sequenceLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { RewritesView } from './RewritesView'

const PAGE_SIZE = 50

/** How parallel passages differ across the corpus: word changes grouped and counted. */
export function ChangesPage() {
  const m = useT()
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'rewrites' ? 'rewrites' : 'words'

  return (
    <div className="page changes-page">
      <h1>{m.par.changes.title}</h1>
      <p className="lede">{m.par.changes.lede}</p>
      <div className="toolbar">
        <Segmented
          label={m.par.changes.view}
          value={view}
          onChange={(v) => update({ view: v === 'words' ? null : v, page: null, unit: null })}
          options={[
            { value: 'words', label: m.par.changes.byWord },
            { value: 'rewrites', label: m.par.changes.rewrites },
          ]}
        />
      </div>
      {view === 'rewrites' ? (
        <RewritesView />
      ) : (
        <ChangesByWord />
      )}
    </div>
  )
}

function ChangesByWord() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const raw = params.get('op') as DiffOp | null
  const op: DiffOp = raw && DIFF_OPS.includes(raw) ? raw : 'substitution'
  const num = (k: string) => {
    const v = params.get(k)
    return v === null || v === '' ? undefined : Number(v)
  }
  const aBook = num('a')
  const bBook = num('b')
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { op, aBook, bBook, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useChanges(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const totals = res.data?.totals

  const bookSelect = (label: string, key: string, value: number | undefined) => (
    <label className="control">
      <span>{label}</span>
      <select value={value ?? ''} onChange={(e) => set({ [key]: e.target.value || null })}>
        <option value="">{m.par.changes.anyBook}</option>
        {books.data?.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {bookOption(b, locale)}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented
          label={m.par.changes.kind}
          value={op}
          onChange={(o) => set({ op: o === 'substitution' ? null : o })}
          options={DIFF_OPS.map((o) => ({
            value: o,
            label: totals?.[o] !== undefined ? m.par.changes.opCount(m.diff.ops[o].label, totals[o]!) : m.diff.ops[o].label,
            title: m.diff.ops[o].hint,
          }))}
        />
      </div>
      <div className="toolbar">
        {bookSelect(m.par.changes.earlierIn, 'a', aBook)}
        {bookSelect(m.par.changes.laterIn, 'b', bBook)}
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{m.par.changes.none}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.par.changes.page(res.data.total, page, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'changes', params: changesParams(query) }}
              filename={`changes-${op}-p${page}.csv`}
              rows={() =>
                res.data.items.map((g) => ({
                  kind: op,
                  earlier: g.a_he,
                  later: g.b_he,
                  times: g.count,
                  sequences: g.n_sequences,
                  example: g.examples[0] ? `${g.examples[0].a_label} -> ${g.examples[0].b_label}` : '',
                }))
              }
            />
          </p>
          <div className="table-wrap">
            <table className={`change-table ${res.isPlaceholderData ? 'stale' : ''}`}>
              <thead>
                <tr>
                  <th>{m.par.changes.earlier}</th>
                  <th aria-hidden="true" />
                  <th>{m.par.changes.later}</th>
                  <th className="num">{m.par.changes.times}</th>
                  <th className="num">{m.par.changes.sequences}</th>
                  <th>{m.par.changes.examples}</th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((g) => (
                  <Row key={`${g.a_key}|${g.b_key}`} g={g} />
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

function Row({ g }: { g: ChangeGroup }) {
  const { m, locale } = useLocale()
  const word = (he: string | null) =>
    he === null ? (
      <span className="muted">—</span>
    ) : (
      <span className="he" dir="rtl" lang="he">
        {he}
      </span>
    )
  return (
    <tr>
      <td>{word(g.a_he)}</td>
      <td className="muted" aria-hidden="true">
        {m.par.arrow}
      </td>
      <td>{word(g.b_he)}</td>
      <td className="num">{g.count}</td>
      <td className="num">{g.n_sequences}</td>
      <td className="change-examples small">
        {g.examples.map((e) => (
          <Link key={`${e.a}|${e.b}`} to={sequenceLink(e.seq_id)} title={m.par.changes.openSequence}>
            {locale === 'he' ? e.a_label_he : e.a_label} {m.par.arrow} {locale === 'he' ? e.b_label_he : e.b_label}
          </Link>
        ))}
      </td>
    </tr>
  )
}
