import { useBooks, usePhrases } from '../api/hooks'
import { Pager } from '../components/Pager'
import { ExportCsv } from '../components/ExportCsv'
import { PhraseCard } from '../components/PhraseCard'
import { ErrorBox, Loading } from '../components/Status'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const MIN_TOKENS = [3, 4, 5, 6, 8, 10]
// By default only sequences found in at most 3 verses are listed: a triple parallel such as
// Kings / Isaiah / Chronicles survives, an idiom shared by many verses does not.
const MAX_SPREAD = 3

/** The strongest shared phrases in the Tanakh (local alignment of lemma streams). */
export function PhrasesPage() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const recurring = params.get('recurring') === '1'
  const minRaw = Number(params.get('min'))
  const minTokens = MIN_TOKENS.includes(minRaw) ? minRaw : 3
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = usePhrases({
    book,
    crossBook,
    minTokens,
    maxSpread: recurring ? undefined : MAX_SPREAD,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page phrases-page">
      <h1>Shared phrases</h1>
      <p className="lede">
        Verse pairs whose lemmas line up as a phrase (same words in the same order, small gaps allowed). Rare words weigh
        more and formulaic phrases barely count, so quotations, allusions and parallel accounts come first.
      </p>
      <div className="toolbar">
        <label className="control">
          <span>Book</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">All books</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {b.name} · {b.he_name}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>At least</span>
          <select value={minTokens} onChange={(e) => set({ min: e.target.value === '3' ? null : e.target.value })}>
            {MIN_TOKENS.map((n) => (
              <option key={n} value={n}>
                {n} lemmas
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          Different books only
        </label>
        <label className="check" title={`Show phrases shared by more than ${MAX_SPREAD} verses (idioms)`}>
          <input type="checkbox" checked={recurring} onChange={(e) => set({ recurring: e.target.checked ? '1' : null })} />
          Include recurring phrases
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No shared phrases match these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} pairs · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`phrases-p${page}.csv`}
              rows={() =>
                res.data.items.map((p) => ({
                  a: p.a.label_en,
                  b: p.b.label_en,
                  score: p.score,
                  lemmas: p.n_tokens,
                  spread: p.spread,
                  sefaria_link: p.link?.level ?? '',
                }))
              }
            />
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((p) => (
              <PhraseCard key={`${p.a.unit_id}|${p.b.unit_id}`} p={p} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}
