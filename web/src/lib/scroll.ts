// Where the window was scrolled to under each history entry, so Back and Forward return to the
// place that was left (a hit in a list, the foot of a page of results), not to the top. The
// positions are kept per tab (`sessionStorage`, `bsim.scroll`), keyed by the router's
// `location.key`, so a reload keeps its place too; each is kept with the address it was on, since
// the first entry of every load has the same key. `Layout` drives this: it tells the store which
// entry is on screen and asks for a position back on a POP.

export const SCROLL_KEY = 'bsim.scroll'
const MAX_ENTRIES = 60
/** How long a restore waits for the page to grow back to the height it had (its data loading). */
const WAIT_MS = 3000

interface Place {
  y: number
  at: string // pathname + search
}
const positions = new Map<string, Place>()
let loaded = false
let current: { key: string; at: string } | undefined
let lastY = 0
/** While a restore is under way its own partial scrolls are not the entry's position. */
let restoring = false

function load() {
  if (loaded) return
  loaded = true
  try {
    const raw = JSON.parse(sessionStorage.getItem(SCROLL_KEY) ?? '[]') as unknown
    if (Array.isArray(raw))
      for (const e of raw)
        if (Array.isArray(e) && typeof e[0] === 'string' && typeof e[1] === 'number' && typeof e[2] === 'string') positions.set(e[0], { y: e[1], at: e[2] })
  } catch {
    // storage unavailable or not ours: start empty
  }
}

function persist() {
  try {
    sessionStorage.setItem(SCROLL_KEY, JSON.stringify([...positions].slice(-MAX_ENTRIES).map(([k, p]) => [k, p.y, p.at])))
  } catch {
    // ignore
  }
}

function put(entry: { key: string; at: string }, y: number) {
  positions.delete(entry.key) // the newest last, so the cap drops the oldest
  positions.set(entry.key, { y, at: entry.at })
}

/** Start following the window's scrolling; returns the way to stop. The browser's own restoring
 * is turned off: it runs before a page's data is back and lands short. */
export function watchScroll(): () => void {
  load()
  try {
    history.scrollRestoration = 'manual'
  } catch {
    // not every embedding allows it
  }
  const onScroll = () => {
    if (restoring) return
    lastY = window.scrollY
    if (current !== undefined) put(current, lastY)
  }
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('pagehide', persist)
  return () => {
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('pagehide', persist)
  }
}

/** A new history entry is on screen. Call before the browser has laid the new page out (a layout
 * effect): the entry left keeps the last position the viewer scrolled to, and `carry` (the same
 * page with a new query, not by Back or Forward) gives the new entry the same position. */
export function enterEntry(key: string, at: string, carry: boolean) {
  load()
  if (current !== undefined && current.key !== key) put(current, lastY)
  const entry = { key, at }
  if (carry && savedScroll(key, at) === undefined) put(entry, lastY)
  current = entry
  persist()
}

/** The position kept for an entry at this address, if any. */
export function savedScroll(key: string, at: string): number | undefined {
  load()
  const p = positions.get(key)
  return p && p.at === at ? p.y : undefined
}

/** The window is where it is now: the entry's place, without waiting for the scroll event (Back
 * can come before it). */
function settle() {
  lastY = window.scrollY
  if (current !== undefined) put(current, lastY)
}

/** A new page starts at the top. */
export function scrollToTop() {
  window.scrollTo(0, 0)
  settle()
}

const frame = (f: () => void): number => (typeof requestAnimationFrame === 'function' ? requestAnimationFrame(f) : window.setTimeout(f, 16))
const unframe = (id: number) => (typeof cancelAnimationFrame === 'function' ? cancelAnimationFrame(id) : window.clearTimeout(id))

/** Try `step` on every frame until it says it is done, the wait runs out or the viewer takes over
 * (a wheel, a touch, a key, a click); returns the way to give up. `done` is told whether the step
 * got there (not when it was given up: by then another entry may be on screen). */
function until(step: () => boolean, done?: (reached: boolean) => void): () => void {
  const started = Date.now()
  let id = 0
  let live = true
  const end = (reached: boolean) => {
    if (!live) return
    live = false
    unframe(id)
    for (const e of TAKEOVER) window.removeEventListener(e, giveUp)
    done?.(reached)
  }
  const giveUp = () => end(false)
  const tick = () => {
    if (!live) return
    if (step()) end(true)
    else if (Date.now() - started > WAIT_MS) end(false)
    else id = frame(tick)
  }
  for (const e of TAKEOVER) window.addEventListener(e, giveUp, { passive: true })
  tick()
  return giveUp
}
const TAKEOVER = ['wheel', 'touchstart', 'keydown', 'mousedown'] as const

/** Scroll back to `y`, waiting for the page to be tall enough again. */
export function restoreScroll(y: number): () => void {
  restoring = true
  return until(
    () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      window.scrollTo(0, Math.min(y, Math.max(0, max)))
      return max >= y - 1
    },
    (reached) => {
      restoring = false
      if (reached) settle()
    },
  )
}

/** Bring the element a `#hash` names into view, in the middle of the window, once it is there. */
export function scrollToAnchor(hash: string): () => void {
  let id: string
  try {
    id = decodeURIComponent(hash.replace(/^#/, ''))
  } catch {
    return () => {}
  }
  if (!id) return () => {}
  return until(() => {
    const el = document.getElementById(id)
    if (!el) return false
    el.scrollIntoView?.({ block: 'center' })
    settle()
    return true
  })
}

/** For tests: forget everything. */
export function resetScrollMemory() {
  positions.clear()
  loaded = false
  current = undefined
  lastY = 0
  restoring = false
}
