import { Link } from 'react-router'
import { useBooks, useWeek } from '../api/hooks'
import type { Book } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { isGroup, NAV, type NavItem, navText } from '../lib/nav'
import { TourList } from './ToursPage'
import { localToday, longDate } from '../lib/week'

export function BooksPage() {
  const m = useT()
  const { data, error, isPending } = useBooks()
  if (isPending) return <Loading />
  if (error) return <ErrorBox error={error} />
  const sections = new Map<string, Book[]>()
  for (const b of data) sections.set(b.section, [...(sections.get(b.section) ?? []), b])
  return (
    <div className="page">
      <h1>{m.books.title}</h1>
      <p className="lede">{m.books.lede}</p>
      <WeekCard />
      <p>
        <Link to="/findings" className="findings-link">
          {m.books.findings} {m.locale === 'he' ? '←' : '→'}
        </Link>
      </p>
      {[...sections].map(([section, books]) => (
        <section key={section} className="section">
          <h2>
            {m.units.sections[section] ?? section}
            {m.locale === 'en' && (
              <>
                {' '}
                <span className="he-label" dir="rtl" lang="he">
                  {m.units.sectionsHe[section]}
                </span>
              </>
            )}
          </h2>
          <ul className="book-grid">
            {books.map((b) => (
              <li key={b.book_id}>
                <Link to={`/browse/${b.book_id}`} className="book-card">
                  <span className="he book-he" dir="rtl" lang="he">
                    {b.he_name}
                  </span>
                  {m.locale === 'en' && <span className="book-en">{b.name}</span>}
                  <span className="muted small">{m.units.chaptersShort(b.n_chapters)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <StartHere />
      <Explore />
    </div>
  )
}

/** This week's parasha, a line linking to its page (nothing when the build has no parashot). */
function WeekCard() {
  const { m, locale } = useLocale()
  const t = m.wk
  const { data } = useWeek(localToday(), false)
  if (!data || !Array.isArray(data.parashot) || data.parashot.length === 0) return null
  const names = data.parashot.map((p) => (locale === 'he' ? p.unit.label_he : p.unit.label_en)).join('–')
  const when = longDate(data.reading_shabbat ?? data.shabbat, locale)
  return (
    <p className="wk-home">
      <span className="wk-home-title">{t.homeTitle}:</span>{' '}
      <Link to="/week">{data.festival ? t.homeFestival(names, when) : t.homeLine(names, when)}</Link>
    </p>
  )
}

/** The guided tours and the glossary, for a first visit. */
function StartHere() {
  const m = useT()
  return (
    <section className="section start-here" aria-labelledby="start-title">
      <h2 id="start-title">{m.tr.homeTitle}</h2>
      <p className="muted">
        {m.tr.homeLede} <Link to="/glossary">{m.gloss.more}</Link>
      </p>
      <TourList />
    </section>
  )
}

/** Every menu group's pages with their one-line hints (the nav's own list and texts). */
function Explore() {
  const m = useT()
  const pages = (items: NavItem[]) => (
    <ul className="explore-pages">
      {items.map((i) => {
        const { label, hint } = navText(m, i.key)
        return (
          <li key={i.to}>
            <Link to={i.to}>{label}</Link>
            {hint && <span className="muted small"> {hint}</span>}
          </li>
        )
      })}
    </ul>
  )
  return (
    <section className="section explore" aria-labelledby="explore-title">
      <h2 id="explore-title">{m.books.explore}</h2>
      <p className="muted">{m.books.exploreLede}</p>
      <div className="explore-groups">
        {NAV.filter(isGroup).map((g) => (
          <div key={g.key} className="explore-group">
            <h3>{m.nav[g.key]}</h3>
            {g.sections
              ? g.sections.map((sec) => (
                  <div key={sec.key}>
                    <h4>{m.navSections[sec.key]}</h4>
                    {pages(sec.items)}
                  </div>
                ))
              : pages(g.items)}
          </div>
        ))}
      </div>
    </section>
  )
}
