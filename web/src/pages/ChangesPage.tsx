import { Link } from 'react-router'
import { useBooks, useChanges, changesParams } from '../api/hooks'
import type { ChangeGroup, DiffOp } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { Segmented } from '../components/Controls'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { DIFF_LABELS, DIFF_OPS } from '../lib/diff'
import { sequenceLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'
import { RewritesView } from './RewritesView'

const PAGE_SIZE = 50

/** How parallel passages differ across the corpus: word changes grouped and counted. */
export function ChangesPage() {
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'rewrites' ? 'rewrites' : 'words'

  return (
    <div className="page changes-page">
      <h1>How parallels differ</h1>
      <p className="lede">
        Every verse pair of a strong parallel sequence aligned word by word, the earlier passage (in canon order) on the
        left. Counted across the corpus, the changes show habits of the later text: Chronicles writes דויד for דוד, על for
        אל, אני for אנכי, and often אלהים where Samuel–Kings has יהוה.
      </p>
      <div className="toolbar">
        <Segmented
          label="View"
          value={view}
          onChange={(v) => update({ view: v === 'words' ? null : v, page: null })}
          options={[
            { value: 'words', label: 'All changes by word' },
            { value: 'rewrites', label: 'Systematic rewrites' },
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
  const [params, update] = useQueryParams()
  const raw = params.get('op') as DiffOp | null
  const op: DiffOp = raw && DIFF_OPS.includes(raw) ? raw : 'substitution'
  const num = (k: string) => {
    const v = params.get(k)
    return v === null || v === '' ? undefined : Number(v)
  }
  const aBook = num('a')
  const bBook = num('b')
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { op, aBook, bBook, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useChanges(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const totals = res.data?.totals

  const bookSelect = (label: string, key: string, value: number | undefined) => (
    <label className="control">
      <span>{label}</span>
      <select value={value ?? ''} onChange={(e) => set({ [key]: e.target.value || null })}>
        <option value="">Any book</option>
        {books.data?.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {b.name} · {b.he_name}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <>
      <div className="toolbar">
        <Segmented
          label="Kind of change"
          value={op}
          onChange={(o) => set({ op: o === 'substitution' ? null : o })}
          options={DIFF_OPS.map((o) => ({
            value: o,
            label: totals?.[o] !== undefined ? `${DIFF_LABELS[o].label} ${totals[o]!.toLocaleString()}` : DIFF_LABELS[o].label,
            title: DIFF_LABELS[o].hint,
          }))}
        />
      </div>
      <div className="toolbar">
        {bookSelect('Earlier passage in', 'a', aBook)}
        {bookSelect('Later passage in', 'b', bBook)}
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>No changes of this kind for these books.</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} distinct changes · page {page} of {pages}
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
                  <th>Earlier</th>
                  <th aria-hidden="true" />
                  <th>Later</th>
                  <th className="num">Times</th>
                  <th className="num">Sequences</th>
                  <th>Examples</th>
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
        →
      </td>
      <td>{word(g.b_he)}</td>
      <td className="num">{g.count}</td>
      <td className="num">{g.n_sequences}</td>
      <td className="change-examples small">
        {g.examples.map((e) => (
          <Link key={`${e.a}|${e.b}`} to={sequenceLink(e.seq_id)} title="Open the parallel sequence">
            {e.a_label} → {e.b_label}
          </Link>
        ))}
      </td>
    </tr>
  )
}
