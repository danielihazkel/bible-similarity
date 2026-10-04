import { ApiError } from '../api/client'

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <p className="status" role="status">
      {label}
    </p>
  )
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg =
    error instanceof ApiError
      ? error.status === 404
        ? `Not found: ${error.detail}`
        : `${error.status}: ${error.detail}`
      : error instanceof Error
        ? `Could not reach the API (${error.message}). Is \`bsim serve\` running?`
        : String(error)
  return (
    <p className="status error" role="alert">
      {msg}
    </p>
  )
}
