import { Component, type ReactNode } from 'react'
import { isChunkLoadError } from '../lib/chunk'

const RELOADED_KEY = 'bsim:chunk-reload'
const RELOAD_GUARD_MS = 30_000

/** Whether the page was already reloaded for a stale chunk moments ago (avoids a reload loop). */
function reloadedRecently(now = Date.now()): boolean {
  try {
    const last = Number(sessionStorage.getItem(RELOADED_KEY) ?? 0)
    if (now - last < RELOAD_GUARD_MS) return true
    sessionStorage.setItem(RELOADED_KEY, String(now))
  } catch {
    return true // no storage, no loop guard: never reload automatically
  }
  return false
}

interface Props {
  children: ReactNode
  /** Reloads the page (injected in tests). */
  reload?: () => void
}

interface State {
  error?: unknown
}

/**
 * Catches render errors of a page so the header and navigation stay usable. A stale lazy chunk
 * reloads the page once (fetching the new build); anything else shows a message with a reload
 * button. Render it with `key={pathname}` so navigating elsewhere clears the error.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = {}

  static getDerivedStateFromError(error: unknown): State {
    return { error }
  }

  componentDidCatch(error: unknown) {
    if (isChunkLoadError(error) && !reloadedRecently()) this.reload()
  }

  reload = () => (this.props.reload ?? (() => window.location.reload()))()

  render() {
    const { error } = this.state
    if (error === undefined) return this.props.children
    const stale = isChunkLoadError(error)
    return (
      <div className="status error" role="alert">
        <p>
          {stale
            ? 'This page could not be loaded: the viewer has been updated since this tab was opened.'
            : `Something went wrong while showing this page${error instanceof Error ? `: ${error.message}` : ''}.`}
        </p>
        <button type="button" onClick={this.reload}>
          Reload
        </button>
      </div>
    )
  }
}
