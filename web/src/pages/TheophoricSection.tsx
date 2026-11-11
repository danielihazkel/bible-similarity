import { Link } from 'react-router'
import { useTheophoric } from '../api/hooks'
import type { TheophoricBook } from '../api/types'
import { TableCsv } from '../components/TableCsv'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { nameLink } from '../lib/links'
import '../i18n/pages/theophoric'

const FORMS = ['yahu', 'yah', 'yeho', 'yo', 'el_first', 'el_last'] as const

/** Names built on God's name (DESIGN.md §16.90, D152), on the Language page: the claim, the
 * books named in advance, the forms by book and the most frequent names. */
export function TheophoricSection({ names }: { names: Map<number, string> }) {
  const { m } = useLocale()
  const t = m.theo
  const res = useTheophoric()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const c = d.claim
  const short = (b: TheophoricBook) => (b.yahu + b.yah ? b.yah / (b.yahu + b.yah) : null)
  const books = d.books.filter((b) => FORMS.some((f) => b[f] > 0))
  return (
    <section aria-labelledby="theophoric" className="theophoric">
      <h2 id="theophoric">{t.title}</h2>
      <p className="lede">{t.lede}</p>
      <p>
        <span className={`dv-verdict ${c.holds ? 'holds' : 'fails'}`}>{t.verdict[c.holds ? 'holds' : 'fails']}</span>{' '}
        {t.claim(c.late_short ?? 0, c.early_short ?? 0, c.names, c.p.toPrecision(2))}
      </p>
      <h3>{t.knownTitle}</h3>
      <ul className="small">
        {d.known.map((k) => (
          <li key={k.books.join('+')}>
            {t.known(k.book_ids.map((id, i) => names.get(id) ?? k.books[i]).join(', '), k.side, k.short, k.endings, k.holds)}
          </li>
        ))}
      </ul>
      <p className="muted small">{t.notInModel}</p>
      <h3>{t.booksTitle}</h3>
      <TableCsv name="theophoric-books">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">{t.cols.book}</th>
              <th scope="col" className="num">
                {t.cols.yahu}
              </th>
              <th scope="col" className="num">
                {t.cols.yah}
              </th>
              <th scope="col" className="num">
                {t.cols.short}
              </th>
              <th scope="col" className="num">
                {t.cols.yeho}
              </th>
              <th scope="col" className="num">
                {t.cols.yo}
              </th>
              <th scope="col" className="num">
                {t.cols.el}
              </th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => {
              const s = short(b)
              return (
                <tr key={b.book_id}>
                  <td>{names.get(b.book_id) ?? b.book_id}</td>
                  <td className="num">{b.yahu}</td>
                  <td className="num">{b.yah}</td>
                  <td className="num">{s === null ? '–' : `${Math.round(s * 100)}%`}</td>
                  <td className="num">{b.yeho}</td>
                  <td className="num">{b.yo}</td>
                  <td className="num">{b.el_first + b.el_last}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </TableCsv>
      <h3>{t.namesTitle}</h3>
      <TableCsv name="theophoric-names">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">{t.namesCols.name}</th>
              <th scope="col" className="num">
                {t.namesCols.n}
              </th>
              <th scope="col">{t.namesCols.forms}</th>
            </tr>
          </thead>
          <tbody>
            {d.names.map((n) => (
              <tr key={n.lemma}>
                <td>
                  <Link to={nameLink(n.lemma)} lang="he" dir="rtl">
                    {n.he}
                  </Link>
                </td>
                <td className="num">{n.n}</td>
                <td>
                  {FORMS.filter((f) => n[f] > 0)
                    .map((f) => t.times(t.forms[f], n[f]))
                    .join(' · ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

