import { Link } from 'react-router'
import { useBooks, useDiscoveries, discoveriesParams } from '../api/hooks'
import type { Discovery, Mode, UnitSummary, UnitType, Verse } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { ModeToggle, Segmented } from '../components/Controls'
import { HebrewPlain, HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale, useT } from '../context/localeContext'
import { formatScore } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { bookOption, unitLabel } from '../lib/names'
import { MODES, parsePage, useQueryParams } from '../lib/urlState'

const UNIT_TYPES: UnitType[] = ['verse', 'chapter', 'pericope', 'parasha']
const PAGE_SIZE = 50
// Semantic scores are comparable across sources; BM25 is not, and fused RRF scores tie at the top.
const DEFAULT_MODE: Mode = 'semantic'

function parseType(v: string | null): UnitType {
  return UNIT_TYPES.includes(v as UnitType) ? (v as UnitType) : 'verse'
}


export function DiscoveriesPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const unitType = parseType(params.get('type'))
  const mode = MODES.includes(params.get('mode') as Mode) ? (params.get('mode') as Mode) : DEFAULT_MODE
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { unitType, mode, book, crossBook, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const disc = useDiscoveries(query)
  const pages = disc.data ? Math.max(1, Math.ceil(disc.data.total / PAGE_SIZE)) : 1
  // Any filter change returns to the first page.
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page discoveries-page">
      <h1>{m.par.discoveries.title}</h1>
      <p className="lede">
        {m.par.discoveries.ledeBefore}
        <em>{m.par.discoveries.ledeNot}</em>
        {m.par.discoveries.ledeAfter}
      </p>
      <div className="toolbar">
        <Segmented
          label={m.units.unitType}
          value={unitType}
          onChange={(t) => set({ type: t === 'verse' ? null : t })}
          options={UNIT_TYPES.map((t) => ({ value: t, label: m.units.type(t) }))}
        />
        <ModeToggle value={mode} onChange={(v) => set({ mode: v === DEFAULT_MODE ? null : v })} />
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
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          {m.par.differentBooks}
        </label>
      </div>
      <p className="muted small">{m.modes.hints[mode]}.</p>

      {disc.isPending ? (
        <Loading />
      ) : disc.error ? (
        <ErrorBox error={disc.error} />
      ) : disc.data.items.length === 0 ? (
        <EmptyList total={disc.data.total} limit={disc.data.limit}>{m.par.discoveries.none}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.par.pairsPage(disc.data.total, page, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'discoveries', params: discoveriesParams(query) }}
              filename={`discoveries-${unitType}-${mode}-p${page}.csv`}
              rows={() =>
                disc.data.items.map((d) => ({
                  a: d.a.label_en,
                  b: d.b.label_en,
                  score: d.score,
                  rank_a_to_b: d.rank_ab,
                  rank_b_to_a: d.rank_ba,
                }))
              }
            />
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
  const { m, locale } = useLocale()
  const a = unitLabel(d.a, locale)
  const b = unitLabel(d.b, locale)
  const ranks = [
    d.rank_ab !== null && m.par.discoveries.rankFor(b, d.rank_ab, a),
    d.rank_ba !== null && m.par.discoveries.rankFor(a, d.rank_ba, b),
  ].filter(Boolean)
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="score" title={ranks.join('; ')}>
          {formatScore(d.score)}
        </span>
        {d.rank_ab !== null && d.rank_ba !== null && (
          <span className="mutual-tag" title={m.par.discoveries.mutualTitle}>
            {m.par.discoveries.mutual}
          </span>
        )}
        <span className="hit-actions">
          <Link className="linkish" to={compareLink(d.a.unit_id, d.b.unit_id)} title={m.hit.compareTitle}>
            {m.hit.compare}
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
  const m = useT()
  return (
    <div className="disc-side">
      <Link className="hit-ref" to={unitLink(unit.unit_id)}>
        <UnitName en={unit.label_en} he={unit.label_he} />
      </Link>
      {verse ? (
        <p className="hit-text">
          <HebrewText verse={verse} />
        </p>
      ) : (
        preview && (
          <p className="hit-text preview">
            <HebrewPlain text={preview} />
            {unit.n_verses > 1 && <span className="muted">{m.hit.moreVerses(unit.n_verses)}</span>}
          </p>
        )
      )}
    </div>
  )
}
