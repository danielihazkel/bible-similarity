import { useSyncExternalStore } from 'react'

// The short notes of a save (M177): "Saved", "Removed · Undo", "Could not save". A small store
// outside React, so that the hook of a save (api/hooks.ts) can say that it failed without the
// component that asked for it, which may be gone by then; `components/Toaster.tsx` draws them in
// the page's one live region.

export interface ToastAction {
  label: string
  run: () => void
}

export interface Toast {
  id: number
  kind: 'ok' | 'error'
  /** What it says; a failure may give the error instead, and the toaster words it. */
  text?: string
  error?: unknown
  /** One button beside the text (Undo). */
  action?: ToastAction
  /** A later note of the same key takes this one's place. */
  key?: string
}

/** How long a note stays (ms): a plain one, one with an action. A failure stays until closed. */
export const TOAST_MS = { plain: 3500, action: 8000 }
const MOST = 3

let toasts: Toast[] = []
let nextId = 1
const listeners = new Set<() => void>()

function set(next: Toast[]) {
  toasts = next
  for (const l of listeners) l()
}

function add(toast: Omit<Toast, 'id'>): number {
  const id = nextId++
  const kept = toasts.filter((t) => !(toast.key && t.key === toast.key))
  // the oldest go when there are more than a few
  set([...kept, { ...toast, id }].slice(-MOST))
  return id
}

/** Say that something was saved or removed, with an action to take it back. */
export function showToast(text: string, options: { action?: ToastAction; key?: string } = {}): number {
  return add({ kind: 'ok', text, ...options })
}

/** Say that a save failed: the error is worded by the toaster, in the interface's language. */
export function failToast(error: unknown, key?: string): number {
  return add({ kind: 'error', error, key })
}

export function dismissToast(id: number) {
  if (toasts.some((t) => t.id === id)) set(toasts.filter((t) => t.id !== id))
}

/** For tests: no notes. */
export function clearToasts() {
  set([])
}

export const currentToasts = () => toasts

const subscribe = (l: () => void) => {
  listeners.add(l)
  return () => {
    listeners.delete(l)
  }
}

/** The notes on screen. */
export const useToasts = () => useSyncExternalStore(subscribe, currentToasts, currentToasts)

/** What a component needs to say so: `saved`, `removed with Undo`, `failed`. */
export function useToast() {
  return { show: showToast, fail: failToast, dismiss: dismissToast }
}
