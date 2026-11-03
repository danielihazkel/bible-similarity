import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { useLocale } from '../context/localeContext'
import { TOURS, isTour, tourHref } from '../lib/tours'

/** The guided tour's bar at the foot of a page whose address carries `?tour=&step=`: the step's
 * caption and the way on (DESIGN.md §11). */
export function TourBar() {
  const t = useLocale().m.tr
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const key = params.get('tour')
  const step = Number(params.get('step'))
  if (!isTour(key) || !Number.isInteger(step) || step < 1 || step > TOURS[key].length) return null
  const tour = t.tours[key]
  const n = TOURS[key].length
  const leave = () => {
    const next = new URLSearchParams(params)
    next.delete('tour')
    next.delete('step')
    const q = next.toString()
    navigate(`${pathname}${q ? `?${q}` : ''}`)
  }
  return (
    <aside className="tour-bar" aria-labelledby="tour-bar-title">
      <div className="tour-bar-inner">
        <p id="tour-bar-title" className="tour-bar-title">
          {t.bar(tour.title, step, n)}
        </p>
        <p className="tour-bar-caption">{tour.steps[step - 1]}</p>
        <div className="tour-bar-actions">
          <button type="button" disabled={step === 1} onClick={() => navigate(tourHref(key, step - 1))}>
            {t.back}
          </button>
          {step < n ? (
            <button type="button" className="primary" onClick={() => navigate(tourHref(key, step + 1))}>
              {t.next}
            </button>
          ) : (
            <button type="button" className="primary" onClick={() => navigate('/tours')}>
              {t.finish}
            </button>
          )}
          <button type="button" className="linkish small" onClick={leave}>
            {t.end}
          </button>
        </div>
      </div>
    </aside>
  )
}
