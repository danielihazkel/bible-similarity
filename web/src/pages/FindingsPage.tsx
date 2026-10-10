import { Link } from 'react-router'
import { useFindings } from '../api/hooks'
import type { Finding, FindingKey } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { type NavKey, navText } from '../lib/nav'

const VERDICTS: Finding['verdict'][] = ['holds', 'fails', 'lead']
// where each finding's evidence is read
const PAGES: Record<FindingKey, { to: string; nav: NavKey }> = {
  acrostics: { to: '/acrostics', nav: 'acrostics' },
  divisions: { to: '/divisions', nav: 'divisions' },
  dating: { to: '/language', nav: 'language' },
  borrowing: { to: '/borrowing', nav: 'borrowing' },
  citations: { to: '/citations?family=command', nav: 'citations' },
  voices: { to: '/speech?view=voices', nav: 'speech' },
  clauses: { to: '/structure?view=small', nav: 'structure' },
  echoes: { to: '/network?view=directions', nav: 'network' },
  sevens: { to: '/structure', nav: 'structure' },
  chiasm: { to: '/structure?view=small', nav: 'structure' },
  allusions: { to: '/phrases?view=spread', nav: 'phrases' },
}

/** The claim each analysis tested, the numbers that decide it and the verdict they give (`/findings`). */
export function FindingsPage() {
  const { m, locale } = useLocale()
  const t = m.find
  const res = useFindings()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { items, alpha } = res.data
  return (
    <div className="page findings-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede(alpha)}</p>
      {items.length === 0 && <p className="status">{t.noData}</p>}
      {VERDICTS.map((verdict) => {
        const group = items.filter((f) => f.verdict === verdict)
        if (group.length === 0) return null
        return (
          <section key={verdict} aria-labelledby={`findings-${verdict}`} className={`findings-group ${verdict}`}>
            <h2 id={`findings-${verdict}`}>{t.groups[verdict].title}</h2>
            <p className="muted small">{t.groups[verdict].hint}</p>
            <ul className="findings-list">
              {group.map((f) => {
                const item = t.items[f.key]
                const page = PAGES[f.key]
                const label = navText(m, page.nav).label
                return (
                  <li key={f.key} className="finding">
                    <h3>{item.title}</h3>
                    <p>{item.text(f.values)}</p>
                    <Link to={page.to} className="small" aria-label={`${item.title}: ${label}`}>
                      {label} {locale === 'he' ? '←' : '→'}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
