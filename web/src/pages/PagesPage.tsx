import { Link } from 'react-router'
import { useServer } from '../api/hooks'
import { PinButton } from '../components/PinButton'
import { useT } from '../context/localeContext'
import { isGroup, matchPages, NAV_PAGE, type NavItem, navFor, navText } from '../lib/nav'
import { isNavPage, usePins } from '../lib/recent'
import { useQueryParams } from '../lib/urlState'
import '../styles/pages/PagesPage.css'

/** Every page of the site by menu and section, each with its hint and a star to pin it; a filter
 * box narrows the list as the jump box matches pages (`matchPages`). Linked at the foot of each
 * menu of the top bar. */
export function PagesPage() {
  const m = useT()
  const t = m.pageIndex
  const { personal } = useServer()
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const nav = navFor(personal)
  const all = nav.flatMap((e) => (isGroup(e) ? e.items : [e]))
  const offered = new Set(all.map((p) => p.to))
  // the filter starts at two letters, as the jump box's does
  const hits = q.trim().length >= 2 ? new Set(matchPages(m, q, all.length, personal).map((p) => p.to)) : undefined
  const keep = (items: NavItem[]) => (hits ? items.filter((i) => hits.has(i.to)) : items)
  const pinned = keep(
    usePins().flatMap((to) => {
      const page = offered.has(to) ? NAV_PAGE.get(to) : undefined
      return page ? [page] : []
    }),
  )
  const top = keep(nav.filter((e): e is NavItem => !isGroup(e)))
  const groups = nav.filter(isGroup)

  const rows = (items: NavItem[], labelledBy: string) => (
    <ul className="pages-list" aria-labelledby={labelledBy}>
      {items.map((i) => {
        const { label, hint } = navText(m, i.key)
        return (
          <li key={i.to} className="pages-row">
            {/* the home page is the brand's link: no star, its place kept */}
            {isNavPage(i.to) ? <PinButton to={i.to} className="pages-star" /> : <span className="pages-star" aria-hidden="true" />}
            <Link to={i.to} className="pages-link">
              {label}
            </Link>
            {hint && <span className="pages-hint muted small">{hint}</span>}
          </li>
        )
      })}
    </ul>
  )

  return (
    <div className="page pages-index">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <label className="control">
          <span>{t.filter}</span>
          <input type="search" dir="auto" value={q} placeholder={t.filterPlaceholder} spellCheck={false} onChange={(e) => update({ q: e.target.value || null })} />
        </label>
        <span className="muted small" aria-live="polite">
          {hits ? t.matching(hits.size, all.length) : t.count(all.length)}
        </span>
      </div>
      {hits?.size === 0 && (
        <p className="status">
          {t.none(q.trim())}{' '}
          <button type="button" className="linkish" onClick={() => update({ q: null })}>
            {t.clear}
          </button>
        </p>
      )}
      {pinned.length > 0 && (
        <section className="section" aria-labelledby="pages-pinned">
          <h2 id="pages-pinned">{m.site.pinned}</h2>
          {rows(pinned, 'pages-pinned')}
        </section>
      )}
      {top.length > 0 && (
        <section className="section" aria-labelledby="pages-top">
          <h2 id="pages-top">{t.top}</h2>
          {rows(top, 'pages-top')}
        </section>
      )}
      {groups.map((g) => {
        if (keep(g.items).length === 0) return null
        const id = `pages-${g.key}`
        return (
          <section key={g.key} className="section" aria-labelledby={id}>
            <h2 id={id}>{m.nav[g.key]}</h2>
            {g.sections
              ? g.sections.map((sec) => {
                  const items = keep(sec.items)
                  if (items.length === 0) return null
                  return (
                    <div key={sec.key} className="pages-section">
                      <h3 id={`${id}-${sec.key}`}>{m.navSections[sec.key]}</h3>
                      {rows(items, `${id}-${sec.key}`)}
                    </div>
                  )
                })
              : rows(keep(g.items), id)}
          </section>
        )
      })}
    </div>
  )
}
