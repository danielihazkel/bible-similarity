import { Link, NavLink, Outlet } from 'react-router'
import { TextModeToggle } from './Controls'

export function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" dir="rtl" lang="he">
            מקבילות
          </span>
          <span className="brand-name">Tanakh Similarity</span>
        </Link>
        <nav className="nav">
          <NavLink to="/" end>
            Browse
          </NavLink>
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/discoveries">Discoveries</NavLink>
          <NavLink to="/phrases">Phrases</NavLink>
          <NavLink to="/structure">Structure</NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/about">About</NavLink>
        </nav>
        <TextModeToggle />
      </header>
      <main className="main">
        <Outlet />
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
          (WLC public domain, morphology CC BY 4.0). Cross-references: Sefaria. For personal and research use.
        </p>
      </footer>
    </div>
  )
}
