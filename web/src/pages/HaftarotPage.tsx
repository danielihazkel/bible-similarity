import { Link } from 'react-router'
import { useHaftarot } from '../api/hooks'
import type { Haftarah, HaftarotResponse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

const MODES = ['lexical', 'semantic', 'fused'] as const

/** Haftarot (§16.69): each parasha's reading from the Prophets, where the systems rank it among
 * all the chapters of the Prophets, and the checks. */
export function HaftarotPage() {
  const { m } = useLocale()
  const t = m.hf
  const res = useHaftarot()
  const d = res.data
  return (
    <div className="page haftarot-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Modes d={d} />
          <Parashot d={d} />
          <p className="muted small">{t.credit}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.hf
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: HaftarotResponse }) {
  const { m, locale } = useLocale()
  const t = m.hf
  const byName = new Map(d.parashot.map((p) => [p.parasha, p]))
  const ranks = d.known
    .map((k) => {
      const p = byName.get(`p:${k.parasha}`)
      return t.known.rank(p ? (locale === 'he' ? p.label_he : p.label_en) : k.parasha, k.rank)
    })
    .join(', ')
  return (
    <section aria-labelledby="hf-checks">
      <h2 id="hf-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.claim.title} <Verdict holds={d.holds} />
          </h3>
          <p>{t.claim.text(d.thematic, d.thematic_pct, d.shuffled_pct, d.p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.calendar.title} <Verdict holds={d.calendar_holds} />
          </h3>
          <p>{t.calendar.text(d.calendar_pct, d.thematic_pct, d.calendar_p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(d.known_rank, ranks)}</p>
        </article>
      </div>
    </section>
  )
}

function Modes({ d }: { d: HaftarotResponse }) {
  const t = useLocale().m.hf
  return (
    <section aria-labelledby="hf-modes">
      <h2 id="hf-modes">{t.modesTitle}</h2>
      <p className="muted small">{t.modesLede(d.thematic)}</p>
      <table className="change-table hf-modes">
        <thead>
          <tr>
            <th scope="col">{t.cols.system}</th>
            <th scope="col" className="num">
              {t.cols.mrr}
            </th>
            <th scope="col" className="num">
              {t.cols.hits(d.list)}
            </th>
            <th scope="col" className="num">
              {t.cols.median}
            </th>
            <th scope="col" className="num">
              {t.cols.pct}
            </th>
          </tr>
        </thead>
        <tbody>
          {MODES.map((mode) => {
            const e = d.modes[mode]
            if (!e) return null
            return (
              <tr key={mode}>
                <th scope="row">{t.modes[mode]}</th>
                <td className="num">{e.mrr.toFixed(3)}</td>
                <td className="num">
                  {e.hits} / {d.thematic}
                </td>
                <td className="num">{e.median}</td>
                <td className="num">{Math.round(e.pct * 100)}%</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}

function Parashot({ d }: { d: HaftarotResponse }) {
  const { m, locale } = useLocale()
  const t = m.hf
  const [params, update] = useQueryParams()
  const sel = d.parashot.find((p) => p.parasha === params.get('p'))
  const name = (p: Haftarah) => (locale === 'he' ? p.label_he : p.label_en)
  return (
    <section aria-labelledby="hf-parashot">
      <h2 id="hf-parashot">{t.cols.parasha}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="hf-parashot">
        <table className="change-table hf-table">
          <thead>
            <tr>
              <th scope="col" className="num">
                {t.cols.num}
              </th>
              <th scope="col">{t.cols.parasha}</th>
              <th scope="col">{t.cols.haftarah}</th>
              <th scope="col" className="num">
                {t.cols.rank}
              </th>
            </tr>
          </thead>
          <tbody>
            {d.parashot.map((p) => (
              <tr key={p.parasha} className={[p.rank_fused <= d.list ? 'hf-top' : '', sel?.parasha === p.parasha ? 'selected' : ''].filter(Boolean).join(' ') || undefined}>
                <td className="num">{p.num}</td>
                <td>
                  <button type="button" className="linkish" aria-label={t.showList(name(p))} aria-pressed={sel?.parasha === p.parasha} onClick={() => update({ p: sel?.parasha === p.parasha ? null : p.parasha }, false)}>
                    {name(p)}
                  </button>
                </td>
                <td>
                  {p.haft}
                  {p.theme && (
                    <>
                      {' '}
                      <span className="type-tag" title={t.calendarHint}>
                        {t.calendarTag[p.theme]}
                      </span>
                    </>
                  )}
                  {p.seph && <div className="muted small">{t.sephardi(p.seph)}</div>}
                </td>
                <td className="num">{t.of(p.rank_fused, p.rank_lexical, p.rank_semantic)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sel && <ChapterList p={sel} onClose={() => update({ p: null }, false)} />}
    </section>
  )
}

function ChapterList({ p, onClose }: { p: Haftarah; onClose: () => void }) {
  const { m, locale } = useLocale()
  const t = m.hf
  const name = locale === 'he' ? p.label_he : p.label_en
  return (
    <section className="hf-list" aria-labelledby="hf-list">
      <h3 id="hf-list">{t.listTitle(name)}</h3>
      <p className="muted small">{t.listLede(p.haft)}</p>
      <ol className="hf-chapters">
        {p.top.map((c) => (
          <li key={c.unit_id} className={c.haftarah ? 'hf-hit' : undefined}>
            <Link to={unitLink(c.unit_id)}>{locale === 'he' ? c.label_he : c.label_en}</Link>{' '}
            <span className="muted small">{t.of(c.rank, c.lex_rank, c.sem_rank)}</span>
            {c.haftarah && <span className="type-tag">{t.inHaftarah}</span>}{' '}
            <Link className="small" to={`/compare?a=${encodeURIComponent(p.parasha)}&b=${encodeURIComponent(c.unit_id)}`}>
              {t.compare}
            </Link>
          </li>
        ))}
      </ol>
      <button type="button" className="linkish small" onClick={onClose}>
        {t.close}
      </button>
    </section>
  )
}
