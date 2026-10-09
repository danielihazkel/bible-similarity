import { useBooks, usePhrases, phrasesParams } from '../api/hooks'
import { EmptyList, Pager } from '../components/Pager'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { PhraseCard } from '../components/PhraseCard'
import { UnitFilter } from '../components/UnitFilter'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { SpreadView } from './SpreadView'

const PAGE_SIZE = 50
const MIN_TOKENS = [3, 4, 5, 6, 8, 10]
// By default only sequences found in at most 3 verses are listed: a triple parallel such as
// Kings / Isaiah / Chronicles survives, an idiom shared by many verses does not.
const MAX_SPREAD = 3

/** Shared phrases, and rare words shared over a few verses (`?view=spread`). */
export function PhrasesPage() {
  const { m } = useLocale()
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'spread' ? 'spread' : 'phrases'
  return (
    <div className="page phrases-page">
      <h1>{m.par.phrases.title}</h1>
      <Segmented
        label={m.par.phrases.viewLabel}
        value={view}
        options={[
          { value: 'phrases', label: m.par.phrases.views.phrases },
          { value: 'spread', label: m.par.phrases.views.spread },
        ]}
        onChange={(v) => update({ view: v === 'spread' ? 'spread' : null, page: null }, false)}
      />
      {view === 'spread' ? <SpreadView /> : <PhraseList />}
    </div>
  )
}

/** The strongest shared phrases in the Tanakh (local alignment of lemma streams). */
function PhraseList() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const recurring = params.get('recurring') === '1'
  const minRaw = Number(params.get('min'))
  const minTokens = MIN_TOKENS.includes(minRaw) ? minRaw : 3
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = {
    book,
    crossBook,
    minTokens,
    // a unit's own phrases are all listed, recurring idioms included
    maxSpread: recurring || unit ? undefined : MAX_SPREAD,
    unit,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const res = usePhrases(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="lede">{m.par.phrases.lede}</p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{m.par.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.par.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.par.phrases.atLeast}</span>
          <select value={minTokens} onChange={(e) => set({ min: e.target.value === '3' ? null : e.target.value })}>
            {MIN_TOKENS.map((n) => (
              <option key={n} value={n}>
                {m.cards.lemmas(n)}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          {m.par.differentBooks}
        </label>
        <label className="check" title={m.par.phrases.recurringTitle(MAX_SPREAD)}>
          <input type="checkbox" checked={recurring} onChange={(e) => set({ recurring: e.target.checked ? '1' : null })} />
          {m.par.phrases.recurring}
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{m.par.phrases.none}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.par.pairsPage(res.data.total, page, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'phrases', params: phrasesParams(query) }}
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
    </>
  )
}
