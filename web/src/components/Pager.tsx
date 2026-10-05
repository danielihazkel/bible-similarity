import { type FormEvent, type ReactNode, useState } from 'react'
import { useT } from '../context/localeContext'
import { parsePage, useQueryParams } from '../lib/urlState'

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
export function EmptyList({ total, limit, children }: { total: number; limit: number; children: ReactNode }) {
  const m = useT()
  const [params, update] = useQueryParams()
  const page = parsePage(params.get('page'))
  if (total > 0) {
    const last = Math.max(1, Math.ceil(total / limit))
    return (
      <p className="status">
        {m.pager.pastEnd(page, last)}{' '}
        <button type="button" className="linkish" onClick={() => update({ page: last === 1 ? null : String(last) })}>
          {m.pager.lastPage}
        </button>
      </p>
    )
  }
  return <p className="status">{children}</p>
}
