import { Link } from 'react-router'
import { useLocale } from '../context/localeContext'
import { TOUR_KEYS, TOURS, tourHref } from '../lib/tours'

/** The guided tours (§11): each with its pages, started from here or from the home page. */
export function ToursPage() {
  const t = useLocale().m.tr
  return (
    <div className="page tours-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <TourList />
    </div>
  )
}

/** The tours as cards with a start link (the tours page and the home page). */
export function TourList() {
  const t = useLocale().m.tr
  return (
    <ul className="tour-list">
      {TOUR_KEYS.map((k) => (
        <li key={k} className="tour-card">
          <h3>{t.tours[k].title}</h3>
          <p className="muted small">{t.tours[k].lede}</p>
          <p className="small">
            <Link to={tourHref(k, 1)} aria-label={`${t.start}: ${t.tours[k].title}`}>
              {t.start}
            </Link>{' '}
            <span className="muted">· {t.steps(TOURS[k].length)}</span>
          </p>
        </li>
      ))}
    </ul>
  )
}
