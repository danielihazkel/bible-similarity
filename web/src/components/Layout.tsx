import { Suspense, useEffect, useRef, useState } from 'react'
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
    ],
  },
  {
    label: 'Patterns',
    items: [
      { to: '/structure', label: 'Structure', hint: 'Inclusio, chiasm, Leitworte' },
      { to: '/poetry', label: 'Poetry', hint: 'Parallel verse halves' },
      { to: '/wordplay', label: 'Wordplay', hint: 'Sound-alike words' },
      { to: '/names', label: 'Names', hint: 'People and places' },
    ],
  },
  {
    label: 'Overview',
    items: [
      { to: '/map', label: 'Map', hint: 'Units by meaning, book affinity' },
      { to: '/style', label: 'Style', hint: 'Stylometry and style shifts' },
      { to: '/eval', label: 'Evaluation', hint: 'How well known cross-references are found' },
    ],
  },
  { to: '/about', label: 'About' },
]

const isGroup = (e: NavEntry): e is NavGroup => 'items' in e

export function Layout() {
  const { pathname } = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  // a new page closes the mobile menu
  const [seenPath, setSeenPath] = useState(pathname)
  if (seenPath !== pathname) {
    setSeenPath(pathname)
    setMobileOpen(false)
  }

  return (
    <div className="app">
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
        <TextModeToggle />
      </header>
      <main className="main">
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
