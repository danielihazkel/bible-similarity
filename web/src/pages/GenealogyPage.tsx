import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useGenealogyPerson, useGenealogySkeleton, usePersonLookup } from '../api/hooks'
import type { FamilyLink, PersonMatch, ProofVerse } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import type { Messages } from '../i18n'
import {
  below,
  type FamilyIndex,
  HEADER_H,
  indexTree,
  layoutTree,
  NODE_H,
  NODE_W,
  opening,
  pathTo,
  shownAt,
  type TreeLayout,
} from '../lib/familyTree'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { usePanZoom } from '../lib/panZoom'
import { personAbout } from '../lib/people'
import { useQueryParams } from '../lib/urlState'

const OPEN_GENERATIONS = 3 // the tree opens with Adam's first generations expanded
const K_MIN = 0.2 // zoom limits
const K_MAX = 2
const ZOOM = 1.4 // a step of the + / − buttons and keys
const KEY_STEP = 80 // CSS pixels an arrow key moves the tree
const MARGIN = 160 // CSS pixels beyond the view still drawn
const MEMBERS_SHOWN = 40 // people attached to a node listed before "show all"
const SPOUSES_SHOWN = 2 // spouses written in a node

type T = Messages['gt']
type Named = { text: string; he: boolean }
type Namer = (id: number) => Named

/** A person's name as the tree writes it: the Hebrew name; for the unnamed, what they are to the
 * one they are drawn under or beside ("בת לוט"); for the "unattached" groups, the book. */
function namer(ix: FamilyIndex, t: T, books: Map<number, string>): Namer {
  return (id) => {
    const n = ix.byId.get(id)
    const p = n ?? ix.spouse.get(id)
    if (!p) return { text: '', he: false }
    if (p.he) return { text: p.he, he: true }
    if (n?.kind === 'virtual') return { text: n.book_id === null ? t.unattached : (books.get(n.book_id) ?? String(n.book_id)), he: false }
    const of = n && n.parent !== null && n.role !== 'unstated' ? ix.byId.get(n.parent) : undefined
    if (of?.he) return { text: n!.sex === 'f' ? t.daughterOf(of.he) : n!.sex === 'm' ? t.sonOf(of.he) : t.childOf(of.he), he: false }
    const host = ix.host.get(id)
    const h = host === undefined ? '' : (ix.byId.get(host)?.he ?? '')
    if (h) return { text: p.sex === 'm' ? t.husbandOf(h) : t.wifeOf(h), he: false }
    return { text: t.unnamed(p.sex), he: false }
  }
}

function Name({ n }: { n: Named }) {
  return n.he ? (
    <span lang="he" dir="rtl" className="he">
      {n.text}
    </span>
  ) : (
    <bdi>{n.text}</bdi>
  )
}

/** Overview → Family tree (§16.63): everyone the text names, from Adam down, collapsible at any
 * node; a person (`?p=`) opens the line down to them and a panel with their family and the verses
 * that state each link. */
