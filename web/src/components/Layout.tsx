import { type RefObject, Suspense, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { TextModeToggle } from './Controls'
import { ErrorBoundary } from './ErrorBoundary'
import { Loading } from './Status'

interface NavItem {
  to: string
  label: string
  hint?: string
}
interface NavGroup {
  label: string
  items: NavItem[]
}
type NavEntry = NavItem | NavGroup

const NAV: NavEntry[] = [
  { to: '/', label: 'Browse' },
  { to: '/search', label: 'Search' },
  { to: '/compare', label: 'Compare' },
  {
    label: 'Parallels',
    items: [
      { to: '/discoveries', label: 'Discoveries', hint: 'Strong pairs Sefaria does not link' },
      { to: '/phrases', label: 'Phrases', hint: 'Shared runs of words' },
      { to: '/sequences', label: 'Sequences', hint: 'Passages parallel verse by verse' },
      { to: '/changes', label: 'Changes', hint: 'How parallel passages differ' },
      { to: '/typescenes', label: 'Action sequences', hint: 'The same actions in the same order' },
    ],
  },
  {
    label: 'Patterns',
    items: [
      { to: '/structure', label: 'Structure', hint: 'Inclusio, chiasm, Leitworte' },
      { to: '/acrostics', label: 'Acrostics', hint: 'Lines through the alphabet' },
      { to: '/poetry', label: 'Poetry', hint: 'Parallel verse halves' },
      { to: '/wordplay', label: 'Wordplay', hint: 'Sound-alike words' },
      { to: '/names', label: 'Names', hint: 'People and places' },
    ],
  },
  {
    label: 'Overview',
    items: [
      { to: '/map', label: 'Map', hint: 'Units by meaning, book affinity' },
      { to: '/network', label: 'Network', hint: 'Echo communities, most echoed passages' },
      { to: '/style', label: 'Style', hint: 'Stylometry and style shifts' },
      { to: '/eval', label: 'Evaluation', hint: 'How well known cross-references are found' },
    ],
  },
  { to: '/about', label: 'About' },
]

const isGroup = (e: NavEntry): e is NavGroup => 'items' in e

const SITE = 'Tanakh Similarity'

export function Layout() {
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  usePageTitle(mainRef)
  useNavigationFocus(mainRef, pathname)
  const [mobileOpen, setMobileOpen] = useState(false)
  // a new page closes the mobile menu
  const [seenPath, setSeenPath] = useState(pathname)
  if (seenPath !== pathname) {
    setSeenPath(pathname)
    setMobileOpen(false)
  }

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" dir="rtl" lang="he">
            מקבילות
          </span>
          <span className="brand-name">Tanakh Similarity</span>
        </Link>
        <button
          type="button"
          className="menu-toggle"
          aria-expanded={mobileOpen}
          aria-controls="main-nav"
          onClick={() => setMobileOpen((o) => !o)}
        >
          <span aria-hidden="true">{mobileOpen ? '✕' : '☰'}</span> Menu
        </button>
        <nav id="main-nav" className={`nav ${mobileOpen ? 'open' : ''}`} aria-label="Main">
          {NAV.map((e) =>
            isGroup(e) ? (
              <NavMenu key={e.label} group={e} pathname={pathname} />
            ) : (
              <NavLink key={e.to} to={e.to} end={e.to === '/'}>
                {e.label}
              </NavLink>
            ),
          )}
        </nav>
        <CopyLink />
        <TextModeToggle />
      </header>
      <main className="main" id="main" tabIndex={-1} ref={mainRef}>
        <ErrorBoundary key={pathname}>
          <Suspense fallback={<Loading />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
      <footer className="footer">
        <p>
          Display text: Sefaria, <i>Miqra according to the Masorah</i> (
          <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">
            CC-BY-SA
          </a>
          ). Lemmas and morphology:{' '}
          <a href="https://github.com/openscriptures/morphhb" target="_blank" rel="noreferrer">
            OSHB
          </a>{' '}
          (WLC public domain, morphology CC BY 4.0). Cross-references: Sefaria; OpenBible.info (CC-BY) for evaluation.
          For personal and research use.
        </p>
      </footer>
    </div>
  )
}

/** A dropdown of related pages: opens on click, closes on Escape, outside click or navigation. On
 * narrow screens (inside the open mobile menu) the group is shown as a plain labelled list. */
function NavMenu({ group, pathname }: { group: NavGroup; pathname: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const active = group.items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
  const [seenPath, setSeenPath] = useState(pathname)
  if (seenPath !== pathname) {
    setSeenPath(pathname)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const id = `menu-${group.label.toLowerCase()}`
  return (
    <div className={`nav-group ${open ? 'open' : ''}`} ref={ref}>
      <button
        type="button"
        ref={buttonRef}
        className={`nav-group-button ${active ? 'active' : ''}`}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        {group.label} <span aria-hidden="true">▾</span>
      </button>
      <ul id={id} className="nav-menu" aria-label={group.label}>
        {group.items.map((i) => (
          <li key={i.to}>
            <NavLink to={i.to}>
              <span className="nav-item-label">{i.label}</span>
              {i.hint && <span className="nav-item-hint">{i.hint}</span>}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** `document.title` follows the page's heading (pages fill it in once their data loads). */
function usePageTitle(main: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = main.current
    if (!el) return
    const update = () => {
      const h1 = el.querySelector('h1')?.textContent?.trim()
      const title = h1 ? `${h1} · ${SITE}` : SITE
      if (document.title !== title) document.title = title
    }
    update()
    const observer = new MutationObserver(update)
    observer.observe(el, { childList: true, subtree: true, characterData: true })
    return () => observer.disconnect()
  }, [main])
}

/** A new page (not a new filter on the same page) starts at the top with focus on the content,
 * so keyboard and screen-reader users are not left on the old link. */
function useNavigationFocus(main: RefObject<HTMLElement | null>, pathname: string) {
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    window.scrollTo(0, 0)
    main.current?.focus({ preventScroll: true })
  }, [main, pathname])
}

/** Copies the current page's address (every view's state is in its URL). */
function CopyLink() {
  const [done, setDone] = useState(false)
  useEffect(() => {
    if (!done) return
    const t = window.setTimeout(() => setDone(false), 1500)
    return () => window.clearTimeout(t)
  }, [done])
  return (
    <button
      type="button"
      className="copy-link"
      title="Copy a link to this view"
      onClick={() => {
        navigator.clipboard
          ?.writeText(window.location.href)
          .then(() => setDone(true))
          .catch(() => setDone(false))
      }}
    >
      <span aria-live="polite">{done ? 'Copied' : 'Copy link'}</span>
    </button>
  )
}
