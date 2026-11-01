import { useMemo, useRef, useState } from 'react'
import { useBooks, useGenealogySkeleton } from '../api/hooks'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { below, indexTree, layoutTree, opening, pathTo, shownAt } from '../lib/familyTree'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'
import { GenealogyPanel } from './genealogy/PersonPanel'
import { PersonSearch } from './genealogy/PersonSearch'
import { TreeView } from './genealogy/TreeView'
import { OPEN_GENERATIONS, namer } from './genealogy/shared'

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
  const panel = useRef<HTMLElement>(null)
  const stage = useRef<HTMLDivElement>(null)
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
  const line = useMemo(() => (ix && selected !== undefined ? new Set(pathTo(ix, selected)) : undefined), [ix, selected])

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
  const ready = !!(sk.data?.nodes.length && ix && name && layout)

  return (
    <div className="page genealogy-page">
      <div className="gt-head">
        <h1>{t.title}</h1>
        {ready && <p className="muted small">{t.summary(meta?.persons ?? 0, meta?.parent_links ?? 0, meta?.proved ?? 0, meta?.reviewed_links ?? 0)}</p>}
        <details className="gt-about">
          <summary className="small">{t.about}</summary>
          <p className="lede">{t.lede}</p>
        </details>
      </div>
      {sk.isPending ? (
        <Loading />
      ) : sk.error ? (
        <ErrorBox error={sk.error} />
      ) : !ready ? (
        <p className="status">{t.noData}</p>
      ) : (
        <div ref={stage} className="gt-stage">
          <TreeView
            ix={ix!}
            layout={layout!}
            name={name!}
            t={t}
            num={m.num}
            selected={selected}
            line={line}
            anchor={anchor}
            centre={centre}
            panel={panel}
            stage={stage}
            onSelect={choose}
            onToggle={toggle}
          />
          <PersonSearch t={t} onPick={pick} />
          {selected === undefined && <p className="gt-idle muted small">{t.idle}</p>}
          <aside ref={panel} className={`gt-side${selected !== undefined ? ' open' : ''}`} onKeyDown={(e) => e.key === 'Escape' && update({ p: null })}>
            {selected !== undefined && (
              <GenealogyPanel
                personId={selected}
                ix={ix!}
                name={name!}
                t={t}
                onPick={pick}
                onShow={show}
                onOpenAll={openAll}
                onClose={() => update({ p: null })}
              />
            )}
          </aside>
        </div>
      )}
    </div>
  )
}
