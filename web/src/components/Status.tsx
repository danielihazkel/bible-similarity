import type { ReactNode } from 'react'
import { ApiError, isStageMissing } from '../api/client'
import { useT } from '../context/localeContext'
import { useOnline } from '../lib/pwa'
import '../styles/components/Status.css'

const PLACEHOLDER_ROWS = 6

/** Loading. `list`: quiet rows in a list's place (the words are still there for a screen reader). */
export function Loading({ label, list = false }: { label?: string; list?: boolean }) {
  const m = useT()
  if (list) {
    return (
      <div className="list-placeholder" role="status">
        <span className="sr-only">{label ?? m.status.loading}</span>
        {Array.from({ length: PLACEHOLDER_ROWS }, (_, i) => (
          <span key={i} aria-hidden="true" />
        ))}
      </div>
    )
  }
  return (
    <p className="status" role="status">
      {label ?? m.status.loading}
    </p>
  )
}

/**
 * A page before its data has come (M176): its heading and lede at once, then the list's
 * placeholder or the error. A page whose heading is its data (a passage, a lemma) gives no
 * `title` and gets the heading's place held.
 */
export function PageWait({ className = 'page', title, lede, error }: { className?: string; title?: ReactNode; lede?: ReactNode; error?: unknown }) {
  return (
    <div className={className}>
      {title !== undefined ? <h1>{title}</h1> : !error && <div className="heading-placeholder" aria-hidden="true" />}
      {lede !== undefined && <p className="lede">{lede}</p>}
      {error ? <ErrorBox error={error} /> : <Loading list />}
    </div>
  )
}

// API details (error.detail) come from the server in English: isolated so they keep their order
// inside a right-to-left sentence.
export function ErrorBox({ error }: { error: unknown }) {
  const m = useT()
  const online = useOnline()
  if (isStageMissing(error)) return <NotComputed stage={error.stage} />
  const msg =
    error instanceof ApiError ? (
      <>
        {error.status === 404 ? m.status.notFound : `${error.status}:`} <bdi>{error.detail}</bdi>
      </>
    ) : error instanceof Error ? (
      online ? m.status.unreachable(error.message) : m.offline.notSaved
    ) : (
      String(error)
    )
  return (
    <p className="status error" role="alert">
      {msg}
    </p>
  )
}

/** The analysis was not computed in this build: not an error, so no alert. */
export function NotComputed({ stage, children }: { stage?: string; children?: ReactNode }) {
  const m = useT()
  return <p className="status not-computed">{children ?? m.status.notComputed(stage)}</p>
}

/** A one-line note that an optional panel (names, phrases, …) could not be loaded. */
export function PanelError({ what, error }: { what: string; error: unknown }) {
  const m = useT()
  const online = useOnline()
  if (isStageMissing(error)) {
    return <p className="status small not-computed">{m.status.notComputed(error.stage)}</p>
  }
  const detail =
    error instanceof ApiError
      ? `${error.status}: ${error.detail}`
      : online
        ? m.status.apiUnreachable
        : m.offline.notSavedShort
  return (
    <p className="status error small" role="alert">
      {m.status.couldNotLoad(what)} (<bdi>{detail}</bdi>).
    </p>
  )
}
