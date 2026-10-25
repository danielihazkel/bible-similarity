import { Link } from 'react-router'
import { useSynopses } from '../api/hooks'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'

/** Parallel sequences joined into synopses of three or more passages (DESIGN.md §16.74). */
export function SynopsesPage() {
  const { m, locale } = useLocale()
  const t = m.par.synopses
  const res = useSynopses()
  return (
    <div className="page synopses-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending && <Loading />}
      {res.error && <ErrorBox error={res.error} />}
      {res.data && res.data.items.length === 0 && <p className="status">{t.none}</p>}
      {res.data && res.data.items.length > 0 && (
        <>
          <p className="muted small">{t.count(res.data.items.length)}</p>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t.title}>
            <table className="change-table synopses-table">
              <thead>
                <tr>
                  <th scope="col">{t.passages}</th>
                  <th scope="col" className="num">
                    {t.rows}
                  </th>
                  <th scope="col" className="num">
                    {t.aligned}
                  </th>
                  <th scope="col" className="num">
                    {t.chains}
                  </th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((s) => (
                  <tr key={s.syn_id}>
                    <td>
                      <Link to={`/synopses/${s.syn_id}`} className="syn-passages">
                        {s.columns.map((c, i) => (
                          <span key={i}>{locale === 'he' ? c.label_he : c.label}</span>
                        ))}
                      </Link>
                    </td>
                    <td className="num">{s.n_rows}</td>
                    <td className="num">{s.n_aligned}</td>
                    <td className="num">{s.seq_ids.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
