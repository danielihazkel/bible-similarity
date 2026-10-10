import { useBooks, useWordplay, wordplayParams } from '../api/hooks'
import type { WordplayPair } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { UnitFilter } from '../components/UnitFilter'
import { WordplayCard } from '../components/WordplayCard'
import { useLocale } from '../context/localeContext'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { AlliterationView, RhymeView } from './SoundViews'
import { Segmented } from '../components/Controls'

const PAGE_SIZE = 50
const KINDS: WordplayPair['kind'][] = ['substitution', 'metathesis', 'extension']

type View = 'pairs' | 'alliteration' | 'rhyme'

/** Sound patterns: sound-alike word pairs, alliteration, rhyme. */
export function WordplayPage() {
  const { m, locale } = useLocale()
  const t = m.pat.wordplay
  const [params, update] = useQueryParams()
  const raw = params.get('view')
  const view: View = raw === 'alliteration' || raw === 'rhyme' ? raw : 'pairs'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  return (
    <div className="page wordplay-page">
      <h1>{t.title}</h1>
      <div className="toolbar">
        <Segmented
          label={t.pattern}
          value={view}
          onChange={(v) => update({ view: v === 'pairs' ? null : v, page: null, kind: null, unit: null })}
          options={[
            { value: 'pairs', label: t.pairsView },
            { value: 'alliteration', label: t.alliteration },
            { value: 'rhyme', label: t.rhyme },
          ]}
        />
        {view !== 'pairs' && (
          <label className="control">
            <span>{m.search.book}</span>
            <select value={book ?? ''} onChange={(e) => update({ book: e.target.value || null, page: null })}>
              <option value="">{m.search.allBooks}</option>
              {books.data?.map((b) => (
                <option key={b.book_id} value={b.book_id}>
                  {bookOption(b, locale)}
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
  const { m, locale } = useLocale()
  const t = m.pat.wordplay
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const rawKind = params.get('kind')
  const kind = KINDS.find((k) => k === rawKind)
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { book, kind, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useWordplay(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="lede">{t.lede}</p>
      {res.data && res.data.expected_by_chance !== null && !book && !kind && !unit && (
        <p className="muted small">
          {t.chance(
            res.data.total,
            Math.round(res.data.expected_by_chance),
            Math.max(0, Math.round(res.data.total - res.data.expected_by_chance)),
          )}
        </p>
      )}
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.pat.kind}</span>
          <select value={kind ?? ''} onChange={(e) => set({ kind: e.target.value || null })}>
            <option value="">{m.pat.any}</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t.kinds[k]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <PagedList
        res={res}
        empty={t.empty}
        summary={(data) => (
          <>
            {m.pat.pairs(data.total)} · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
            all={{ list: 'wordplay', params: wordplayParams(query) }}
            filename={`wordplay-p${page}.csv`}
            rows={() =>
            data.items.map((p) => ({
            verse: p.a_label,
            word_a: p.a_form,
            word_b: p.b_form,
            kind: p.kind,
            words_apart: p.gap,
            score: p.score,
            }))
            }
            />
          </>
        )}
      >
        {(data, stale) => (
          <ol className={`disc-list ${stale}`}>
            {data.items.map((p) => (
              <WordplayCard key={`${p.a_vid}:${p.a_display}|${p.b_vid}:${p.b_display}`} p={p} />
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}
