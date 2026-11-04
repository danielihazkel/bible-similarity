import { type RefObject, Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { useT } from '../context/localeContext'
import { isGroup, NAV, type NavGroup, type NavItem, navText } from '../lib/nav'
import { LocaleToggle, TextModeToggle } from './Controls'
import { JumpBox } from './JumpBox'
import { TourBar } from './TourBar'
import { AppBanner } from './AppBanner'
import { ErrorBoundary } from './ErrorBoundary'
import { Loading } from './Status'

export function Layout() {
  const m = useT()
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  usePageTitle(mainRef, m.site.name)
  useNavigationFocus(mainRef, pathname)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [jumpOpen, setJumpOpen] = useState(false)
  // Ctrl+K (⌘K) opens the jump box anywhere, and closes it again
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setJumpOpen((o) => !o)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])
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
              <NavMenu key={e.key} group={e} pathname={pathname} mobileOpen={mobileOpen} />
            ) : (
              <NavLink key={e.to} to={e.to} end={e.to === '/'}>
                {navText(m, e.key).label}
              </NavLink>
            ),
          )}
        </nav>
        <button type="button" className="copy-link jump-open" title={m.jump.openTitle} aria-haspopup="dialog" onClick={() => setJumpOpen(true)}>
          {m.jump.open} <kbd aria-hidden="true">Ctrl K</kbd>
        </button>
        <CopyLink />
        <TextModeToggle />
        <LocaleToggle />
      </header>
      <AppBanner />
      {jumpOpen && <JumpBox onClose={() => setJumpOpen(false)} />}
      <main className="main" id="main" tabIndex={-1} ref={mainRef}>
        <ErrorBoundary key={pathname}>
          <Suspense fallback={<Loading />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
      <TourBar />
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

/** A dropdown of related pages: opens on click, closes on Escape, outside click or navigation. A
 * big group is laid out in two columns, a sectioned one (Patterns) in a column per heading, so it
 * fits under the sticky top bar. On narrow screens (inside the open mobile menu) each group is a
 * disclosure: the current page's group opens with the menu, the others on a tap. */
function NavMenu({ group, pathname, mobileOpen }: { group: NavGroup; pathname: string; mobileOpen: boolean }) {
  const m = useT()
  const label = m.nav[group.key]
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const active = group.items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
  const [seenPath, setSeenPath] = useState(pathname)
  if (seenPath !== pathname) {
    setSeenPath(pathname)
    setOpen(false)
  }
  // the phone menu opens with the current page's group expanded
  const [seenMobile, setSeenMobile] = useState(mobileOpen)
  if (seenMobile !== mobileOpen) {
    setSeenMobile(mobileOpen)
    setOpen(mobileOpen && active)
  }

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      // inside the phone menu the groups are disclosures: a tap elsewhere leaves this one open
      if (mobileOpen) return
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
  }, [open, mobileOpen])

  // an open menu that would spill past the window's edge is slid back inside it
  useLayoutEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const fit = () => {
      menu.style.setProperty('--menu-shift', '0px')
      if (!open) return
      const { left, right } = menu.getBoundingClientRect()
      const edge = document.documentElement.clientWidth - 8
      const shift = right > edge ? edge - right : left < 8 ? 8 - left : 0
      menu.style.setProperty('--menu-shift', `${Math.round(shift)}px`)
    }
    fit()
    if (!open) return
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
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
      {group.sections ? (
        <div id={id} ref={menuRef} className="nav-menu sectioned">
          {group.sections.map((sec) => (
            <div key={sec.key} className="nav-section">
              <span className="nav-section-title" id={`${id}-${sec.key}`}>
                {m.navSections[sec.key]}
              </span>
              <NavItems items={sec.items} labelledBy={`${id}-${sec.key}`} />
            </div>
          ))}
        </div>
      ) : (
        <div id={id} ref={menuRef} className={`nav-menu ${group.items.length > 10 ? 'wide' : ''}`}>
          <NavItems items={group.items} label={label} />
        </div>
      )}
    </div>
  )
}

function NavItems({ items, label, labelledBy }: { items: NavItem[]; label?: string; labelledBy?: string }) {
  const m = useT()
  return (
    <ul className="nav-items" aria-label={label} aria-labelledby={labelledBy}>
      {items.map((i) => {
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
