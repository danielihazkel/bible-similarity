import { useSyncExternalStore } from 'react'

// The offline app's state for its banner (components/AppBanner.tsx): whether the browser is
// online, and the reload that installs a new build waiting in the service worker
// (`startServiceWorker`, called by main.tsx in production builds only; vite.config.ts).

let update: (() => void) | null = null
const listeners = new Set<() => void>()

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  window.addEventListener('online', listener)
  window.addEventListener('offline', listener)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('online', listener)
    window.removeEventListener('offline', listener)
  }
}

/** A new build is installed and waiting: `apply` reloads the page into it. `null` withdraws it. */
export function offerUpdate(apply: (() => void) | null): void {
  update = apply
  for (const l of listeners) l()
}

/** Whether the browser says it is online (`navigator.onLine`, kept by its events). */
export const useOnline = (): boolean => useSyncExternalStore(subscribe, () => navigator.onLine, () => true)

/** The reload into a waiting new build, if there is one. */
export const currentUpdate = (): (() => void) | null => update

/** `currentUpdate`, kept by a component. */
export const useUpdate = (): (() => void) | null => useSyncExternalStore(subscribe, currentUpdate, () => null)

/** `registerSW` of `virtual:pwa-register` (injected, so the tests need no build). */
export type RegisterSW = (options: { onNeedRefresh: () => void; onNeedReload: () => void }) => () => Promise<void>

/**
 * Registers the service worker; a new build waiting in it is offered on the banner, and taking
 * it reloads the page once the new worker controls it. The reload is ours: the plugin's own
 * reloads only a worker it counts as this page's update, not one found while the page was open
 * (`isExternal`), which is how a new build is usually found.
 */
export function startServiceWorker(register: RegisterSW, reload: () => void = () => window.location.reload()): void {
  const apply = () => {
    navigator.serviceWorker.addEventListener('controllerchange', () => reload(), { once: true })
    void updateSW()
  }
  const updateSW = register({ onNeedRefresh: () => offerUpdate(apply), onNeedReload: () => {} })
}
