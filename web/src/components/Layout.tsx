import { type RefObject, Suspense, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { useT } from '../context/localeContext'
import type { Messages } from '../i18n'
import { LocaleToggle, TextModeToggle } from './Controls'
import { ErrorBoundary } from './ErrorBoundary'
import { Loading } from './Status'

type GroupKey = 'parallels' | 'patterns' | 'overview'
type NavKey = Exclude<keyof Messages['nav'], GroupKey>

interface NavItem {
  to: string
  key: NavKey
}
interface NavGroup {
  key: GroupKey
  items: NavItem[]
}
type NavEntry = NavItem | NavGroup

const NAV: NavEntry[] = [
  { to: '/', key: 'browse' },
  { to: '/search', key: 'search' },
  { to: '/compare', key: 'compare' },
  {
    key: 'parallels',
    items: [
      { to: '/discoveries', key: 'discoveries' },
      { to: '/labels', key: 'labels' },
      { to: '/phrases', key: 'phrases' },
      { to: '/sequences', key: 'sequences' },
      { to: '/changes', key: 'changes' },
      { to: '/borrowing', key: 'borrowing' },
      { to: '/typescenes', key: 'typescenes' },
    ],
  },
  {
    key: 'patterns',
    items: [
      { to: '/structure', key: 'structure' },
      { to: '/acrostics', key: 'acrostics' },
      { to: '/divisions', key: 'divisions' },
      { to: '/ketiv', key: 'ketiv' },
      { to: '/poetry', key: 'poetry' },
      { to: '/wordplay', key: 'wordplay' },
      { to: '/names', key: 'names' },
      { to: '/domains', key: 'domains' },
    ],
  },
  {
    key: 'overview',
    items: [
      { to: '/map', key: 'map' },
      { to: '/network', key: 'network' },
      { to: '/style', key: 'style' },
      { to: '/shifts', key: 'shifts' },
      { to: '/language', key: 'language' },
      { to: '/speech', key: 'speech' },
      { to: '/eval', key: 'eval' },
    ],
  },
  { to: '/about', key: 'about' },
]

const isGroup = (e: NavEntry): e is NavGroup => 'items' in e

/** A nav entry's label and hint (top-level links have no hint). */
function navText(m: Messages, key: NavKey): { label: string; hint?: string } {
  const v = m.nav[key]
  return typeof v === 'string' ? { label: v } : v
}

export function Layout() {
  const m = useT()
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  usePageTitle(mainRef, m.site.name)
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
        {m.site.skip}
      </a>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" dir="rtl" lang="he">
            מקבילות
          </span>
          {m.locale === 'en' && <span className="brand-name">{m.site.name}</span>}
        </Link>
        <button
          type="button"
          className="menu-toggle"
          aria-expanded={mobileOpen}
          aria-controls="main-nav"
          onClick={() => setMobileOpen((o) => !o)}
        >
          <span aria-hidden="true">{mobileOpen ? '✕' : '☰'}</span> {m.site.menu}
        </button>
        <nav id="main-nav" className={`nav ${mobileOpen ? 'open' : ''}`} aria-label={m.site.mainNav}>
          {NAV.map((e) =>
            isGroup(e) ? (
              <NavMenu key={e.key} group={e} pathname={pathname} />
            ) : (
              <NavLink key={e.to} to={e.to} end={e.to === '/'}>
                {navText(m, e.key).label}
              </NavLink>
            ),
          )}
        </nav>
        <CopyLink />
        <TextModeToggle />
        <LocaleToggle />
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
          {m.site.footer.display} <i>{m.site.footer.mam}</i> (
          <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">
            CC-BY-SA
          </a>
          ). {m.site.footer.lemmas}{' '}
          <a href="https://github.com/openscriptures/morphhb" target="_blank" rel="noreferrer">
            OSHB
          </a>{' '}
          {m.site.footer.wlc}
        </p>
        <p>{m.site.footer.lexicon}</p>
        <p>{m.site.footer.syntax}</p>
      </footer>
    </div>
  )
}

/** A dropdown of related pages: opens on click, closes on Escape, outside click or navigation. On
 * narrow screens (inside the open mobile menu) the group is shown as a plain labelled list. */
function NavMenu({ group, pathname }: { group: NavGroup; pathname: string }) {
  const m = useT()
  const label = m.nav[group.key]
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

  const id = `menu-${group.key}`
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
        {label} <span aria-hidden="true">▾</span>
      </button>
      <ul id={id} className="nav-menu" aria-label={label}>
        {group.items.map((i) => {
          const { label, hint } = navText(m, i.key)
          return (
            <li key={i.to}>
              <NavLink to={i.to}>
                <span className="nav-item-label">{label}</span>
                {hint && <span className="nav-item-hint">{hint}</span>}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/** `document.title` follows the page's heading (pages fill it in once their data loads). */
function usePageTitle(main: RefObject<HTMLElement | null>, site: string) {
  useEffect(() => {
    const el = main.current
    if (!el) return
    const update = () => {
      const h1 = el.querySelector('h1')?.textContent?.trim()
      const title = h1 ? `${h1} · ${site}` : site
      if (document.title !== title) document.title = title
    }
    update()
    const observer = new MutationObserver(update)
    observer.observe(el, { childList: true, subtree: true, characterData: true })
    return () => observer.disconnect()
  }, [main, site])
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
  const m = useT()
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
      title={m.site.copyLinkTitle}
      onClick={() => {
        navigator.clipboard
          ?.writeText(window.location.href)
          .then(() => setDone(true))
          .catch(() => setDone(false))
      }}
    >
      <span aria-live="polite">{done ? m.site.copied : m.site.copyLink}</span>
    </button>
  )
}
