import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useBasemap, usePlaceArc, usePlaceArcBook } from '../api/hooks'
import type { ArcBook, ArcChapter, ArcMove, ArcMoveEnd, ArcOracles, PlaceArcResponse } from '../api/types'
import { GeoMap } from '../components/GeoMap'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { type Bounds, fitBounds, type GeoPoint, VIEWS } from '../lib/geo'
import { unitLink } from '../lib/links'
import { bookName, unitLabel } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const LONGEST = 3 // steps marked as the longest

/** The geographic arc (§16.60): each chapter placed at the mean of the places it names; a book's
 * chapters as a path on the map against shuffled orders, the story's known moves, and the oracles
 * against the nations against the other chapters of the prophets. */
export function PlaceArcPage() {
  const { m } = useLocale()
  const t = m.pa
  const res = usePlaceArc()
  return (
    <div className="page place-arc-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.arc ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Summary data={res.data} />
          <BookPath books={res.data.books} alpha={res.data.meta.alpha ?? 0.05} />
          <Books books={res.data.books} alpha={res.data.meta.alpha ?? 0.05} />
          {res.data.moves.length > 0 && <Moves moves={res.data.moves} />}
          {res.data.oracles && <Oracles oracles={res.data.oracles} />}
          <p className="muted small">{t.credit}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.pa
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function Summary({ data }: { data: PlaceArcResponse }) {
  const t = useLocale().m.pa
  const a = data.arc!
  const alpha = data.meta.alpha ?? 0.05
  if (a.p == null || a.mean_step == null || a.null_mean == null) return null
  return (
    <>
      <p>
        <Verdict holds={a.p <= alpha && a.mean_step < a.null_mean} /> {t.summary(a.placed, a.chapters, a.mean_step, a.null_mean, a.p, data.meta.shuffles ?? 0)}{' '}
        {t.booksHeld(a.books_held, a.books)}
      </p>
      <p className="muted small">{t.caveat(data.meta.min_mentions ?? 2)}</p>
    </>
  )
}

/** The book shown: `?book=`, else the first book tested. */
function useBook(books: ArcBook[]): [ArcBook | undefined, (id: number) => void] {
  const [params, update] = useQueryParams()
  const asked = Number(params.get('book'))
  const fallback = books.find((b) => b.p != null) ?? books[0]
  const book = books.find((b) => params.get('book') != null && b.book_id === asked) ?? fallback
  return [book, (id: number) => update({ book: id === fallback?.book_id ? null : String(id) }, false)]
}

function BookPath({ books, alpha }: { books: ArcBook[]; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.pa
  const [book, setBook] = useBook(books)
  const res = usePlaceArcBook(book?.book_id)
  const basemap = useBasemap()
  const [picked, setPicked] = useState<number>()
  const [moved, setMoved] = useState<{ book: number; bounds: Bounds }>()
  const chapters = useMemo(() => (res.data && res.data.book.book_id === book?.book_id ? res.data.items : []), [res.data, book])
  const byNumber = useMemo(() => new Map(chapters.map((c) => [c.chapter, c])), [chapters])
  const points: GeoPoint[] = useMemo(() => chapters.map((c) => ({ place_id: c.chapter, he: unitLabel(c, locale), kind: null, lat: c.lat, lon: c.lon, n: c.n_mentions })), [chapters, locale])
  const longest = useMemo(
    () =>
      new Set(
        chapters
          .filter((c) => c.step_km != null)
          .sort((x, y) => (y.step_km ?? 0) - (x.step_km ?? 0))
          .slice(0, LONGEST)
          .map((c) => c.chapter),
      ),
    [chapters],
  )
  if (!book) return null
  const name = bookName(book, locale)
  const bounds = moved?.book === book.book_id ? moved.bounds : (fitBounds(points) ?? VIEWS.east)
  return (
    <section className="pa-book" aria-label={t.bookTitle(name)}>
      <h2>{t.bookTitle(name)}</h2>
      <div className="toolbar">
        <label className="control">
          <span>{t.book}</span>
          <select
            value={book.book_id}
            onChange={(e) => {
              setPicked(undefined)
              setBook(Number(e.target.value))
            }}
          >
            {books.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookName(b, locale)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p>
        {book.p != null && book.mean_step != null && book.null_mean != null ? (
          <>
            <Verdict holds={book.p <= alpha && book.mean_step < book.null_mean} /> {t.bookNote(book.n, book.chapters, book.mean_step, book.null_mean, book.p)}
          </>
        ) : (
          t.bookUntested(book.n, book.chapters)
        )}
      </p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : (
        <div className="places-layout">
          <div className="places-map">
            <GeoMap
              basemap={basemap.data}
              points={points}
              bounds={bounds}
              onBounds={(b) => setMoved({ book: book.book_id, bounds: b })}
              selected={picked}
              onSelect={setPicked}
              label={t.mapLabel(name)}
              labels={points.length}
              paths={[{ key: 'arc', className: 'pa-path', coords: chapters.map((c) => [c.lon, c.lat] as [number, number]) }]}
              fillOf={(p) => (byNumber.get(p.place_id)?.oracle ? 'var(--geo-town)' : 'var(--accent)')}
              labelOf={(p) => t.chapterNumber(p.place_id)}
              titleOf={(p) => {
                const c = byNumber.get(p.place_id)
                return c ? t.pointTitle(unitLabel(c, locale), c.n_mentions, c.spread_km) : p.he
              }}
            />
          </div>
          <aside className="places-side">
            <h3>{t.chaptersTitle}</h3>
            <p className="muted small">{t.chaptersLede}</p>
            <ol className="pa-chapters">
              {chapters.map((c) => (
                <ChapterItem key={c.chapter} c={c} long={longest.has(c.chapter)} on={c.chapter === picked} onPick={() => setPicked(c.chapter)} />
              ))}
            </ol>
          </aside>
        </div>
      )}
    </section>
  )
}

function ChapterItem({ c, long, on, onPick }: { c: ArcChapter; long: boolean; on: boolean; onPick: () => void }) {
  const { m, locale } = useLocale()
  const t = m.pa
  const label = unitLabel(c, locale)
  // the chapter a step comes from is named when the chapters between were not placed
  const step = c.step_km == null ? null : c.prev_chapter != null && c.prev_chapter !== c.chapter - 1 ? t.stepFrom(c.step_km, c.prev_chapter) : t.step(c.step_km)
  return (
    <li className={[long ? 'long' : '', on ? 'on' : ''].join(' ').trim() || undefined}>
      <Link to={unitLink(c.unit_id)}>{label}</Link>{' '}
      {c.top_place && (
        <button type="button" className="linkish" onClick={onPick}>
          <span dir="rtl" lang="he" className="he">
            {c.top_place.he}
          </span>
        </button>
      )}{' '}
      {step && <span className={long ? 'pa-km long' : 'pa-km muted small'}>{step}</span>} <span className="muted small">· {t.spread(c.spread_km)}</span>
      {c.oracle && <span className="type-tag">{t.oracleTag}</span>}{' '}
      <Link className="small" to={`/places?unit=${encodeURIComponent(c.unit_id)}`} aria-label={t.onMap(label)}>
        ↗
      </Link>
    </li>
  )
}

function Books({ books, alpha }: { books: ArcBook[]; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.pa
  const [book, setBook] = useBook(books)
  return (
    <section aria-label={t.booksTitle}>
      <h2>{t.booksTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
        <table className="change-table pa-table">
          <thead>
            <tr>
              <th>{t.cols.book}</th>
              <th>{t.cols.placed}</th>
              <th>{t.cols.step}</th>
              <th>{t.cols.shuffled}</th>
              <th title={t.colHints.ratio}>{t.cols.ratio}</th>
              <th>{t.cols.p}</th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => {
              const on = b.book_id === book?.book_id
              return (
                <tr key={b.book_id} className={on ? 'on' : undefined} aria-current={on ? 'true' : undefined}>
                  <td>
                    <button type="button" className="linkish" onClick={() => setBook(b.book_id)} aria-label={t.open(bookName(b, locale))}>
                      {bookName(b, locale)}
                    </button>
                  </td>
                  <td>{t.placedOf(b.n, b.chapters)}</td>
                  {b.p == null || b.mean_step == null || b.null_mean == null ? (
                    <td colSpan={4} className="muted">
                      {t.untested}
                    </td>
                  ) : (
                    <>
                      <td>{t.km(b.mean_step)}</td>
                      <td>{t.km(b.null_mean)}</td>
                      <td>{b.ratio == null ? '–' : t.ratio(b.ratio)}</td>
                      <td>
                        <Verdict holds={b.p <= alpha && b.mean_step < b.null_mean} /> {fp(b.p)}
                      </td>
                    </>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

function Moves({ moves }: { moves: ArcMove[] }) {
  const { m, locale } = useLocale()
  const t = m.pa
  const basemap = useBasemap()
  const [moved, setMoved] = useState<Bounds>()
  const region = (k: string) => t.regions[k] ?? k
  const moveName = (k: string) => t.moves[k] ?? k
  const tested = moves.filter((x) => x.holds != null)
  // two points per move, numbered from 1: its start (odd) and its end (even)
  const ends = moves.flatMap((x, i) => [...(x.start ? [{ id: 2 * i + 1, e: x.start, move: x }] : []), ...(x.end ? [{ id: 2 * i + 2, e: x.end, move: x }] : [])])
  const points: GeoPoint[] = ends.map(({ id, e }) => ({ place_id: id, he: unitLabel(e, locale), kind: null, lat: e.lat, lon: e.lon, n: e.n_mentions }))
  const titles = new Map(ends.map(({ id, e, move }) => [id, t.moveTitle(moveName(move.key), unitLabel(e, locale))]))
  const bounds = moved ?? fitBounds(points, 4) ?? VIEWS.east
  const endCell = (e: ArcMoveEnd | null | undefined, x: ArcMove) =>
    e ? (
      <>
        <Link to={unitLink(e.unit_id)}>{unitLabel(e, locale)}</Link>
        <div className="muted small">{t.endNote(e.to_from_region, region(x.from_region), e.to_to_region, region(x.to_region))}</div>
      </>
    ) : (
      <span className="muted">{t.unplaced}</span>
    )
  return (
    <section className="pa-moves" id="moves" aria-label={t.movesTitle}>
      <h2>{t.movesTitle}</h2>
      <p className="muted small">{t.movesLede}</p>
      <p>{t.movesSummary(tested.filter((x) => x.holds).length, tested.length)}</p>
      <div className="places-layout pa-moves-layout">
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.movesTitle}>
          <table className="change-table pa-table">
            <thead>
              <tr>
                <th>{t.mcols.move}</th>
                <th>{t.mcols.before}</th>
                <th>{t.mcols.after}</th>
                <th>{t.mcols.km}</th>
              </tr>
            </thead>
            <tbody>
              {moves.map((x) => (
                <tr key={x.key}>
                  <td>
                    {moveName(x.key)}
                    {x.holds != null && (
                      <div>
                        <Verdict holds={x.holds} />
                      </div>
                    )}
                  </td>
                  <td>{endCell(x.start, x)}</td>
                  <td>{endCell(x.end, x)}</td>
                  <td>{x.km == null ? '–' : t.km(x.km)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="places-map">
          <GeoMap
            basemap={basemap.data}
            points={points}
            bounds={bounds}
            onBounds={setMoved}
            onSelect={() => undefined}
            label={t.movesMap}
            paths={moves.flatMap((x) => (x.start && x.end ? [{ key: x.key, className: 'pa-path move', coords: [[x.start.lon, x.start.lat] as [number, number], [x.end.lon, x.end.lat] as [number, number]] }] : []))}
            fillOf={(p) => (p.place_id % 2 ? 'var(--geo-none)' : 'var(--accent)')}
            titleOf={(p) => titles.get(p.place_id) ?? p.he}
          />
        </div>
      </div>
    </section>
  )
}

function Oracles({ oracles: o }: { oracles: ArcOracles }) {
  const { m, locale } = useLocale()
  const t = m.pa
  const refs = (locale === 'he' ? o.labels_he : o.labels_en).join(', ')
  const tests = (['spread', 'reach'] as const).flatMap((k) => (o[k] ? [{ key: k, r: o[k] }] : []))
  return (
    <section className="pa-oracles" id="oracles" aria-label={t.oraclesTitle}>
      <h2>{t.oraclesTitle}</h2>
      <p>
        {o.holds != null && <Verdict holds={o.holds} />} {t.oraclesLede(refs)} {t.oracleVerdict(o.alpha)}
      </p>
      {tests.length > 0 && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.oraclesTitle}>
          <table className="change-table pa-table">
            <thead>
              <tr>
                <th>{t.ocols.measure}</th>
                <th>{t.ocols.oracles}</th>
                <th>{t.ocols.others}</th>
                <th>{t.ocols.shuffled}</th>
                <th>{t.ocols.p}</th>
              </tr>
            </thead>
            <tbody>
              {tests.map(({ key, r }) => (
                <tr key={key}>
                  <td>{t.measures[key] ?? key}</td>
                  <td>{t.meanMedian(r.observed, r.median, r.n)}</td>
                  <td>{t.meanMedian(r.other, r.other_median, r.n_other)}</td>
                  <td>{t.km(r.null_mean)}</td>
                  <td>
                    <Verdict holds={r.p <= o.alpha} /> {fp(r.p)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {o.items.length > 0 && (
        <>
          <h3>{t.oracleChapters}</h3>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t.oracleChapters}>
            <table className="change-table pa-table pa-oracle-chapters">
              <thead>
                <tr>
                  <th>{t.chcols.chapter}</th>
                  <th>{t.chcols.place}</th>
                  <th>{t.chcols.places}</th>
                  <th>{t.chcols.spread}</th>
                  <th>{t.chcols.reach}</th>
                </tr>
              </thead>
              <tbody>
                {o.items.map((c) => (
                  <tr key={c.unit_id}>
                    <td>
                      <Link to={unitLink(c.unit_id)}>{unitLabel(c, locale)}</Link>
                    </td>
                    <td>
                      {c.top_place && (
                        <Link to={`/places?p=${c.top_place.place_id}`} dir="rtl" lang="he" className="he">
                          {c.top_place.he}
                        </Link>
                      )}
                    </td>
                    <td>{c.n_places}</td>
                    <td>{t.km(c.spread_km)}</td>
                    <td>{t.km(c.reach_km)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
