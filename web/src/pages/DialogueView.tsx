import { Link } from 'react-router'
import { useBooks, useDialogue, useDialogueBook, useDialogueExchanges } from '../api/hooks'
import type { DialogueMeta, DialogueParty, DialoguePair } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { readLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const NODES = 14

/** Who speaks → To whom (DESIGN.md §16.44): addressees, the three checks, who speaks to whom in a
 * book and the exchanges between two speakers. */
export function DialogueView() {
  const { m, locale } = useLocale()
  const t = m.dlg
  const [params, update] = useQueryParams()
  const res = useDialogue()
  const books = useBooks()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const meta = res.data.meta
  if (!meta.tests || res.data.books.length === 0) return <p className="status">{t.noData}</p>
  const names = new Map(books.data?.map((b) => [b.book_id, bookName(b, locale)]) ?? [])
  const bookParam = params.get('book')
  const book = bookParam !== null && bookParam !== '' ? Number(bookParam) : res.data.books[0].book_id
  const name = names.get(book) ?? String(book)
  return (
    <>
      <p className="lede">{t.lede}</p>
      <Summary meta={meta} />
      <Checks meta={meta} />
      <section aria-label={t.booksTitle}>
        <h2>{t.booksTitle}</h2>
        <div className="toolbar">
          <label className="control">
            <span>{t.book}</span>
            <select value={book} onChange={(e) => update({ book: e.target.value, party: null, page: null })}>
              {res.data.books.map((b) => (
                <option key={b.book_id} value={b.book_id}>
                  {t.bookOption(names.get(b.book_id) ?? String(b.book_id), b.n_quotes)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <BookPairs bookId={book} name={name} />
      </section>
      <Exchanges book={book} name={name} />
    </>
  )
}

function Summary({ meta }: { meta: DialogueMeta }) {
  const t = useLocale().m.dlg
  return (
    <>
      {meta.addressee && <p>{t.summary(meta.quotations ?? 0, meta.with_addressee ?? 0, meta.addressee)}</p>}
      {meta.hand_check && <p className="muted small">{t.handCheck(meta.hand_check)}</p>}
    </>
  )
}

function Verdict({ holds }: { holds: boolean | null | undefined }) {
  const t = useLocale().m.dlg
  if (holds == null) return null
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function Checks({ meta }: { meta: DialogueMeta }) {
  const t = useLocale().m.dlg
  const k = meta.tests!
  const d = k.deference
  const p = k.particle
  const l = k.last_word
  const s = meta.sensitivity
  const o = meta.opener
  const g = meta.lengths
  return (
    <section aria-label={t.checksTitle}>
      <h2>{t.checksTitle}</h2>
      <ol className="dlg-checks">
        <li>
          <Verdict holds={d.holds} /> {t.deference(d.up.rate, d.rest.rate, d.up.count, d.up.of, d.null, d.p)}
        </li>
        <li>
          <Verdict holds={p.holds} /> {t.particle(p.up.rate, p.rest.rate, p.up.count, p.up.of, p.p)}
        </li>
        <li>
          <Verdict holds={l.holds} /> {t.lastWord(l.observed, l.exchanges, l.expected, l.p)}
        </li>
      </ol>
      {s && <p className="small">{t.sensitivity(s.deference.observed, s.deference.p, s.particle.observed, s.particle.p)}</p>}
      {o && g && (
        <p className="small muted">
          {t.described(o.observed, o.exchanges, o.expected, o.p, g.longer, g.shorter, g.median_higher, g.median_lower, g.p)}
        </p>
      )}
    </section>
  )
}

/** A party's name: the Hebrew form, or "God" for the divine names together. */
function Party({ p }: { p: DialogueParty }) {
  const t = useLocale().m.dlg
  return p.he ? (
    <span lang="he" dir="rtl">
      {p.he}
    </span>
  ) : (
    <>{t.god}</>
  )
}

function BookPairs({ bookId, name }: { bookId: number; name: string }) {
  const { m } = useLocale()
  const t = m.dlg
  const [, update] = useQueryParams()
  const res = useDialogueBook(bookId)
  if (res.error) return <PanelError what={t.pairsTitle(name)} error={res.error} />
  if (!res.data) return <Loading />
  const pairs = res.data.pairs
  if (pairs.length === 0) return <p className="status">{t.noPairs}</p>
  const label = (p: DialogueParty) => p.he ?? t.god
  return (
    <>
      <Network pairs={pairs} name={name} />
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.pairsTitle(name)}>
        <table className="change-table dlg-pairs">
          <caption>{t.pairsTitle(name)}</caption>
          <thead>
            <tr>
              <th>{t.cols.speaker}</th>
              <th>{t.cols.addressee}</th>
              <th className="num">{t.cols.quotes}</th>
              <th className="num">{t.cols.words}</th>
              <th className="num">{t.cols.named}</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map((p) => (
              <tr key={`${p.speaker.key}>${p.addressee.key}`}>
                {[p.speaker, p.addressee].map((x, i) => (
                  <td key={i}>
                    <button type="button" className="linkish" title={t.filterParty(label(x))} onClick={() => update({ party: x.key, page: null }, false)}>
                      <Party p={x} />
                    </button>
                  </td>
                ))}
                <td className="num">{p.n_quotes}</td>
                <td className="num">{p.n_words}</td>
                <td className="num">{p.n_reliable}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

/** The book's most active parties on a circle, an arrow from speaker to addressee, thicker with
 * more quotations. */
function Network({ pairs, name }: { pairs: DialoguePair[]; name: string }) {
  const t = useLocale().m.dlg
  const activity = new Map<string, { party: DialogueParty; n: number }>()
  for (const p of pairs) {
    for (const x of [p.speaker, p.addressee]) {
      const a = activity.get(x.key) ?? { party: x, n: 0 }
      a.n += p.n_quotes
      activity.set(x.key, a)
    }
  }
  const nodes = [...activity.values()].sort((a, b) => b.n - a.n || a.party.key.localeCompare(b.party.key)).slice(0, NODES)
  if (nodes.length < 2) return null
  const W = 440
  const H = 400
  const R = 140
  const at = new Map(
    nodes.map((x, i) => {
      const a = (2 * Math.PI * i) / nodes.length - Math.PI / 2
      return [x.party.key, { x: W / 2 + R * Math.cos(a), y: H / 2 + R * Math.sin(a), a }] as const
    }),
  )
  const edges = pairs.filter((p) => at.has(p.speaker.key) && at.has(p.addressee.key))
  const max = Math.max(...edges.map((e) => e.n_quotes), 1)
  return (
    <figure className="dlg-network">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.networkLabel(nodes.length, name)}>
        <title>{t.network(name)}</title>
        <defs>
          <marker id="dlg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="dlg-arrow" />
          </marker>
        </defs>
        {edges.map((e) => {
          const s = at.get(e.speaker.key)!
          const a = at.get(e.addressee.key)!
          const dx = a.x - s.x
          const dy = a.y - s.y
          const len = Math.hypot(dx, dy) || 1
          // bend each direction to its own side so A -> B and B -> A do not overlap
          const mx = (s.x + a.x) / 2 - (dy / len) * 14
          const my = (s.y + a.y) / 2 + (dx / len) * 14
          const ex = a.x - (dx / len) * 9
          const ey = a.y - (dy / len) * 9
          return (
            <path
              key={`${e.speaker.key}>${e.addressee.key}`}
              d={`M${s.x},${s.y} Q${mx},${my} ${ex},${ey}`}
              className="dlg-edge"
              strokeWidth={1 + 5 * Math.sqrt(e.n_quotes / max)}
              markerEnd="url(#dlg-arrow)"
            >
              <title>{t.pairTitle(e.speaker.he ?? t.god, e.addressee.he ?? t.god, e.n_quotes)}</title>
            </path>
          )
        })}
        {nodes.map(({ party }) => {
          const p = at.get(party.key)!
          const lx = W / 2 + (R + 22) * Math.cos(p.a)
          const ly = H / 2 + (R + 22) * Math.sin(p.a)
          const anchor = Math.abs(Math.cos(p.a)) < 0.3 ? 'middle' : Math.cos(p.a) > 0 ? 'start' : 'end'
          return (
            <g key={party.key} className={`dlg-node rank-${party.rank}`}>
              <circle cx={p.x} cy={p.y} r={6} />
              <text x={lx} y={ly + 4} textAnchor={anchor} lang={party.he ? 'he' : undefined}>
                {party.he ?? t.god}
              </text>
            </g>
          )
        })}
      </svg>
    </figure>
  )
}

function Exchanges({ book, name }: { book: number; name: string }) {
  const { m, locale } = useLocale()
  const t = m.dlg
  const [params, update] = useQueryParams()
  const party = params.get('party') ?? undefined
  const unequal = params.get('unequal') === '1'
  const page = parsePage(params.get('page'))
  const res = useDialogueExchanges(book, party, unequal, PAGE_SIZE, (page - 1) * PAGE_SIZE)
  const pairs = useDialogueBook(book).data?.pairs ?? []
  const who = (p: DialogueParty) => p.he ?? t.god
  const named = pairs.flatMap((x) => [x.speaker, x.addressee]).find((x) => x.key === party)
  const partyName = party === undefined ? null : named ? who(named) : party === 'divine' ? t.god : party
  return (
    <section aria-label={t.exchangesTitle}>
      <h2>
        {t.exchangesTitle} · {name}
      </h2>
      <p className="small">{t.exchangesLede}</p>
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={unequal} onChange={(e) => update({ unequal: e.target.checked ? '1' : null, page: null })} />
          {t.unequal}
        </label>
        {partyName !== null && (
          <button type="button" className="chip" onClick={() => update({ party: null, page: null })}>
            {t.party(partyName)} ×
          </button>
        )}
      </div>
      <PagedList
        res={res}
        empty={t.empty}
        summary={(d, p, pages) => (
          <>
            {t.count(d.total)} · {m.pat.pageOf(p, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'exchanges', params: { book, party, unequal: unequal ? 'true' : undefined } }}
              filename={`exchanges-${book}.csv`}
              rows={() =>
                d.items.map((x) => ({
                  first: x.first.label_en,
                  last: x.last_verse.label_en,
                  a: x.a.he ?? x.a.key,
                  b: x.b.he ?? x.b.key,
                  turns: x.turns,
                  last_word: x.last,
                }))
              }
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits dlg-exchanges ${stale}`}>
            {d.items.map((x) => {
              const last = x.last === x.a.key ? x.a : x.b
              const span = locale === 'he' ? `${x.first.label_he} – ${x.last_verse.label_he}` : `${x.first.label_en} – ${x.last_verse.label_en}`
              return (
                <li key={x.exchange} className="hit dlg-exchange">
                  <Link to={readLink(x.unit_id, '?layers=speakers')} title={t.read}>
                    {span}
                  </Link>{' '}
                  <span className="dlg-parties">
                    <Party p={x.a} /> ⇄ <Party p={x.b} />
                  </span>{' '}
                  <span className="muted small">
                    {t.turns(x.turns, who(x.a), x.a_turns, who(x.b), x.turns - x.a_turns)} · {t.last(who(last))}
                  </span>
                </li>
              )
            })}
          </ol>
        )}
      </PagedList>
    </section>
  )
}
