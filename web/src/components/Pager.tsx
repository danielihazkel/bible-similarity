import type { UseQueryResult } from '@tanstack/react-query'
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from 'react'
import { useT } from '../context/localeContext'
import type { Params } from '../api/client'
import { flattenItems } from '../lib/csv'
import { parsePage, useQueryParams } from '../lib/urlState'
import { ExportCsv } from './ExportCsv'
import { ErrorBox, Loading } from './Status'
import '../styles/components/Pager.css'

/** Previous / next, and a page number to jump to. */
export function Pager({ page, pages, onPage }: { page: number; pages: number; onPage: (p: number) => void }) {
  const m = useT()
  const [draft, setDraft] = useState(String(page))
  const [seen, setSeen] = useState(page)
  if (seen !== page) {
    setSeen(page)
    setDraft(String(page))
  }
  if (pages <= 1) return null
  const jump = (e: FormEvent) => {
    e.preventDefault()
    const p = Math.min(pages, Math.max(1, Math.round(Number(draft))))
    if (Number.isFinite(p) && p !== page) onPage(p)
    else setDraft(String(page))
  }
  return (
    <nav className="pager" aria-label={m.pager.label}>
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {m.pager.previous}
      </button>
      <form className="pager-jump" onSubmit={jump} noValidate>
        <label className="muted small">
          {m.pager.page}{' '}
          <input
            type="number"
            min={1}
            max={pages}
            value={draft}
            aria-current="page"
            aria-label={m.pager.pageOf(pages)}
            onChange={(e) => setDraft(e.target.value)}
          />{' '}
          {m.pager.of(pages)}
        </label>
        <button type="submit" className="linkish">
          {m.pager.go}
        </button>
      </form>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        {m.pager.next}
      </button>
    </nav>
  )
}

/**
 * The empty state of a list page: the list's own message, or — when the URL asks for a page past
 * the end of a non-empty list — a way back to its last page.
 */
export function EmptyList({ total, limit, pageParam = 'page', children }: { total: number; limit: number; pageParam?: string; children: ReactNode }) {
  const m = useT()
  const [params, update] = useQueryParams()
  const page = parsePage(params.get(pageParam))
  if (total > 0) {
    const last = Math.max(1, Math.ceil(total / limit))
    return (
      <p className="status">
        {m.pager.pastEnd(page, last)}{' '}
        <button type="button" className="linkish" onClick={() => update({ [pageParam]: last === 1 ? null : String(last) })}>
          {m.pager.lastPage}
        </button>
      </p>
    )
  }
  return <p className="status">{children}</p>
}

interface Page {
  items: unknown[]
  total: number
  limit: number
}

/**
 * A list page's states in one place: loading, an error, empty (or past its last page), and then a
 * summary line above the list, the list itself and the pager. The page is the URL's `page`; the
 * list is drawn by `children`, given `stale` (`'stale'` while the next page loads over this one)
 * for its class. `csv` names the list for its exports, at the end of the summary line: the page as
 * it is listed, and, when the result carries its request's parameters (`Listed`, `api/hooks.ts`),
 * every row from the server (`/api/export/{csv}.csv`). A page that writes its own columns puts an
 * `ExportCsv` in its `summary` instead.
 */
export function PagedList<T extends Page>({
  res,
  empty,
  summary,
  csv,
  pageParam = 'page',
  children,
}: {
  /** the parameter that holds the page, for a second list of a page (`vpage`, `cpage`) */
  pageParam?: string
  res: UseQueryResult<T>
  /** the list's name in the server's export table, and in the files' names */
  csv?: string
  /** what an empty list says */
  empty: ReactNode
  /** the line above the list (count and page, an export link …) */
  summary?: (data: T, page: number, pages: number) => ReactNode
  children: (data: T, stale: string) => ReactNode
}) {
  const [params, update] = useQueryParams()
  const page = parsePage(params.get(pageParam))
  // a list hook hands its request's parameters on with the result (`Listed`)
  const asked = (res as { params?: Params }).params
  const top = useRef<HTMLSpanElement>(null)
  // a new page of the list is read from its top: the pager is at its foot. Scrolled once the new
  // history entry is on screen (an effect), so the entry left keeps its own place for Back
  const turned = useRef(false)
  const toPage = (p: number) => {
    turned.current = true
    update({ [pageParam]: p === 1 ? null : String(p) }, false)
  }
  useEffect(() => {
    if (!turned.current) return
    turned.current = false
    const el = top.current
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: 'start' })
  }, [page])
  if (res.isPending) return <Loading />
  if (res.isError) return <ErrorBox error={res.error} />
  const data = res.data
  if (data.items.length === 0) {
    return (
      <EmptyList total={data.total} limit={data.limit} pageParam={pageParam}>
        {empty}
      </EmptyList>
    )
  }
  const pages = Math.max(1, Math.ceil(data.total / data.limit))
  return (
    <>
      <span ref={top} className="list-top" />
      {(summary || csv) && (
        <p className="muted small">
          {summary && (csv ? <span>{summary(data, page, pages)}</span> : summary(data, page, pages))}
          {summary && csv && ' · '}
          {csv && <ExportCsv filename={`${csv}-p${page}.csv`} rows={() => flattenItems(data.items)} all={asked ? { list: csv, params: asked } : undefined} />}
        </p>
      )}
      {children(data, res.isPlaceholderData ? 'stale' : '')}
      <Pager page={page} pages={pages} onPage={toPage} />
    </>
  )
}
