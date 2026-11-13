import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { useT } from '../context/localeContext'
import { useOnline } from '../lib/pwa'
import { dismissToast, TOAST_MS, type Toast, useToasts } from '../lib/toast'
import '../styles/components/Toaster.css'

/**
 * The page's one live region for what a save did (M177): "Saved", "Removed" with an Undo, and
 * failures. A note goes after a few seconds, longer when it offers an action, and waits while the
 * pointer or the focus is on it; a failure stays until it is closed. Drawn once, by `Layout`.
 */
export function Toaster() {
  const m = useT()
  const toasts = useToasts()
  // the timers wait while the viewer is at the notes
  const [held, setHeld] = useState(false)
  return (
    <section
      className="toaster"
      aria-label={m.toast.region}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
    >
      {/* always there, so that a note put into it is read out */}
      <div className="toaster-list" role="status" aria-live="polite">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} held={held} />
        ))}
      </div>
    </section>
  )
}

function ToastItem({ toast, held }: { toast: Toast; held: boolean }) {
  const m = useT()
  const online = useOnline()
  const failed = toast.kind === 'error'
  const ms = failed ? undefined : toast.action ? TOAST_MS.action : TOAST_MS.plain
  useEffect(() => {
    if (ms === undefined || held) return
    const timer = window.setTimeout(() => dismissToast(toast.id), ms)
    return () => window.clearTimeout(timer)
  }, [toast.id, ms, held])
  return (
    <div
      className={failed ? 'toast error' : 'toast'}
      role={failed ? 'alert' : undefined}
      // Escape closes the note the focus is in
      onKeyDown={(e) => {
        if (e.key === 'Escape') dismissToast(toast.id)
      }}
    >
      <span className="toast-text">
        {toast.text ?? (
          // the server's answer is in English: kept in its own order inside a right-to-left line
          <>
            {m.toast.failed} <bdi>{detail(toast.error, online ? undefined : m.toast.offline)}</bdi>
          </>
        )}
      </span>
      {toast.action && (
        <button
          type="button"
          className="toast-action"
          onClick={() => {
            dismissToast(toast.id)
            toast.action!.run()
          }}
        >
          {toast.action.label}
        </button>
      )}
      <button type="button" className="toast-close" aria-label={m.toast.dismiss} title={m.toast.dismiss} onClick={() => dismissToast(toast.id)}>
        <span aria-hidden="true">×</span>
      </button>
    </div>
  )
}

/** What went wrong, in a few words: the server's answer, or that there is no connection. */
function detail(error: unknown, offline: string | undefined): string {
  if (error instanceof ApiError) return `${error.status}: ${error.detail}`
  if (offline) return offline
  return error instanceof Error ? error.message : String(error)
}
