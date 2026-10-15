import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useBasemap, useBooks, usePlace, usePlaces, usePlaceVerses } from '../api/hooks'
import type { Book, PlaceKind } from '../api/types'
import { Segmented } from '../components/Controls'
import { GeoMap } from '../components/GeoMap'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { type Bounds, fitBounds, geoPoints, VIEWS, type ViewName } from '../lib/geo'
import type { Highlight } from '../lib/highlight'
import { hebrewNumeral } from '../lib/hebrew'
import { nameLink, unitLink } from '../lib/links'
import { bookName, bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const KINDS: PlaceKind[] = ['town', 'region', 'landform', 'water']
const LABELS = 12 // names written on the map
const LIST_SHOWN = 20
const VERSES_PAGE = 10

/** Places on the map (§16.57): every place the text names, filtered by book, chapter, unit and
 * kind, with a panel for one place. */
export function PlacesPage() {
  const { m, locale } = useLocale()
  const t = m.pl
  const [params, update] = useQueryParams()
  const books = useBooks()
  const num = (k: string) => {
    const v = params.get(k)
    return v === null || v === '' || !Number.isFinite(Number(v)) ? undefined : Number(v)
  }
  const book = num('book')
  const chapter = book === undefined ? undefined : num('chapter')
  const unitParam = params.get('unit') ?? undefined
  const unit = unitParam ?? (book !== undefined && chapter !== undefined ? `c:${book}:${chapter}` : undefined)
  const k = params.get('kind')
  const kind = KINDS.includes(k as PlaceKind) ? (k as PlaceKind) : undefined
  const selected = num('p')
  const scoped = book !== undefined || unit !== undefined
  const v = params.get('view')
  const view: ViewName | 'fit' = v === 'land' || v === 'east' || v === 'fit' ? v : scoped ? 'fit' : 'land'
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  const places = usePlaces({ kind, book: unit ? undefined : book, unit })
  const basemap = useBasemap()
  const items = places.data?.items ?? []
  const points = useMemo(() => geoPoints(places.data?.items ?? []), [places.data])
  const scopeKey = `${view}|${book}|${unit}|${kind}|${points.length}`
  const [moved, setMoved] = useState<{ key: string; bounds: Bounds }>()
  const standing = view === 'fit' ? (fitBounds(points) ?? VIEWS.land) : VIEWS[view]
  const bounds = moved && moved.key === scopeKey ? moved.bounds : standing
  const bk = books.data?.find((b) => b.book_id === book)

  return (
    <div className="page places-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {unitParam && <UnitFilter unitId={unitParam} onClear={() => set({ unit: null, p: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null, chapter: null, unit: null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        {bk && !unitParam && (
          <label className="control">
            <span>{t.chapter}</span>
            <select value={chapter ?? ''} onChange={(e) => set({ chapter: e.target.value || null })}>
              <option value="">{t.allChapters}</option>
              {Array.from({ length: bk.n_chapters }, (_, i) => i + 1).map((c) => (
                <option key={c} value={c}>
                  {locale === 'he' ? hebrewNumeral(c) : c}
                </option>
              ))}
            </select>
          </label>
        )}
        <Segmented
          label={t.kind}
          value={kind ?? 'all'}
          onChange={(x) => set({ kind: x === 'all' ? null : x })}
          options={[{ value: 'all', label: t.all }, ...KINDS.map((x) => ({ value: x, label: t.kinds[x] }))]}
        />
        <Segmented
          label={t.view}
          value={view}
          onChange={(x) => update({ view: x === (scoped ? 'fit' : 'land') ? null : x }, false)}
          options={(['land', 'east', 'fit'] as const).map((x) => ({ value: x, label: t.views[x] }))}
        />
      </div>
      {places.isPending ? (
        <Loading />
      ) : places.error ? (
        <ErrorBox error={places.error} />
      ) : !places.data.meta.places ? (
        <p className="status">{t.noData}</p>
      ) : (
        <div className="places-layout">
          <div className="places-map">
            <p className="muted small">{t.summary(items.length, points.length)}</p>
            <GeoMap
              basemap={basemap.data}
              points={points}
              bounds={bounds}
              onBounds={(b) => setMoved({ key: scopeKey, bounds: b })}
              selected={selected}
              onSelect={(id) => set({ p: String(id) })}
              label={t.mapLabel}
              labels={LABELS}
            />
            <ul className="geo-legend small" aria-label={t.kind}>
              {KINDS.map((x) => (
                <li key={x}>
                  <span className={`geo-key kind-${x}`} aria-hidden="true" /> {t.kindOne[x]}
                </li>
              ))}
            </ul>
            <p className="muted small">{t.credit}</p>
          </div>
          <aside className="places-side">
            {selected !== undefined ? (
              <PlacePanel placeId={selected} books={books.data ?? []} onPick={(id) => set({ p: String(id) })} onClose={() => set({ p: null })} />
            ) : (
              <section aria-label={t.listTitle}>
                <h2>{t.listTitle}</h2>
                <p className="muted small">{t.listLede}</p>
                <ol className="place-list">
                  {items.slice(0, LIST_SHOWN).map((p) => (
                    <li key={p.place_id}>
                      <button type="button" className="linkish" onClick={() => set({ p: String(p.place_id) })}>
                        <span dir="rtl" lang="he" className="he">
                          {p.he}
                        </span>
                      </button>{' '}
                      {p.kind && <span className={`type-tag place-${p.kind}`}>{t.kindOne[p.kind]}</span>}{' '}
                      <span className="muted small">{t.verseCount(p.n_here ?? p.n_verses)}</span>
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

function PlacePanel({ placeId, books, onPick, onClose }: { placeId: number; books: Book[]; onPick: (id: number) => void; onClose: () => void }) {
  const { m, locale } = useLocale()
  const t = m.pl
  const names = m.ov.names
  const res = usePlace(placeId)
  const [params] = useQueryParams()
  const page = parsePage(params.get('page'))
  const verses = usePlaceVerses(placeId, VERSES_PAGE, (page - 1) * VERSES_PAGE)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { place: p, by_book, partners } = res.data
  const counts = new Map(by_book.map((b) => [b.book_id, b.n_verses]))
  const max = Math.max(1, ...by_book.map((b) => b.n_verses))
  return (
    <section className="place-panel" aria-label={t.panel}>
      <div className="word-head">
        <h2>
          <span dir="rtl" lang="he" className="he">
            {p.he}
          </span>{' '}
          {p.kind && <span className={`type-tag place-${p.kind}`}>{t.kindOne[p.kind]}</span>}
        </h2>
        <button type="button" className="linkish" onClick={onClose}>
          {t.close}
        </button>
      </div>
      <p className="small">
        {p.lat != null && p.lon != null ? names.coords(p.lat, p.lon) : names.unlocated}
        {p.score != null ? ` · ${names.votes(p.score)}` : p.coord_source === 'tipnr' ? ` · ${names.tipnrPoint}` : ''}
        {p.runner_up != null ? ` · ${names.contested(p.runner_up)}` : ''}
      </p>
      <p className="muted small">
        {t.verseCount(p.n_verses)}, {t.firstNamed} <Link to={unitLink(`v:${p.first_vid}`)}>{locale === 'he' ? res.data.first_label_he : res.data.first_label}</Link>
      </p>
      <h3>{t.names}</h3>
      <p className="unit-names">
        {res.data.names.map((n) => (
          <Link key={n.lemma} to={nameLink(n.lemma)} className="name-chip">
            <span dir="rtl" lang="he" className="he">
              {n.he}
            </span>
            <span className="muted small">{n.n_verses}</span>
          </Link>
        ))}
      </p>
      <h3>{t.perBook}</h3>
      <ol className="book-strip" aria-label={t.perBook} dir="ltr">
        {books.map((b) => {
          const n = counts.get(b.book_id) ?? 0
          return (
            <li key={b.book_id} title={t.bookCount(bookName(b, locale), n)}>
              <span className="strip-bar" style={{ height: `${(n / max) * 100}%`, opacity: n ? 1 : 0 }} />
            </li>
          )
        })}
      </ol>
      <p className="muted small strip-axis" dir="ltr">
        <span>{books.length ? bookName(books[0], locale) : ''}</span>
        <span>{books.length ? bookName(books[books.length - 1], locale) : ''}</span>
      </p>
      {partners.length > 0 && (
        <>
          <h3>{t.partners}</h3>
          <ul className="partner-list">
            {partners.map((q) => (
              <li key={q.place_id}>
                <button type="button" className="linkish" onClick={() => onPick(q.place_id)} title={t.partnerTitle(q.n_verses)}>
                  <span dir="rtl" lang="he" className="he">
                    {q.he}
                  </span>
                </button>{' '}
                <span className="muted small">{q.n_verses}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <h3>{t.verses}</h3>
      <PagedList res={verses} empty={t.emptyVerses} summary={(d, pg, pages) => `${t.verseCount(d.total)} · ${t.pageOf(pg, pages)}`}>
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((x) => {
              const hl: Highlight = new Map(x.tokens.map((i) => [i, 'focus']))
              return (
                <li key={x.verse.verse_id} className="hit place-verse">
                  <Link className="verse-ref" to={unitLink(`v:${x.verse.verse_id}`)}>
                    {locale === 'he' ? x.verse.ref_he : x.verse.ref}
                  </Link>
                  <p className="hit-text">
                    <HebrewText verse={x.verse} highlight={hl} />
                  </p>
                </li>
              )
            })}
          </ol>
        )}
      </PagedList>
    </section>
  )
}
