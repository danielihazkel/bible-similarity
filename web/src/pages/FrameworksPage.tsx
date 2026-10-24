import { Link } from 'react-router'
import { useFrameworks } from '../api/hooks'
import type { FrameworkKing, FrameworksResponse, SlotHit } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

/** The narrative frameworks (§16.71): the judges' cycle slot by slot, every king's verdict and
 * regnal slots, and the checks. */
export function FrameworksPage() {
  const { m } = useLocale()
  const t = m.fw
  const res = useFrameworks()
  const d = res.data
  return (
    <div className="page frameworks-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Cycle d={d} />
          <Kings d={d} />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.fw
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: FrameworksResponse }) {
  const t = useLocale().m.fw
  const missing = (ep: string) => {
    const k = d.known_cycle.find((x) => x.episode === ep)
    return k && k.missing.length ? k.missing.map((s) => t.slot[s] ?? s).join(', ') : t.none
  }
  const names = new Map(d.kings.map((k) => [k.king, k.name]))
  const tag = (v: string | null) => (v ? (t.verdictTag[v] ?? v) : t.noVerdict)
  const found = d.known_verdicts.filter((k) => k.holds).length
  return (
    <section aria-labelledby="fw-checks">
      <h2 id="fw-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.cycle.title} <Verdict holds={d.cycle_holds} />
          </h3>
          <p>{t.cycle.text(d.rho, d.episodes.length, d.cycle_p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.cycleKnown.title} <Verdict holds={d.known_cycle_holds} />
          </h3>
          <p>{t.cycleKnown.text(missing('othniel'), missing('samson'))}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.verdicts.title} <Verdict holds={d.verdict_holds} />
          </h3>
          <p>{t.verdicts.text(d.verdicts, d.within_all ?? 0, d.between ?? 0, d.verdict_p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.verdictsKnown.title} <Verdict holds={d.known_verdicts_holds} />
          </h3>
          <p>
            {t.verdictsKnown.text(
              found,
              d.known_verdicts.length,
              d.known_verdicts.map((k) => t.verdictsKnown.row(`⁨${names.get(k.king) ?? k.king}⁩`, tag(k.expected), tag(k.found))).join(', '),
            )}
          </p>
        </article>
      </div>
    </section>
  )
}

function Hit({ h }: { h: SlotHit }) {
  const { m, locale } = useLocale()
  const t = m.fw
  if (h.verse_id === null) return <span className="muted" aria-label={t.absent}>—</span>
  const ref = (locale === 'he' ? h.ref_he : h.ref) ?? ''
  return (
    <Link className="fw-hit" to={unitLink(`v:${h.verse_id}`)} aria-label={`${t.slot[h.slot] ?? h.slot}: ${t.found(ref)}`} title={ref}>
      ✓
    </Link>
  )
}

function Cycle({ d }: { d: FrameworksResponse }) {
  const { m, locale } = useLocale()
  const t = m.fw
  return (
    <section aria-labelledby="fw-cycle">
      <h2 id="fw-cycle">{t.cycleTitle}</h2>
      <p className="muted small">
        {t.cycleLede(d.open)} {t.formulas}
      </p>
      <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="fw-cycle">
        <table className="change-table fw-cycle">
          <thead>
            <tr>
              <th scope="col">{t.episode}</th>
              {d.slots.map((s) => (
                <th key={s} scope="col" className="fw-slot">
                  {t.slot[s] ?? s}
                </th>
              ))}
              <th scope="col" className="num">
                {t.share}
              </th>
            </tr>
          </thead>
          <tbody>
            {d.episodes.map((e) => (
              <tr key={e.episode}>
                <th scope="row">
                  <span className="he" lang="he" dir="rtl">
                    {e.judge}
                  </span>{' '}
                  <span className="muted small">{locale === 'he' ? e.ref_he : e.ref}</span>
                </th>
                {e.slots.map((h) => (
                  <td key={h.slot} className="fw-slot">
                    <Hit h={h} />
                  </td>
                ))}
                <td className="num">
                  {e.n_slots} / {d.slots.length}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Kings({ d }: { d: FrameworksResponse }) {
  const t = useLocale().m.fw
  const [params, update] = useQueryParams()
  const sel = d.kings.find((k) => k.king === params.get('k'))
  const cols = ['verdict_vid', ...d.regnal]
  return (
    <section aria-labelledby="fw-kings">
      <h2 id="fw-kings">{t.kingsTitle}</h2>
      <p className="muted small">{t.kingsLede}</p>
      <p className="small">{t.wording(d.within.judah, d.within.israel, d.between)}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="fw-kings">
        <table className="change-table fw-kings">
          <thead>
            <tr>
              <th scope="col">{t.king}</th>
              <th scope="col">{t.verdict}</th>
              {d.regnal.map((s) => (
                <th key={s} scope="col" className="fw-slot">
                  {t.slot[s] ?? s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.kings.map((k) => (
              <tr key={k.king} className={[`fw-${k.kingdom}`, sel?.king === k.king ? 'selected' : ''].filter(Boolean).join(' ')}>
                <th scope="row">
                  <button type="button" className="linkish" aria-label={t.showKing(k.name)} aria-pressed={sel?.king === k.king} onClick={() => update({ k: sel?.king === k.king ? null : k.king }, false)}>
                    <span className="he" lang="he" dir="rtl">
                      {k.name}
                    </span>
                  </button>{' '}
                  <span className="muted small">{t.kingdom[k.kingdom]}</span>
                </th>
                <td>{k.verdict ? <span className={`type-tag fw-${k.verdict}`}>{t.verdictTag[k.verdict]}</span> : <span className="muted small">{t.noVerdict}</span>}</td>
                {k.slots.map((h) => (
                  <td key={h.slot} className="fw-slot">
                    <Hit h={h} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sel && <KingPanel k={sel} onClose={() => update({ k: null }, false)} />}
      <h3>{t.byKingdomTitle}</h3>
      <p className="muted small">{t.byKingdomLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.byKingdomTitle}>
        <table className="change-table fw-by-kingdom">
          <thead>
            <tr>
              <th scope="col" />
              <th scope="col" className="num">
                {t.kingdom.judah}
              </th>
              <th scope="col" className="num">
                {t.kingdom.israel}
              </th>
            </tr>
          </thead>
          <tbody>
            {cols.map((c) => (
              <tr key={c}>
                <th scope="row">{t.slot[c] ?? c}</th>
                {(['judah', 'israel'] as const).map((k) => (
                  <td key={k} className="num">
                    {Math.round((d.by_kingdom[k]?.[c] ?? 0) * 100)}%
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function KingPanel({ k, onClose }: { k: FrameworkKing; onClose: () => void }) {
  const { m, locale } = useLocale()
  const t = m.fw
  const v = k.verdict_verse
  return (
    <section className="hf-list fw-panel" aria-labelledby="fw-panel">
      <h3 id="fw-panel">{t.kingTitle(`⁨${k.name}⁩`)}</h3>
      {v ? (
        <>
          <p>
            <Link className="verse-ref" to={unitLink(`v:${v.verse_id}`)}>
              {locale === 'he' ? v.ref_he : v.ref}
            </Link>{' '}
            {k.verdict && <span className={`type-tag fw-${k.verdict}`}>{t.verdictTag[k.verdict]}</span>}
          </p>
          <p className="hit-text">
            <HebrewText verse={v} />
          </p>
        </>
      ) : (
        <p className="muted">{t.noVerdict}</p>
      )}
      <button type="button" className="linkish small" onClick={onClose}>
        {t.close}
      </button>
    </section>
  )
}
