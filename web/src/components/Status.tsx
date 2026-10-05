import { ApiError } from '../api/client'
import { useT } from '../context/localeContext'

export function Loading({ label }: { label?: string }) {
  const m = useT()
  return (
    <p className="status" role="status">
      {label ?? m.status.loading}
    </p>
  )
}

// API details (error.detail) come from the server in English: isolated so they keep their order
// inside a right-to-left sentence.
export function ErrorBox({ error }: { error: unknown }) {
  const m = useT()
  const msg =
    error instanceof ApiError ? (
      <>
        {error.status === 404 ? m.status.notFound : `${error.status}:`} <bdi>{error.detail}</bdi>
      </>
    ) : error instanceof Error ? (
      m.status.unreachable(error.message)
    ) : (
      String(error)
    )
  return (
    <p className="status error" role="alert">
      {msg}
    </p>
  )
}

/** A one-line note that an optional panel (names, phrases, …) could not be loaded. */
export function PanelError({ what, error }: { what: string; error: unknown }) {
  const m = useT()
  const detail = error instanceof ApiError ? `${error.status}: ${error.detail}` : m.status.apiUnreachable
  return (
    <p className="status error small" role="alert">
      {m.status.couldNotLoad(what)} (<bdi>{detail}</bdi>).
    </p>
  )
}
