import { useBooks, useWordplay, wordplayParams } from '../api/hooks'
import type { WordplayPair } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { WordplayCard } from '../components/WordplayCard'
import { parsePage, useQueryParams } from '../lib/urlState'
import { AlliterationView, RhymeView } from './SoundViews'
import { Segmented } from '../components/Controls'

const PAGE_SIZE = 50
const KINDS: { value: WordplayPair['kind']; label: string }[] = [
  { value: 'substitution', label: 'One letter changed' },
  { value: 'metathesis', label: 'Letters swapped' },
  { value: 'extension', label: 'One letter added' },
]

type View = 'pairs' | 'alliteration' | 'rhyme'

/** Sound patterns: sound-alike word pairs, alliteration, rhyme. */
export function WordplayPage() {
  const [params, update] = useQueryParams()
  const raw = params.get('view')
  const view: View = raw === 'alliteration' || raw === 'rhyme' ? raw : 'pairs'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  return (
    <div className="page wordplay-page">
      <h1>Wordplay</h1>
      <div className="toolbar">
        <Segmented
          label="Sound pattern"
          value={view}
          onChange={(v) => update({ view: v === 'pairs' ? null : v, page: null, kind: null, unit: null })}
          options={[
            { value: 'pairs', label: 'Sound-alike words' },
            { value: 'alliteration', label: 'Alliteration' },
            { value: 'rhyme', label: 'Rhyme' },
          ]}
        />
        {view !== 'pairs' && (
          <label className="control">
            <span>Book</span>
            <select value={book ?? ''} onChange={(e) => update({ book: e.target.value || null, page: null })}>
              <option value="">All books</option>
              {books.data?.map((b) => (
                <option key={b.book_id} value={b.book_id}>
                  {b.name} · {b.he_name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {view === 'alliteration' ? <AlliterationView book={book} /> : view === 'rhyme' ? <RhymeView book={book} /> : <PairsView />}
    </div>
  )
}

/** Sound-alike words close together (paronomasia), rarest first. */
function PairsView() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const rawKind = params.get('kind')
  const kind = KINDS.some((k) => k.value === rawKind) ? (rawKind as WordplayPair['kind']) : undefined
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { book, kind, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useWordplay(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="lede">
        Different words that sound alike, a few words apart: one consonant changed, two swapped or one added, with the same
        vowels — as in Isaiah 5:7, מִשְׁפָּט / מִשְׂפָּח and צְדָקָה / צְעָקָה. Rare words first: that is what makes the echo
        audible.
      </p>
      {res.data && res.data.expected_by_chance !== null && !book && !kind && !unit && (
        <p className="muted small">
          {res.data.total.toLocaleString()} pairs; shuffling the word order within each chapter yields about{' '}
          {Math.round(res.data.expected_by_chance).toLocaleString()}, so roughly{' '}
          {Math.max(0, Math.round(res.data.total - res.data.expected_by_chance)).toLocaleString()} are more than chance —
          read the list as candidates, not proofs.
        </p>
      )}
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
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
          <span>Kind</span>
          <select value={kind ?? ''} onChange={(e) => set({ kind: e.target.value || null })}>
            <option value="">Any</option>
            {KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>No wordplay matches these filters.</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} pairs · page {page} of {pages}
            {' · '}
            <ExportCsv
              all={{ list: 'wordplay', params: wordplayParams(query) }}
              filename={`wordplay-p${page}.csv`}
              rows={() =>
                res.data.items.map((p) => ({
                  verse: p.a_label,
                  word_a: p.a_form,
                  word_b: p.b_form,
                  kind: p.kind,
                  words_apart: p.gap,
                  score: p.score,
                }))
              }
            />
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((p) => (
              <WordplayCard key={`${p.a_vid}:${p.a_display}|${p.b_vid}:${p.b_display}`} p={p} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}
