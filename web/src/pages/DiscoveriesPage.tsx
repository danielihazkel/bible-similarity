import { Link } from 'react-router'
import { useBooks, useDiscoveries } from '../api/hooks'
import type { Discovery, Mode, UnitSummary, UnitType, Verse } from '../api/types'
import { ModeToggle, Segmented } from '../components/Controls'
import { HebrewPlain, HebrewText } from '../components/HebrewText'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { formatScore, MODE_HINTS, unitTypeLabel } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { MODES, parsePage, useQueryParams } from '../lib/urlState'

const UNIT_TYPES: UnitType[] = ['verse', 'chapter', 'pericope', 'parasha']
const PAGE_SIZE = 50
// Semantic scores are comparable across sources; BM25 is not, and fused RRF scores tie at the top.
const DEFAULT_MODE: Mode = 'semantic'

function parseType(v: string | null): UnitType {
  return UNIT_TYPES.includes(v as UnitType) ? (v as UnitType) : 'verse'
}


export function DiscoveriesPage() {
  const [params, update] = useQueryParams()
  const unitType = parseType(params.get('type'))
  const mode = MODES.includes(params.get('mode') as Mode) ? (params.get('mode') as Mode) : DEFAULT_MODE
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const disc = useDiscoveries({ unitType, mode, book, crossBook, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = disc.data ? Math.max(1, Math.ceil(disc.data.total / PAGE_SIZE)) : 1
  // Any filter change returns to the first page.
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page discoveries-page">
      <h1>Discoveries</h1>
      <p className="lede">
        The strongest pairs that Sefaria does <em>not</em> cross-reference: one unit ranks the other in its top 10,
        no Sefaria link joins them, and neighbouring verses are left out.
      </p>
      <div className="toolbar">
        <Segmented
          label="Unit type"
          value={unitType}
          onChange={(t) => set({ type: t === 'verse' ? null : t })}
          options={UNIT_TYPES.map((t) => ({ value: t, label: unitTypeLabel(t) }))}
        />
        <ModeToggle value={mode} onChange={(m) => set({ mode: m === DEFAULT_MODE ? null : m })} />
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
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          Different books only
        </label>
      </div>
      <p className="muted small">{MODE_HINTS[mode]}.</p>

      {disc.isPending ? (
        <Loading />
      ) : disc.error ? (
        <ErrorBox error={disc.error} />
      ) : disc.data.items.length === 0 ? (
        <p className="status">No unlinked pairs match these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {disc.data.total.toLocaleString()} pairs · page {page} of {pages}
          </p>
          <ol className={`disc-list ${disc.isPlaceholderData ? 'stale' : ''}`} start={disc.data.offset + 1}>
            {disc.data.items.map((d) => (
              <DiscoveryCard key={`${d.a.unit_id}|${d.b.unit_id}`} d={d} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}

function DiscoveryCard({ d }: { d: Discovery }) {
  const ranks = [
    d.rank_ab !== null && `${d.b.label_en} is #${d.rank_ab} for ${d.a.label_en}`,
    d.rank_ba !== null && `${d.a.label_en} is #${d.rank_ba} for ${d.b.label_en}`,
  ].filter(Boolean)
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="score" title={ranks.join('; ')}>
          {formatScore(d.score)}
        </span>
        {d.rank_ab !== null && d.rank_ba !== null && (
          <span className="mutual-tag" title="Each is in the other's top 10">
            mutual
          </span>
        )}
        <span className="hit-actions">
          <Link className="linkish" to={compareLink(d.a.unit_id, d.b.unit_id)} title="Side-by-side comparison">
            Compare
          </Link>
        </span>
      </div>
      <div className="disc-pair">
        <Side unit={d.a} verse={d.a_verse} preview={d.a_preview} />
        <Side unit={d.b} verse={d.b_verse} preview={d.b_preview} />
      </div>
    </li>
  )
}

function Side({ unit, verse, preview }: { unit: UnitSummary; verse: Verse | null; preview: string | null }) {
  return (
    <div className="disc-side">
      <Link className="hit-ref" to={unitLink(unit.unit_id)}>
        {unit.label_en}
        <span className="he-label" dir="rtl" lang="he">
          {unit.label_he}
        </span>
      </Link>
      {verse ? (
        <p className="hit-text">
          <HebrewText verse={verse} />
        </p>
      ) : (
        preview && (
          <p className="hit-text preview">
            <HebrewPlain text={preview} />
            {unit.n_verses > 1 && <span className="muted"> … ({unit.n_verses} verses)</span>}
          </p>
        )
      )}
    </div>
  )
}