export function GenealogyPage() {
  const { m, locale } = useLocale()
  const t = m.gt
  const [params, update] = useQueryParams()
  const pv = params.get('p')
  const selected = pv && Number.isFinite(Number(pv)) ? Number(pv) : undefined
  const sk = useGenealogySkeleton()
  const books = useBooks()
  const ix = useMemo(() => (sk.data ? indexTree(sk.data) : undefined), [sk.data])
  const bookNames = useMemo(() => new Map((books.data ?? []).map((b) => [b.book_id, bookName(b, locale)])), [books.data, locale])
  const name = useMemo(() => (ix ? namer(ix, t, bookNames) : undefined), [ix, t, bookNames])
  const [expanded, setExpanded] = useState<Set<number>>()
  const [anchor, setAnchor] = useState<number>() // the node kept in place when the layout changes
  const [centre, setCentre] = useState<{ id: number; seq: number }>()
  const [opened, setOpened] = useState<number>() // the selected person whose line is open
  const [quiet, setQuiet] = useState<number>() // chosen in the tree: already in view
  if (ix && !expanded) setExpanded(opening(ix, OPEN_GENERATIONS))
  if (ix && expanded && selected !== undefined && opened !== selected) {
    setOpened(selected)
    const closed = pathTo(ix, selected)
      .slice(0, -1)
      .filter((id) => !expanded.has(id))
    if (closed.length) setExpanded(new Set([...expanded, ...closed]))
    if (quiet !== selected) setCentre({ id: selected, seq: (centre?.seq ?? 0) + 1 })
  }
  const layout = useMemo(() => (ix && expanded && sk.data ? layoutTree(ix, expanded, sk.data.cross, locale === 'he') : undefined), [ix, expanded, sk.data, locale])

  const show = (id: number) => setCentre({ id, seq: (centre?.seq ?? 0) + 1 })
  const pick = (id: number) => {
    setQuiet(undefined)
    if (id === selected) show(id)
    else update({ p: String(id) }, false)
  }
  const choose = (id: number) => {
    setQuiet(id)
    update({ p: String(id) }, false)
  }
  const toggle = (id: number) => {
    setAnchor(id)
    setExpanded((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const openAll = (id: number, open: boolean) => {
    if (!ix) return
    const at = shownAt(ix, id)
    if (at === undefined) return
    setAnchor(at)
    setExpanded((s) => {
      const next = new Set(s)
      for (const x of [at, ...below(ix, at)]) {
        if (open) next.add(x)
        else next.delete(x)
      }
      return next
    })
  }
  const meta = sk.data?.meta

  return (
    <div className="page genealogy-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {sk.isPending ? (
        <Loading />
      ) : sk.error ? (
        <ErrorBox error={sk.error} />
      ) : !sk.data.nodes.length || !ix || !name || !layout ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <p className="muted small">{t.summary(meta?.persons ?? 0, meta?.parent_links ?? 0, meta?.proved ?? 0, meta?.reviewed_links ?? 0)}</p>
          <PersonSearch t={t} onPick={pick} />
          <div className="gt-layout">
            <div className="gt-main">
              <TreeView
                ix={ix}
                layout={layout}
                name={name}
                t={t}
                num={m.num}
                selected={selected}
                anchor={anchor}
                centre={centre}
                onSelect={choose}
                onToggle={toggle}
              />
              <Legend t={t} />
            </div>
            <aside className={`gt-side${selected !== undefined ? ' open' : ''}`} onKeyDown={(e) => e.key === 'Escape' && update({ p: null })}>
              {selected !== undefined ? (
                <GenealogyPanel
                  personId={selected}
                  ix={ix}
                  name={name}
                  t={t}
                  onPick={pick}
                  onShow={show}
                  onOpenAll={openAll}
                  onClose={() => update({ p: null })}
                />
              ) : (
                <p className="muted">{t.idle}</p>
              )}
            </aside>
          </div>
        </>
      )}
    </div>
  )
}

interface View {
  x: number
  y: number
  k: number
}

interface TreeProps {
  ix: FamilyIndex
  layout: TreeLayout
  name: Namer
  t: T
  num: (n: number) => string
  selected?: number
  anchor?: number
  centre?: { id: number; seq: number }
  onSelect: (id: number) => void
  onToggle: (id: number) => void
}

/** The tree: an SVG layer of edges under HTML nodes and headers, panned and zoomed as one; only
 * what is in view (and a margin) is drawn. */
