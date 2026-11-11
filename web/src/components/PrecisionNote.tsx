import { Link } from 'react-router'
import { useDetectorPrecision } from '../api/hooks'
import type { PrecisionRow } from '../api/types'
import { useLocale } from '../context/localeContext'
import { TableWrap } from './TableCsv'
import '../i18n/pages/precision'
import '../styles/components/PrecisionNote.css'

const ORDER = ['shown', 'marked', 'strongest']

/** How often a detector is right by Claude's reading (DESIGN.md §16.86, D147): the share right of
 * what its page lists, then each population judged and the runs' calibration. Nothing when the
 * detector was not audited, or on a public server. */
export function PrecisionNote({ detector }: { detector: string }) {
  const t = useLocale().m.prc
  const res = useDetectorPrecision()
  const rows = [...(res.data?.detectors?.[detector] ?? [])].sort((a, b) => ORDER.indexOf(a.set) - ORDER.indexOf(b.set))
  if (!rows.length) return null
  const head = rows.find((r) => r.set === 'shown' && r.precision !== null)
  const runs = Array.isArray(res.data?.runs) ? res.data.runs : []
  return (
    <details className="precision-note small" data-detector={detector}>
      <summary>{head && head.precision !== null ? t.summary(head.precision, head.lo, head.hi) : t.head}</summary>
      <ul>
        {rows.map((r: PrecisionRow) => (
          <li key={r.set}>
            {(t.rows[r.set] ?? t.rows.strongest)(r.judged, r.population)}: {t.result(r.right, r.wrong, r.unsure, r.precision, r.lo, r.hi)}
          </li>
        ))}
      </ul>
      {runs.map((r) => (
        <p key={r.run}>{t.run(r.model, r.collected_at.slice(0, 10), r.places_right, r.known_right)}</p>
      ))}
      <p>
        {t.ci} {t.caveat}
      </p>
    </details>
  )
}

// where each audited detector's findings are listed
const PAGES: Record<string, string> = {
  etiologies: '/etiologies',
  brackets: '/brackets',
  retold: '/retold',
  binomials: '/binomials',
  typescenes: '/typescenes',
  acrostics: '/acrostics',
  wordplay: '/wordplay',
  allusions: '/phrases?view=spread',
  refrains: '/refrains',
  sayings: '/forms',
  lists: '/forms?view=lists',
  mirrors: '/structure?view=small',
  ciphers: '/ciphers',
  seams: '/style',
  mainline: '/mainline',
  prophetic: '/prophetic',
}

/** Every audited detector's precision on what its page lists, and on what it marks as strong
 * (Findings; DESIGN.md §16.86, D147). Nothing on a public server or before a `pages` run. */
export function PrecisionTable() {
  const t = useLocale().m.prc
  const res = useDetectorPrecision()
  const detectors = Object.entries(res.data?.detectors ?? {}).flatMap(([name, rows]) => {
    const shown = rows.find((r) => r.set === 'shown')
    return shown ? [{ name, shown, marked: rows.find((r) => r.set === 'marked') }] : []
  })
  if (!detectors.length) return null
  return (
    <section aria-labelledby="precision-table">
      <h2 id="precision-table">{t.tableTitle}</h2>
      <p className="muted small">{t.tableLede}</p>
      <TableWrap>
        <table className="change-table precision-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.detector}</th>
              <th scope="col" className="num">
                {t.cols.listed}
              </th>
              <th scope="col">{t.cols.shown}</th>
              <th scope="col">{t.cols.marked}</th>
            </tr>
          </thead>
          <tbody>
            {detectors.map(({ name, shown, marked }) => (
              <tr key={name}>
                <td>{PAGES[name] ? <Link to={PAGES[name]}>{t.detectors[name] ?? name}</Link> : (t.detectors[name] ?? name)}</td>
                <td className="num">{shown.population ?? '–'}</td>
                <td>{t.share(shown.precision, shown.lo, shown.hi, shown.judged)}</td>
                <td>{marked ? t.share(marked.precision, marked.lo, marked.hi, marked.judged) : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </section>
  )
}
