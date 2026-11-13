import { type RefObject, Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigationType } from 'react-router'
import { useT } from '../context/localeContext'
import { useServer, useUnit } from '../api/hooks'
import { useFitInWindow } from '../lib/menuFit'
import { ALL_PAGES, isGroup, NAV_PAGE, type NavItem, type NavSection, navFor, navText, PERSONAL_PAGES } from '../lib/nav'
import { isNavPage, passageLink, passageOf, usePins, visitPage, visitPassage } from '../lib/recent'
import { enterEntry, restoreScroll, savedScroll, scrollToAnchor, scrollToTop, watchScroll } from '../lib/scroll'
import { DisplayMenu } from './DisplayMenu'
import { JumpBox } from './JumpBox'
import { PinButton } from './PinButton'
import { TourBar } from './TourBar'
import { AppBanner } from './AppBanner'
import { ErrorBoundary } from './ErrorBoundary'
import { Loading } from './Status'

export function Layout() {
  const m = useT()
  const { pathname } = useLocation()
  const { personal } = useServer()
  const mainRef = useRef<HTMLElement>(null)
  usePageTitle(mainRef, m.site.name)
  useNavigationFocus(mainRef)
  useRecordVisit(pathname)
  // the pinned pages this server offers, as nav items
  const pins = usePins()
  const pinned = pins.flatMap((to) => {
    const page = personal || !PERSONAL_PAGES.has(to) ? NAV_PAGE.get(to) : undefined
    return page ? [page] : []
  })
  const within = (items: NavItem[]) => items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
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
  // Escape closes the phone menu and gives the focus back to its button; an open group inside it
  // or the open Display menu takes the key first (each closes itself)
  const menuToggle = useRef<HTMLButtonElement>(null)
  // the bar's height, for what sticks under it (a page's section strip) and scrolls to under it
  const bar = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = bar.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const set = () => document.documentElement.style.setProperty('--topbar-h', `${Math.round(el.getBoundingClientRect().height)}px`)
    set()
    const seen = new ResizeObserver(set)
    seen.observe(el)
    return () => seen.disconnect()
  }, [])
  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || document.querySelector('#main-nav .nav-group.open, .display-menu.open, .filter-menu.open')) return
      setMobileOpen(false)
      menuToggle.current?.focus()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [mobileOpen])
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
      <header className="topbar" ref={bar}>
        <Link to="/" className="brand">
          <span className="brand-mark" dir="rtl" lang="he">
            מקבילות
          </span>
          {m.locale === 'en' && <span className="brand-name">{m.site.name}</span>}
        </Link>
        <button
          type="button"
          className="menu-toggle"
          ref={menuToggle}
          aria-expanded={mobileOpen}
          aria-controls="main-nav"
          onClick={() => setMobileOpen((o) => !o)}
        >
          <span aria-hidden="true">{mobileOpen ? '✕' : '☰'}</span> {m.site.menu}
        </button>
        <nav id="main-nav" className={`nav ${mobileOpen ? 'open' : ''}`} aria-label={m.site.mainNav}>
          {pinned.length > 0 && <NavMenu id="menu-pinned" label={m.site.pinned} items={pinned} active={false} pathname={pathname} mobileOpen={mobileOpen} />}
          {navFor(personal).map((e) =>
            isGroup(e) ? (
              <NavMenu key={e.key} id={`menu-${e.key}`} label={m.nav[e.key]} items={e.items} sections={e.sections} active={within(e.items)} pathname={pathname} mobileOpen={mobileOpen} />
            ) : (
              <NavLink key={e.to} to={e.to} end={e.to === '/'}>
                {navText(m, e.key).label}
              </NavLink>
            ),
          )}
        </nav>
        {isNavPage(pathname) && (personal || !PERSONAL_PAGES.has(pathname)) && <PinButton to={pathname} className="copy-link" />}
        <button type="button" className="copy-link jump-open" title={m.jump.openTitle} aria-haspopup="dialog" onClick={() => setJumpOpen(true)}>
          {m.jump.open} <kbd aria-hidden="true">Ctrl K</kbd>
        </button>
        <DisplayMenu />
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