function TreeView({ ix, layout, name, t, num, selected, anchor, centre, onSelect, onToggle }: TreeProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 800, h: 560 })
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([e]) => e.contentRect.width && setSize({ w: e.contentRect.width, h: e.contentRect.height }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const top = layout.nodes.find((n) => n.node.placement === 'root') ?? layout.nodes[0]
  const home: View = { k: 1, x: size.w / 2 - (top?.x ?? 0), y: 16 }
  const [stored, setView] = useState<View>()
  const view = stored ?? home
  const at = (v: View, x: number, y: number) => setView({ k: v.k, x: size.w / 2 - x * v.k, y: size.h / 3 - y * v.k })

  // a new layout keeps the node just opened or closed where it was on screen
  const [prev, setPrev] = useState(layout)
  if (prev !== layout) {
    setPrev(layout)
    const a = anchor === undefined ? undefined : prev.at.get(anchor)
    const b = anchor === undefined ? undefined : layout.at.get(anchor)
    if (a && b) setView({ ...view, x: view.x - (b.x - a.x) * view.k, y: view.y - (b.y - a.y) * view.k })
  }
  // a person chosen outside the tree (search, the panel, the address) is brought into view
  const [done, setDone] = useState(0)
  if (centre && centre.seq !== done) {
    const id = shownAt(ix, centre.id)
    const c = id === undefined ? undefined : layout.at.get(id)
    if (c || id === undefined) setDone(centre.seq)
    if (c) at(view, c.x, c.y + NODE_H / 2)
  }

  const zoomAt = (v: View, f: number, px: number, py: number): View => {
    const k = Math.min(K_MAX, Math.max(K_MIN, v.k * f))
    const r = k / v.k
    return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r }
  }
  const { handlers, dragged } = usePanZoom(ref, {
    onPan: (dx, dy) => setView((v) => ({ ...(v ?? home), x: (v ?? home).x + dx, y: (v ?? home).y + dy })),
    onZoom: (f, px, py) => setView((v) => zoomAt(v ?? home, f, px, py)),
  })
  const zoom = (f: number) => setView((v) => zoomAt(v ?? home, f, size.w / 2, size.h / 2))
  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return
    const step = { ArrowLeft: [KEY_STEP, 0], ArrowRight: [-KEY_STEP, 0], ArrowUp: [0, KEY_STEP], ArrowDown: [0, -KEY_STEP] }[e.key]
    if (step) {
      e.preventDefault()
      setView((v) => ({ ...(v ?? home), x: (v ?? home).x + step[0], y: (v ?? home).y + step[1] }))
    } else if (e.key === '+' || e.key === '=') zoom(ZOOM)
    else if (e.key === '-') zoom(1 / ZOOM)
    else if (e.key === 'Home') setView(undefined)
  }

  // what is in view, in layout units
  const x0 = (-view.x - MARGIN) / view.k
  const x1 = (size.w - view.x + MARGIN) / view.k
  const y0 = (-view.y - MARGIN) / view.k
  const y1 = (size.h - view.y + MARGIN) / view.k
  const nodes = layout.nodes.filter((n) => n.x + NODE_W / 2 >= x0 && n.x - NODE_W / 2 <= x1 && n.y + NODE_H >= y0 && n.y <= y1)
  const headers = layout.headers.filter((h) => h.x + NODE_W / 2 >= x0 && h.x - NODE_W / 2 <= x1 && h.y >= y0 && h.y <= y1)
  const edges = layout.edges.filter((e) => e.box[2] >= x0 && e.box[0] <= x1 && e.box[3] >= y0 && e.box[1] <= y1)
  const click = (f: () => void) => () => {
    if (!dragged()) f()
  }

  return (
    <div className="gt-tree">
      {/* left to right inside in either language: the layout mirrors itself for Hebrew */}
      <div ref={ref} className="gt-viewport" dir="ltr" tabIndex={0} role="group" aria-label={t.treeLabel} onKeyDown={onKey} {...handlers}>
        <div className="gt-canvas" style={{ width: layout.width, height: layout.height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}>
          <svg className="gt-edges" width={layout.width} height={layout.height} aria-hidden="true">
            {edges.map((e) => (
              <path key={e.key} className={e.cls} d={e.d} />
            ))}
          </svg>
          {headers.map((h) => {
            const label = typeof h.group === 'number' ? t.byMother(name(h.group).text) : h.group === 'none' ? t.motherUnnamed : t.attached(h.n)
            return (
              <div key={h.key} className={`gt-header ${typeof h.group === 'number' ? 'mother' : h.group}`} style={{ left: h.x - NODE_W / 2, top: h.y - HEADER_H / 2, width: NODE_W, height: HEADER_H }} title={label}>
                {typeof h.group === 'number' ? (
                  <button type="button" className="linkish" onClick={click(() => onSelect(h.group as number))} dir="auto">
                    {label}
                  </button>
                ) : (
                  <span dir="auto">{label}</span>
                )}
              </div>
            )
          })}
          {nodes.map(({ node: n, x, y, expanded, hidden }) => {
            const kids = ix.kids.get(n.person_id)?.length ?? 0
            const cls = [
              'gt-node',
              `kind-${n.kind}`,
              n.kind === 'virtual' ? '' : n.reviewed ? 'reviewed' : 'unreviewed',
              n.conflict ? 'conflict' : '',
              n.person_id === selected || (selected !== undefined && ix.host.get(selected) === n.person_id) ? 'selected' : '',
            ]
            return (
              <div key={n.person_id} className={cls.filter(Boolean).join(' ')} style={{ left: x - NODE_W / 2, top: y, width: NODE_W, height: NODE_H }}>
                <button type="button" className="gt-name" aria-current={n.person_id === selected ? 'true' : undefined} onClick={click(() => onSelect(n.person_id))}>
                  {n.conflict && (
                    <span className="gt-warn" aria-hidden="true">
                      ⚠{' '}
                    </span>
                  )}
                  <Name n={name(n.person_id)} />
                  {n.conflict && <span className="sr-only">, {t.srConflict}</span>}
                  {n.kind !== 'virtual' && !n.reviewed && <span className="sr-only">, {t.srUnreviewed}</span>}
                </button>
                {n.spouses.length > 0 && (
                  <span className="gt-spouses">
                    <span aria-hidden="true">⚭ </span>
                    {n.spouses.slice(0, SPOUSES_SHOWN).map((s, i) => (
                      <span key={s}>
                        {i > 0 && ', '}
                        <button type="button" className="linkish" onClick={click(() => onSelect(s))}>
                          <Name n={name(s)} />
                        </button>
                      </span>
                    ))}
                    {n.spouses.length > SPOUSES_SHOWN && ` +${num(n.spouses.length - SPOUSES_SHOWN)}`}
                  </span>
                )}
                {kids > 0 && (
                  <button type="button" className="gt-toggle" aria-expanded={expanded} aria-label={expanded ? t.hide : t.show(hidden)} onClick={click(() => onToggle(n.person_id))}>
                    {expanded ? '−' : `+${num(hidden)}`}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <div className="geo-zoom gt-zoom" role="group" aria-label={t.zoom}>
        <button type="button" onClick={() => zoom(ZOOM)} aria-label={t.zoomIn}>
          +
        </button>
        <button type="button" onClick={() => zoom(1 / ZOOM)} aria-label={t.zoomOut}>
          −
        </button>
        <button type="button" onClick={() => setView(undefined)} aria-label={t.home} title={t.home}>
          ⌂
        </button>
      </div>
    </div>
  )
}

function Legend({ t }: { t: T }) {
  const line = (cls: string) => (
    <svg className="gt-key-line" width="30" height="10" aria-hidden="true">
      <path className={cls} d="M1 5H29" />
    </svg>
  )
  return (
    <ul className="gt-legend small" aria-label={t.legend}>
      <li>
        <span className="gt-key-node conflict" aria-hidden="true">
          ⚠
        </span>{' '}
        {t.keys.conflict}
      </li>
      <li>
        {line('gt-edge desc')} {t.keys.desc}
      </li>
      <li>
        {line('gt-edge unstated')} {t.keys.unstated}
      </li>
      <li>
        <span className="gt-key-node unreviewed" aria-hidden="true" /> {t.keys.unreviewed}
      </li>
      <li>
        {line('gt-cross')} {t.keys.cross}
      </li>
      <li>
        <span aria-hidden="true">⚭</span> {t.keys.spouse}
      </li>
      <li>
        <span className="gt-key-node kind-group" aria-hidden="true" /> {t.keys.group}
      </li>
      <li>
        <span className="gt-key-header" aria-hidden="true" /> {t.keys.header}
      </li>
    </ul>
  )
}

function PersonSearch({ t, onPick }: { t: T; onPick: (id: number) => void }) {
  const { locale } = useLocale()
  const [q, setQ] = useState('')
  const dq = useDeferredValue(q.trim())
  const res = usePersonLookup(dq)
  const items = q.trim() && res.data?.query === dq ? res.data.items : undefined
  const choose = (x: PersonMatch) => {
    setQ('')
    onPick(x.person_id)
  }
  return (
    <div className="gt-search">
      <label className="control">
        <span>{t.search}</span>
        <input
          type="search"
          value={q}
          placeholder={t.searchHint}
          lang="he"
          dir="rtl"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && items?.length) choose(items[0])
            else if (e.key === 'Escape') setQ('')
          }}
        />
      </label>
      {items &&
        (items.length ? (
          <ul className="gt-matches" aria-label={t.matches}>
            {items.map((x) => (
              <li key={x.person_id}>
                <button type="button" className="linkish" onClick={() => choose(x)}>
                  <span lang="he" dir="rtl" className="he">
                    {x.he}
                  </span>
                </button>{' '}
                <span className="muted small" dir="auto">
                  {personAbout(x, t, locale)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted small">{t.noMatch(q.trim())}</p>
        ))}
    </div>
  )
}

interface PanelProps {
  personId: number
  ix: FamilyIndex
  name: Namer
  t: T
  onPick: (id: number) => void
  onShow: (id: number) => void
  onOpenAll: (id: number, open: boolean) => void
  onClose: () => void
}

/** One person: where they stand, their family with the verses of each link, the readings where
 * the text disagrees. */
function GenealogyPanel({ personId, ix, name, t, onPick, onShow, onOpenAll, onClose }: PanelProps) {
  const { locale } = useLocale()
  const res = useGenealogyPerson(personId)
  const [allMembers, setAllMembers] = useState(false)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const p = d.person
  const host = ix.host.get(p.person_id)
  const tribe = d.attached && p.placement === 'tribe' ? name(d.attached.person.person_id) : undefined
  const below_ = ix.kids.get(p.person_id)?.length ?? 0
  const first = locale === 'he' ? d.first_label_he : d.first_label
  const who = (id: number) => (
    <button type="button" className="linkish" onClick={() => onPick(id)}>
      <Name n={name(id)} />
    </button>
  )
  const links = (ls: FamilyLink[], compact = false, roles = true) => (
    <ul className="gt-links">
      {ls.map((l) => (
        <LinkItem key={l.link_id} l={l} t={t} who={who} compact={compact} role={roles} />
      ))}
    </ul>
  )
  const members = allMembers ? d.members : d.members.slice(0, MEMBERS_SHOWN)
  return (
    <section className="gt-panel" aria-label={t.panel}>
      <div className="word-head">
        <h2>
          <Name n={name(p.person_id)} /> {p.kind !== 'person' && <span className={`type-tag gt-kind-${p.kind}`}>{t.kinds[p.kind as keyof T['kinds']]}</span>}
        </h2>
        <button type="button" className="linkish" onClick={onClose}>
          {t.close}
        </button>
      </div>
      {p.kind !== 'virtual' && (
        <p className="muted small">
          {first && p.first_vid !== null && (
            <>
              {t.firstNamed} <Link to={unitLink(`v:${p.first_vid}`)}>{first}</Link> ·{' '}
            </>
          )}
          {t.verseCount(p.n_verses)} · {p.reviewed ? t.reviewed : t.notReviewed}
        </p>
      )}
      {tribe && <p className="small">{t.placedTribe(tribe.text)}</p>}
      {p.placement === 'unattached' && <p className="small">{t.placedUnattached}</p>}
      {p.placement === 'spouse' && host !== undefined && <p className="small">{t.placedSpouse(name(host).text)}</p>}
      <p className="gt-actions">
        <button type="button" onClick={() => onShow(p.person_id)}>
          {t.showInTree}
        </button>
        {below_ > 0 && (
          <>
            <button type="button" onClick={() => onOpenAll(p.person_id, true)}>
              {t.openAll}
            </button>
            <button type="button" onClick={() => onOpenAll(p.person_id, false)}>
              {t.closeAll}
            </button>
          </>
        )}
      </p>
      {d.conflicts.length > 0 && (
        <section className="gt-conflicts">
          <h3>
            <span className="gt-warn" aria-hidden="true">
              ⚠
            </span>{' '}
            {t.conflicts}
          </h3>
          {d.conflicts.map((c) => (
            <div key={c.conflict_id} className="gt-conflict">
              <p className="small">
                <strong>{t.conflictKinds[c.kind]}</strong>
                {(locale === 'he' ? c.note_he : c.note_en) && ` · ${locale === 'he' ? c.note_he : c.note_en}`}
              </p>
              <ul className="gt-links">
                {c.readings.map((l, i) => (
                  <LinkItem key={l.link_id} l={l} t={t} who={who} reading={i === 0 ? t.readingDrawn : t.readingOther} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
      {d.identities.length > 0 && (
        <section className="gt-identities">
          <h3>{t.identities}</h3>
          {d.identities.map((x) => {
            const note = locale === 'he' ? x.note_he : x.note_en
            return (
              <div key={x.identity_id} className="gt-identity">
                <p className="small">
                  {x.person ? (
                    <>
                      {t.maybeSame} {who(x.person.person_id)}
                    </>
                  ) : (
                    t.mergedFrom(x.n_keys)
                  )}
                  {note && ` · ${note}`}
                </p>
                <ol className="gt-proofs">
                  {x.proofs.map((v) => (
                    <Proof key={v.verse.verse_id} v={v} t={t} />
                  ))}
                </ol>
              </div>
            )
          })}
        </section>
      )}
      {d.parents.length > 0 && (
        <>
          <h3>{t.parents}</h3>
          {links(d.parents)}
        </>
      )}
      {d.spouses.length > 0 && (
        <>
          <h3>{t.spouses}</h3>
          {links(d.spouses, false, false)}
        </>
      )}
      {d.children.length > 0 && (
        <>
          <h3>{t.children}</h3>
          {d.children.map((g) => (
            <div key={g.other?.person_id ?? 0} className="gt-child-group">
              <h4 className="small">
                {g.other ? (
                  <>
                    {g.other.sex === 'f' ? t.childrenBy : t.childrenOf} {who(g.other.person_id)}
                  </>
                ) : (
                  t.childrenUnnamed
                )}
              </h4>
              {links(g.children, true, false)}
            </div>
          ))}
        </>
      )}
      {d.siblings.length > 0 && (
        <>
          <h3>{t.siblings}</h3>
          <p className="gt-names">
            {d.siblings.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
        </>
      )}
      {d.members.length > 0 && (
        <>
          <h3>{t.members(d.members.length)}</h3>
          <p className="muted small">{t.membersLede}</p>
          <p className="gt-names">
            {members.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
          {d.members.length > MEMBERS_SHOWN && (
            <button type="button" className="linkish" onClick={() => setAllMembers((x) => !x)}>
              {allMembers ? t.showFewer : t.showAll(d.members.length)}
            </button>
          )}
        </>
      )}
    </section>
  )
}

interface LinkProps {
  l: FamilyLink
  t: T
  who: (id: number) => React.ReactNode
  compact?: boolean // the verses folded (a child's)
  role?: boolean // say father / mother
  reading?: string // a conflict's reading: which
}

function LinkItem({ l, t, who, compact = false, role = true, reading }: LinkProps) {
  const tags = [
    role && !reading ? t.roles[l.role] : undefined,
    reading,
    l.kind === 'descendant' ? t.descendant : undefined,
    l.kind === 'adopted' ? t.adopted : undefined,
    t.status[l.status],
    l.marker && t.markers[l.marker] ? t.markers[l.marker] : undefined,
    l.doubt ? t.doubt : undefined,
    (l.role === 'father' || l.role === 'mother') && !reading ? (l.drawn ? t.drawn : t.notDrawn) : undefined,
  ].filter(Boolean)
  const proved = l.proofs.filter((v) => v.cue !== 'nearby')
  const hint = l.proofs.filter((v) => v.cue === 'nearby')
  const verses = (
    <>
      {!proved.length && l.role !== 'unstated' && <p className="muted small">{t.noProof}</p>}
      {hint.length > 0 && <p className="muted small">{t.nearbyHint}</p>}
      <ol className="gt-proofs">
        {l.proofs.map((v) => (
          <Proof key={v.verse.verse_id} v={v} t={t} />
        ))}
      </ol>
    </>
  )
  return (
    <li className={`gt-link${l.kind === 'descendant' ? ' desc' : ''}${l.status === 'tipnr' ? ' unreviewed' : ''}`}>
      <span className="gt-link-head">
        {who(l.person.person_id)}{' '}
        {tags.map((x) => (
          <span key={x} className="gt-tag small">
            {x}
          </span>
        ))}
      </span>
      {compact ? (
        <details>
          <summary className="small">{l.proofs.length ? t.verses(proved.length || l.proofs.length) : t.noProof}</summary>
          {verses}
        </details>
      ) : (
        verses
      )}
    </li>
  )
}

function Proof({ v, t }: { v: ProofVerse; t: T }) {
  const { locale } = useLocale()
  const hl: Highlight = new Map(v.tokens.map((i) => [i, 'focus']))
  return (
    <li className="hit gt-proof">
      <Link className="verse-ref" to={unitLink(`v:${v.verse.verse_id}`)}>
        {locale === 'he' ? v.verse.ref_he : v.verse.ref}
      </Link>{' '}
      {v.cue && (
        <span className="type-tag gt-cue" title={t.cueTitle}>
          {t.cues[v.cue]}
        </span>
      )}{' '}
      {v.source === 'curated' && <span className="muted small">{t.curated}</span>}
      <p className="hit-text">
        <HebrewText verse={v.verse} highlight={hl} />
      </p>
    </li>
  )
}
