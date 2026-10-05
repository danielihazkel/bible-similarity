import { useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useEntities, useEntity } from '../api/hooks'
import type { Book, EntityDetail, EntityKind } from '../api/types'
import { Segmented } from '../components/Controls'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { lemmaLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 60
const KIND_LABELS: Record<EntityKind, string> = { person: 'Person', place: 'Place', mixed: 'Person / place', unclear: 'Unclear' }
const KINDS = Object.keys(KIND_LABELS) as EntityKind[]

/** People and places: who is mentioned where, and who appears with whom. */
export function NamesPage() {
  const [params, update] = useQueryParams()
  const rawKind = params.get('kind') as EntityKind | null
  const kind = rawKind && KINDS.includes(rawKind) ? rawKind : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const q = params.get('q') ?? ''
  const selected = params.get('e') ?? undefined
  const page = parsePage(params.get('page'))
  const [draft, setDraft] = useState(q)
  const books = useBooks()
  const res = useEntities({ kind, book, q: q || undefined, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page names-page">
      <h1>People and places</h1>
      <p className="lede">
        Every name in the text. Whether a name is a person or a place is guessed from its contexts (directional ־ה, "city of",
        "son of", "and X said"); tribes and peoples count as people. Two names are linked when they share verses more often
        than their frequencies predict.
      </p>
      <div className="toolbar">
        <Segmented
          label="Kind"
          value={kind ?? 'all'}
          onChange={(k) => set({ kind: k === 'all' ? null : k })}
          options={[{ value: 'all', label: 'All' }, ...KINDS.map((k) => ({ value: k, label: KIND_LABELS[k] }))]}
        />
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
        <form
          className="control"
          role="search"
          onSubmit={(e) => {
            e.preventDefault()
            set({ q: draft.trim() || null })
          }}
        >
          <input
            type="search"
            dir="rtl"
            lang="he"
            aria-label="Find a name"
            placeholder="שם…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </form>
      </div>

      <div className="names-grid">
        <section aria-label="Names">
          {res.isPending ? (
            <Loading />
          ) : res.error ? (
            <ErrorBox error={res.error} />
          ) : res.data.items.length === 0 ? (
            <p className="status">No names match.</p>
          ) : (
            <>
              <p className="muted small">
                {res.data.total.toLocaleString()} names{book !== undefined ? ' in this book' : ''} · page {page} of {pages}
              </p>
              <ul className={`name-list ${res.isPlaceholderData ? 'stale' : ''}`}>
                {res.data.items.map((e) => (
                  <li key={e.lemma}>
                    <button
                      type="button"
                      className={`name-chip kind-${e.kind} ${selected === e.lemma ? 'on' : ''}`}
                      aria-pressed={selected === e.lemma}
                      onClick={() => update({ e: selected === e.lemma ? null : e.lemma }, false)}
                    >
                      <span dir="rtl" lang="he" className="he">
                        {e.he}
                      </span>
                      <span className="muted small">{e.n_here ?? e.n_mentions}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
            </>
          )}
        </section>
        {selected && <EntityPanel lemma={selected} books={books.data ?? []} onPick={(l) => update({ e: l }, false)} />}
      </div>
    </div>
  )
}

function EntityPanel({ lemma, books, onPick }: { lemma: string; books: Book[]; onPick: (lemma: string) => void }) {
  const res = useEntity(lemma)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { entity: e, by_book, partners } = res.data
  const counts = new Map(by_book.map((b) => [b.book_id, b.n_verses]))
  const max = Math.max(1, ...by_book.map((b) => b.n_verses))
  return (
    <section className="entity-panel" aria-label="Name details">
      <h2>
        <span dir="rtl" lang="he" className="he">
          {e.he}
        </span>{' '}
        <span className={`type-tag kind-${e.kind}`}>{KIND_LABELS[e.kind]}</span>
      </h2>
      <p className="muted small">
        {e.n_mentions} mentions in {e.n_verses} verses · first <Link to={unitLink(`v:${e.first_vid}`)}>{res.data.first_label}</Link>
        , last <Link to={unitLink(`v:${e.last_vid}`)}>{res.data.last_label}</Link> ·{' '}
        <Link to={lemmaLink(e.lemma)}>all verses</Link>
      </p>
      <h3>Where</h3>
      <ol className="book-strip" aria-label="Verses per book">
        {books.map((b) => {
          const n = counts.get(b.book_id) ?? 0
          return (
            <li key={b.book_id} title={`${b.name}: ${n} verses`}>
              <span className="strip-bar" style={{ height: `${(n / max) * 100}%`, opacity: n ? 1 : 0 }} />
            </li>
          )
        })}
      </ol>
      <p className="muted small strip-axis">
        <span>Genesis</span>
        <span>Chronicles</span>
      </p>
      {partners.length > 0 && (
        <>
          <h3>Appears with</h3>
          <EgoNetwork data={res.data} onPick={onPick} />
          <ul className="partner-list">
            {partners.map((p) => (
              <li key={p.lemma}>
                <button type="button" className="linkish" onClick={() => onPick(p.lemma)}>
                  <span dir="rtl" lang="he" className="he">
                    {p.he}
                  </span>
                </button>{' '}
                <span className="muted small">
                  {p.n_verses} verses together ({p.expected < 0.1 ? '<0.1' : p.expected.toFixed(1)} by chance)
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

/** The name in the centre, its partners on a circle (by strength), lines between linked partners. */
function EgoNetwork({ data, onPick }: { data: EntityDetail; onPick: (lemma: string) => void }) {
  const size = 320
  const c = size / 2
  const r = size / 2 - 42
  const ps = data.partners
  const maxG = Math.max(...ps.map((p) => p.g2), 1)
  const pos = new Map(
    ps.map((p, i) => {
      const a = (2 * Math.PI * i) / ps.length - Math.PI / 2
      return [p.lemma, { x: c + r * Math.cos(a), y: c + r * Math.sin(a) }]
    }),
  )
  return (
    <svg className="ego" viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Names appearing with ${data.entity.he}`}>
      {data.links.map((l) => {
        const a = pos.get(l.a)
        const b = pos.get(l.b)
        return a && b ? <line key={`${l.a}-${l.b}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="ego-side" /> : null
      })}
      {ps.map((p) => {
        const q = pos.get(p.lemma)!
        return <line key={p.lemma} x1={c} y1={c} x2={q.x} y2={q.y} className="ego-spoke" strokeWidth={1 + 3 * (p.g2 / maxG)} />
      })}
      {ps.map((p) => {
        const q = pos.get(p.lemma)!
        return (
          <g key={p.lemma} className={`ego-node kind-${p.kind}`} onClick={() => onPick(p.lemma)}>
            <circle cx={q.x} cy={q.y} r={5} />
            <text x={q.x} y={q.y - 9} textAnchor="middle" direction="rtl">
              {p.he}
            </text>
          </g>
        )
      })}
      <circle cx={c} cy={c} r={8} className={`ego-centre kind-${data.entity.kind}`} />
      <text x={c} y={c + 24} textAnchor="middle" className="ego-centre-label" direction="rtl">
        {data.entity.he}
      </text>
    </svg>
  )
}
