import { Link } from 'react-router'
import { listsParams, sayingsParams, useBooks, useForms, useLists, useSayings } from '../api/hooks'
import type { FormsKind, FormsList, FormsResponse, FormsSaying, VerseLabel } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const KINDS: FormsKind[] = ['genealogy', 'itinerary', 'census', 'offering', 'kings', 'names', 'other']

/** Graded numerical sayings and lists (§16.45): the checks, what was named in advance, and what was found. */
export function FormsPage() {
  const { m } = useLocale()
  const t = m.fm
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'lists' ? 'lists' : 'sayings'
  const res = useForms()
  return (
    <div className="page forms-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <Segmented
          label={t.view}
          value={view}
          onChange={(v) => update({ view: v === 'sayings' ? null : v, page: null, book: null, unit: null, known: null, kind: null })}
          options={[
            { value: 'sayings', label: t.sayingsView },
            { value: 'lists', label: t.listsView },
          ]}
        />
      </div>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.meta.chance == null && res.data.meta.lists.observed == null ? (
        <p className="status">{t.noData}</p>
      ) : view === 'lists' ? (
        <>
          <ListChecks data={res.data} />
          <Lists />
        </>
      ) : (
        <>
          <SayingChecks data={res.data} />
          <Sayings />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.fm
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function VerseLink({ v }: { v: VerseLabel }) {
  const { locale } = useLocale()
  return <Link to={unitLink(`v:${v.verse_id}`)}>{locale === 'he' ? v.label_he : v.label_en}</Link>
}

function SayingChecks({ data }: { data: FormsResponse }) {
  const { m } = useLocale()
  const t = m.fm
  const meta = data.meta
  const alpha = meta.alpha ?? 0.05
  const c = meta.chance
  const par = meta.parallel
  const found = meta.known_found ?? 0
  return (
    <>
      <p>{t.summary(meta.numbers ?? 0, meta.free ?? 0, meta.sayings ?? 0, meta.graded_pairs ?? 0, meta.window ?? 8)}</p>
      <section aria-label={t.checksTitle}>
        <h2>{t.checksTitle}</h2>
        <ol className="dlg-checks">
          {data.known.length > 0 && (
            <li>
              <Verdict holds={found / data.known.length >= (meta.known_share ?? 2 / 3)} /> {t.known(found, data.known.length)}
            </li>
          )}
          {c && (
            <li>
              <Verdict holds={c.observed > c.expected && c.p != null && c.p <= alpha} /> {t.chance(c.observed, c.expected, c.p, meta.shuffles ?? 0)}
              {c.without && c.without_observed != null && (
                <span className="muted small"> {t.without(c.without.join(', '), c.without_observed, c.without_expected ?? 0, c.without_p ?? null)}</span>
              )}
            </li>
          )}
          {par && (
            <li>
              <Verdict holds={par.saying_prob > par.other_prob && par.p != null && par.p <= alpha} />{' '}
              {t.parallel(par.saying_parallel, par.other_parallel, par.saying_prob, par.other_prob, par.p, par.sayings, par.others)}
            </li>
          )}
        </ol>
        {meta.steps && (
          <p className="small muted">
            {t.stepsTitle}:{' '}
            {Object.entries(meta.steps)
              .map(([s, n]) => t.step(s, n))
              .join(' · ')}
          </p>
        )}
      </section>
      <section aria-label={t.knownTitle}>
        <h2>{t.knownTitle}</h2>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.knownCols.name}</th>
                <th>{t.knownCols.where}</th>
                <th>{t.knownCols.found}</th>
              </tr>
            </thead>
            <tbody>
              {data.known.map((k) => (
                <tr key={k.name}>
                  <td dir="rtl" lang="he" className="he-cell">
                    {k.name}
                  </td>
                  <td>
                    <VerseLink v={k.first} />
                  </td>
                  <td className={k.found ? undefined : 'muted'}>{t.hits(k.hits, k.n_verses)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function BookSelect({ book, onChange }: { book: number | undefined; onChange: (b: string | null) => void }) {
  const { m, locale } = useLocale()
  const books = useBooks()
  return (
    <label className="control">
      <span>{m.search.book}</span>
      <select value={book ?? ''} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">{m.search.allBooks}</option>
        {books.data?.map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {bookOption(b, locale)}
          </option>
        ))}
      </select>
    </label>
  )
}

function useFilters() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return { params, book, unit, page, set }
}

function Sayings() {
  const { m } = useLocale()
  const t = m.fm
  const { params, book, unit, page, set } = useFilters()
  const known = params.get('known') === '1'
  const query = { book, unit, known, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useSayings(query)
  return (
    <section aria-label={t.sayingsTitle}>
      <h2>{t.sayingsTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <BookSelect book={book} onChange={(b) => set({ book: b })} />
        <label className="check">
          <input type="checkbox" checked={known} onChange={(e) => set({ known: e.target.checked ? '1' : null })} />
          {t.knownOnly}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.emptySayings}
        summary={(d, p, pages) => (
          <>
            {t.sayingCount(d.total)} · {m.pat.pageOf(p, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'sayings', params: sayingsParams(query) }}
              filename={`sayings-p${p}.csv`}
              rows={() => d.items.map((s) => ({ verse: s.verse.ref, steps: s.steps, parallel: s.prob ?? '', known: s.known ?? '' }))}
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((s) => (
              <SayingItem key={s.verse.verse_id} s={s} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function SayingItem({ s }: { s: FormsSaying }) {
  const t = useLocale().m.fm
  const hl: Highlight = new Map()
  for (const p of s.pairs) {
    if (p.a_tok != null) hl.set(p.a_tok, 'shared')
    if (p.b_tok != null) hl.set(p.b_tok, 'shared')
  }
  return (
    <li className="hit saying">
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${s.verse.verse_id}`)}>
          <UnitName en={s.verse.ref} he={s.verse.ref_he} />
        </Link>{' '}
        <span className="type-tag">{s.steps}</span>{' '}
        <span className="muted small">
          {s.prob != null && t.parallelTag(s.prob)}
          {s.known && (
            <>
              {s.prob != null && ' · '}
              {t.named}
              <span dir="rtl" lang="he">
                {s.known}
              </span>
            </>
          )}
        </span>
      </div>
      <p className="hit-text">
        <HebrewText verse={s.verse} highlight={hl} />
      </p>
    </li>
  )
}

function ListChecks({ data }: { data: FormsResponse }) {
  const { m, locale } = useLocale()
  const t = m.fm
  const li = data.meta.lists
  const found = li.known_found ?? 0
  const n = data.known_lists.length
  return (
    <>
      {li.observed != null && (
        <p>{t.listsSummary(li.observed, li.expected ?? 0, li.shuffles ?? 0, li.verses ?? 0, li.min_verses ?? 5)}</p>
      )}
      {n > 0 && (
        <section aria-label={t.checksTitle}>
          <h2>{t.checksTitle}</h2>
          <ol className="dlg-checks">
            <li>
              <Verdict holds={found / n >= (li.known_share ?? 2 / 3) && (li.observed ?? 0) > (li.expected ?? 0)} />{' '}
              {t.listsCheck(found, n, li.observed ?? 0, li.expected ?? 0)}
            </li>
          </ol>
        </section>
      )}
      <section aria-label={t.knownListsTitle}>
        <h2>{t.knownListsTitle}</h2>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownListsTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.knownListsCols.name}</th>
                <th>{t.knownListsCols.span}</th>
                <th className="num">{t.knownListsCols.covered}</th>
              </tr>
            </thead>
            <tbody>
              {data.known_lists.map((k) => (
                <tr key={k.name}>
                  <td>{k.name}</td>
                  <td>
                    <Link to={unitLink(`v:${k.first.verse_id}`)}>
                      {t.span(locale === 'he' ? k.first.label_he : k.first.label_en, locale === 'he' ? k.last_verse.label_he : k.last_verse.label_en)}
                    </Link>
                  </td>
                  <td className={`num${k.found ? '' : ' muted'}`}>{t.covered(k.covered, k.n_verses)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {li.kinds && (
        <section aria-label={t.kindsTitle}>
          <h2>{t.kindsTitle}</h2>
          <p className="small">
            {KINDS.filter((k) => li.kinds?.[k])
              .map((k) => `${t.kind[k]} ${li.kinds![k]}`)
              .join(' · ')}
          </p>
          <p className="small muted">{t.kindsLede}</p>
        </section>
      )}
    </>
  )
}

function Lists() {
  const { m } = useLocale()
  const t = m.fm
  const { params, book, unit, page, set } = useFilters()
  const rawKind = params.get('kind') as FormsKind | null
  const kind = rawKind && KINDS.includes(rawKind) ? rawKind : undefined
  const query = { book, unit, kind, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useLists(query)
  return (
    <section aria-label={t.listsTitle}>
      <h2>{t.listsTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <BookSelect book={book} onChange={(b) => set({ book: b })} />
        <label className="control">
          <span>{t.kindFilter}</span>
          <select value={kind ?? ''} onChange={(e) => set({ kind: e.target.value || null })}>
            <option value="">{t.allKinds}</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t.kind[k]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.emptyLists}
        summary={(d, p, pages) => (
          <>
            {t.listCount(d.total)} · {m.pat.pageOf(p, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'lists', params: listsParams(query) }}
              filename={`lists-p${p}.csv`}
              rows={() =>
                d.items.map((l) => ({ first: l.first.label_en, last: l.last_verse.label_en, verses: l.n_verses, kind: l.kind, known: l.known ?? '' }))
              }
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((l) => (
              <ListItem key={l.list_id} l={l} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function ListItem({ l }: { l: FormsList }) {
  const { m, locale } = useLocale()
  const t = m.fm
  const label = (v: VerseLabel) => (locale === 'he' ? v.label_he : v.label_en)
  return (
    <li className="hit list">
      <div className="hit-head">
        <Link to={unitLink(`v:${l.first.verse_id}`)}>{t.span(label(l.first), label(l.last_verse))}</Link>{' '}
        <span className="type-tag">{t.kind[l.kind]}</span>{' '}
        <span className="muted small">
          {t.verses(l.n_verses, l.n_like)} · {t.likeness(l.likeness)}
          {l.known && (
            <>
              {' · '}
              {t.named}
              {l.known}
            </>
          )}
        </span>{' '}
        <Link className="small" to={unitLink(l.unit_id)}>
          {t.read}
        </Link>
      </div>
      {l.verses.map((v) => (
        <p key={v.verse_id} className="hit-text">
          <Link className="verse-ref small" to={unitLink(`v:${v.verse_id}`)}>
            <UnitName en={v.ref} he={v.ref_he} />
          </Link>{' '}
          <HebrewText verse={v} />
        </p>
      ))}
      {l.n_verses > l.verses.length && <p className="muted small">{t.more(l.n_verses - l.verses.length)}</p>}
    </li>
  )
}