/** A dropdown of pages (a group of the nav, or the pinned pages): opens on click, closes on Escape,
 * outside click or navigation. A big group is laid out in two columns, a sectioned one (Patterns)
 * in a column per heading, so it fits under the sticky top bar; each ends with the link to the
 * index of every page. On narrow screens (inside the open mobile menu) each group is a disclosure:
 * the current page's group (`active`) opens with the menu, the others on a tap. */
function NavMenu({
  id,
  label,
  items,
  sections,
  active,
  pathname,
  mobileOpen,
}: {
  id: string
  label: string
  items: NavItem[]
  sections?: NavSection[]
  active: boolean
  pathname: string
  mobileOpen: boolean
}) {
  const m = useT()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
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

  useFitInWindow(menuRef, open)

  const foot = (
    <NavLink to={ALL_PAGES} className="nav-menu-foot">
      {m.site.allPages}
    </NavLink>
  )
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
      {sections ? (
        <div id={id} ref={menuRef} className="nav-menu sectioned">
          {sections.map((sec) => (
            <div key={sec.key} className="nav-section">
              <span className="nav-section-title" id={`${id}-${sec.key}`}>
                {m.navSections[sec.key]}
              </span>
              <NavItems items={sec.items} labelledBy={`${id}-${sec.key}`} />
            </div>
          ))}
          {foot}
        </div>
      ) : (
        <div id={id} ref={menuRef} className={`nav-menu ${items.length > 10 ? 'wide' : ''}`}>
          <NavItems items={items} label={label} />
          {foot}
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

/** The page or passage on screen goes to the head of the recent ones (`lib/recent.ts`): a nav page
 * by its path, a passage once its unit is known (the unit page and the reader ask for the same
 * unit, so this is no second request). A verse opened in the reader is not recorded: the reader
 * sends it on to its chapter. */
function useRecordVisit(pathname: string) {
  const passage = passageOf(pathname)
  const unit = useUnit(passage?.id).data?.unit
  useEffect(() => {
    visitPage(pathname)
  }, [pathname])
  const view = passage?.view
  useEffect(() => {
    if (!view || !unit || unit.unit_id !== passageOf(pathname)?.id) return
    if (view === 'read' && unit.unit_type === 'verse') return
    visitPassage({ to: passageLink(view, unit.unit_id), en: unit.label_en, he: unit.label_he })
  }, [pathname, view, unit])
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

/** Where a navigation leaves the window and the focus. A new page (not a new filter on the same
 * page) starts at the top with focus on the content, so keyboard and screen-reader users are not
 * left on the old link. Back and Forward (and a reload) return to where the entry was left
 * (`lib/scroll.ts`), once the page is as tall as it was. An address with a `#hash` brings the
 * element it names into view (a verse in the reader). */
function useNavigationFocus(main: RefObject<HTMLElement | null>) {
  const { key, pathname, search, hash } = useLocation()
  const type = useNavigationType()
  const at = pathname + search
  const shown = useRef<{ key: string; pathname: string } | undefined>(undefined)
  useEffect(() => watchScroll(), [])
  // before the new page is laid out, so the entry left keeps the place the viewer scrolled to
  useLayoutEffect(() => {
    const before = shown.current
    enterEntry(key, at, !!before && before.pathname === pathname && type !== 'POP')
    // one run per history entry: the address and the kind of navigation belong to the key
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  useEffect(() => {
    const before = shown.current
    shown.current = { key, pathname }
    const newPage = !!before && before.pathname !== pathname
    if (newPage) main.current?.focus({ preventScroll: true })
    const saved = type === 'POP' ? savedScroll(key, at) : undefined
    if (saved !== undefined) {
      if (saved > 0) return restoreScroll(saved)
      if (before) scrollToTop()
      return
    }
    if (hash) return scrollToAnchor(hash)
    if (newPage) scrollToTop()
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
}
