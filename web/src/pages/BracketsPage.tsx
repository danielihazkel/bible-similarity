import { Link } from 'react-router'
import { useBooks, useBracketItems, useBrackets } from '../api/hooks'
import type { Bracket, BracketOrder, BracketShow, BracketsResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { readLink, unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const SHOWS: BracketShow[] = ['all', 'strong', 'known']
const ORDERS: BracketOrder[] = ['canon', 'strongest']

/** Resumptive repetition (§16.67): clauses said again after a block, how much the block interrupts
 * the text around it against random brackets, and the two checks. */
export function BracketsPage() {
  const { m } = useLocale()
  const t = m.brk
  const res = useBrackets()
  const d = res.data
  return (
    <div className="page brackets-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Repetitions d={d} />
          <p className="muted small">{t.method}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.brk
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: BracketsResponse }) {
  const t = useLocale().m.brk
  return (
    <section aria-labelledby="brk-checks">
      <h2 id="brk-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.claim.title} <Verdict holds={d.holds} />
          </h3>
          {d.mean !== null && d.mean_null !== null && <p>{t.claim.text(d.brackets, d.mean, d.mean_null, d.p, d.leads, d.strong)}</p>}
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(d.known_found, d.known_beat, d.known.length)}</p>
          <ul className="brk-known small">
            {d.known.map((k) => (
              <li key={`${k.a}|${k.b}`}>
                {k.a} … {k.b}: {k.found ? t.known.found : t.known.missing}
                {k.p !== null && <> · {t.known.beats(k.p)}</>}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  )
}

function Repetitions({ d }: { d: BracketsResponse }) {
  const { m, locale } = useLocale()
  const t = m.brk
  const [params, update] = useQueryParams()
  const sp = params.get('show')
  const show: BracketShow = sp === 'strong' || sp === 'known' ? sp : 'all'
  const order: BracketOrder = params.get('order') === 'strongest' ? 'strongest' : 'canon'
  const bp = params.get('book')
  const book = bp === null || bp === '' ? undefined : Number(bp)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const named = new Map((books.data ?? []).map((b) => [b.book_id, b]))
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useBracketItems({ show, order, book, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <section aria-labelledby="brk-list">
      <h2 id="brk-list">{t.listTitle}</h2>
      <div className="toolbar">
        <Segmented<BracketShow> label={t.show.label} value={show} options={SHOWS.map((v) => ({ value: v, label: t.show[v] }))} onChange={(v) => set({ show: v === 'all' ? null : v })} />
        <Segmented<BracketOrder> label={t.order.label} value={order} options={ORDERS.map((v) => ({ value: v, label: t.order[v] }))} onChange={(v) => set({ order: v === 'canon' ? null : v })} />
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.search.allBooks}</option>
            {d.books.map((b) => {
              const x = named.get(b.book_id)
              return (
                <option key={b.book_id} value={b.book_id}>
                  {x ? bookOption(x, locale) : b.book_id} ({b.brackets})
                </option>
              )
            })}
          </select>
        </label>
      </div>
      <PagedList res={res} empty={t.empty} summary={(p, n, pages) => `${t.count(p.total)} · ${t.pageOf(n, pages)}`}>
        {(p, stale) => (
          <ol className={`hits brk-list ${stale}`}>
            {p.items.map((b) => (
              <BracketItem key={b.bracket} b={b} alpha={d.alpha} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function BracketItem({ b, alpha }: { b: Bracket; alpha: number }) {
  const t = useLocale().m.brk
  const mark = (toks: number[]): Highlight => new Map(toks.map((i) => [i, 'shared'] as const))
  return (
    <li className={`hit brk-bracket${b.p <= alpha ? ' brk-strong' : ''}`}>
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${b.a.verse_id}`)}>
          <UnitName en={b.a.ref} he={b.a.ref_he} />
        </Link>{' '}
        …{' '}
        <Link className="verse-ref" to={unitLink(`v:${b.b.verse_id}`)}>
          <UnitName en={b.b.ref} he={b.b.ref_he} />
        </Link>{' '}
        <span className="muted small">{t.between(b.between)}</span>
        <span className="small"> · {t.score(b.insertion)}</span>
        <span className="muted small">
          {' '}
          ({t.parts(b.lex, b.sem)}) · {t.pq(b.p, b.q)}
        </span>
        {b.known && <span className="muted small"> · {t.knownTag}</span>}
      </div>
      <p className="hit-text">
        <HebrewText verse={b.a} highlight={mark(b.a_disp)} />
      </p>
      <p className="hit-text">
        <HebrewText verse={b.b} highlight={mark(b.b_disp)} />
      </p>
      <p className="small brk-links">
        <Link to={readLink(b.unit_id)}>{t.read}</Link> · <Link to={`/compare?a=${encodeURIComponent(`v:${b.a.verse_id}`)}&b=${encodeURIComponent(`v:${b.b.verse_id}`)}`}>{t.compare}</Link>
      </p>
    </li>
  )
}
