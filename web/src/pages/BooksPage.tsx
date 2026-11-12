import { Link } from 'react-router'
import { useBooks, useNotebook, useServer, useWeek } from '../api/hooks'
import type { Book } from '../api/types'
import { JumpField } from '../components/JumpBox'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { ALL_PAGES, NAV_PAGE, type NavItem, navText, PERSONAL_PAGES } from '../lib/nav'
import { unitLabel } from '../lib/names'
import { passageOf, type RecentPassage, usePins, useRecent } from '../lib/recent'
import { TourList } from './ToursPage'
import { localToday, longDate } from '../lib/week'
import '../i18n/pages/glossary'
import '../i18n/pages/tours'
import '../i18n/pages/week'
import '../styles/pages/BooksPage.css'

const PASSAGES_SHOWN = 6
const PAGES_SHOWN = 6
const NOTES_SHOWN = 3

/** The start page (`/`): a jump field, then the viewer's own way back in (the passages and pages
 * opened last, the pinned pages, the latest notebook entries), this week's parasha and the
 * findings, and the books. A first visit, with nothing stored, has the guided tours where the
 * recent ones would be. */
export function BooksPage() {
  const m = useT()
  const { personal } = useServer()
  const recent = useRecent()
  const pins = usePins()
  const pages = (paths: string[]) =>
    paths.flatMap((to) => {
      const page = personal || !PERSONAL_PAGES.has(to) ? NAV_PAGE.get(to) : undefined
      return page ? [page] : []
    })
  const pinned = pages(pins)
  // a pinned page is in its own row, not among the recent ones too
  const recentPages = pages(recent.pages.filter((to) => !pins.includes(to))).slice(0, PAGES_SHOWN)
  const passages = recent.passages.slice(0, PASSAGES_SHOWN)
  const fresh = passages.length === 0 && recentPages.length === 0 && pinned.length === 0
  const arrow = m.locale === 'he' ? '←' : '→'
  return (
    <div className="page start-page">
      <h1>{m.books.title}</h1>
      <JumpField inline />
      {fresh ? <StartHere /> : (passages.length > 0 || recentPages.length > 0) && <Continue passages={passages} pages={recentPages} />}
      {pinned.length > 0 && (
        <section className="section" aria-labelledby="start-pinned">
          <h2 id="start-pinned">{m.site.pinned}</h2>
          <PageLinks pages={pinned} labelledBy="start-pinned" />
        </section>
      )}
      {personal && <LatestNotes />}
      <WeekCard />
      <ul className="start-more">
        <li>
          <Link to="/findings" className="findings-link">
            {m.books.findings} {arrow}
          </Link>
        </li>
        <li>
          <Link to={ALL_PAGES}>
            {m.books.allPages} {arrow}
          </Link>
        </li>
      </ul>
      <BookList />
      {!fresh && (
        <p className="muted start-tours">
          {m.tr.homeTitle} <Link to="/tours">{m.tr.homeTours}</Link> · <Link to="/glossary">{m.gloss.more}</Link>
        </p>
      )}
    </div>
  )
}

/** The passages opened last as cards (the unit page or the reader, as each was left), and the pages
 * opened last as a row of links. */
function Continue({ passages, pages }: { passages: RecentPassage[]; pages: NavItem[] }) {
  const { m, locale } = useLocale()
  return (
    <section className="section" aria-labelledby="start-continue">
      <h2 id="start-continue">{m.books.resume}</h2>
      {passages.length > 0 && (
        <ul className="book-grid start-passages" aria-label={m.jump.recentPassages}>
          {passages.map((p) => (
            <li key={p.to}>
              <Link to={p.to} className="book-card">
                <span className="he start-passage-he" dir="rtl" lang="he">
                  {p.he}
                </span>
                {locale === 'en' && <span className="book-en">{p.en}</span>}
                {passageOf(p.to)?.view === 'read' && <span className="muted small">{m.jump.inReader}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {pages.length > 0 && (
        <div className="start-row">
          <span className="muted small" id="start-recent-pages">
            {m.jump.recentPages}
          </span>
          <PageLinks pages={pages} labelledBy="start-recent-pages" />
        </div>
      )}
    </section>
  )
}

/** Nav pages as a row of links, each with its hint as a tooltip. */
function PageLinks({ pages, labelledBy }: { pages: NavItem[]; labelledBy: string }) {
  const m = useT()
  return (
    <ul className="start-pages" aria-labelledby={labelledBy}>
      {pages.map((p) => {
        const { label, hint } = navText(m, p.key)
        return (
          <li key={p.to}>
            <Link to={p.to} className="start-page-link" title={hint}>
              {label}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

/** The notebook's latest entries, each a passage and the start of its note (a personal server
 * with something kept; nothing otherwise). */
function LatestNotes() {
  const { m, locale } = useLocale()
  const { data } = useNotebook()
  const entries = [...(data?.entries ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, NOTES_SHOWN)
  if (entries.length === 0) return null
  return (
    <section className="section" aria-labelledby="start-notebook">
      <h2 id="start-notebook">{m.nav.notebook}</h2>
      <ul className="start-notes">
        {entries.map((e) => (
          <li key={e.unit.unit_id}>
            <Link to={unitLink(e.unit.unit_id)}>{unitLabel(e.unit, locale)}</Link>
            {e.note.trim() && (
              <span className="start-note muted" dir="auto">
                {e.note.trim().split('\n')[0]}
              </span>
            )}
          </li>
        ))}
      </ul>
      <p className="small">
        <Link to="/notebook">
          {m.books.notebookAll} {m.locale === 'he' ? '←' : '→'}
        </Link>
      </p>
    </section>
  )
}

/** The books by section of the canon, each a link to its chapters. */
function BookList() {
  const m = useT()
  const { data, error, isPending } = useBooks()
  const sections = new Map<string, Book[]>()
  for (const b of data ?? []) sections.set(b.section, [...(sections.get(b.section) ?? []), b])
  return (
    <section className="section start-books" aria-labelledby="start-books">
      <h2 id="start-books">{m.books.booksTitle}</h2>
      <p className="lede">{m.books.lede}</p>
      {isPending ? (
        <Loading />
      ) : error ? (
        <ErrorBox error={error} />
      ) : (
        [...sections].map(([section, books]) => (
          <div key={section} className="start-canon">
            <h3>
              {m.units.sections[section] ?? section}
              {m.locale === 'en' && (
                <>
                  {' '}
                  <span className="he-label" dir="rtl" lang="he">
                    {m.units.sectionsHe[section]}
                  </span>
                </>
              )}
            </h3>
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
          </div>
        ))
      )}
    </section>
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

/** A first visit: the guided tours and the glossary, where the recent passages will be. */
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
