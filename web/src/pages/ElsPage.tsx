import { Link } from 'react-router'
import { useEls } from '../api/hooks'
import type { ElsControlKey, ElsKnown, ElsResponse, ElsScope } from '../api/types'
import { Segmented } from '../components/Controls'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { unitLabel } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const CONTROLS: ElsControlKey[] = ['letters', 'verses', 'blocks']

/** Letters at equal skips (§16.62): names at equal skips in the Torah and in Genesis against
 * their exact expectation, shuffled letters, shuffled verses and stretches of the other books;
 * the tradition's sequences at the start of each book. Counts against controls, not codes. */
export function ElsPage() {
  const { m } = useLocale()
  const t = m.els
  const res = useEls()
  return (
    <div className="page els-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.scopes.length ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Scope data={res.data} />
          {res.data.known.length > 0 && <Known known={res.data.known} />}
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.els
  return <span className={`dlg-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.verdict.holds : t.verdict.fails}</span>
}

function Scope({ data }: { data: ElsResponse }) {
  const { m, locale } = useLocale()
  const t = m.els
  const [params, update] = useQueryParams()
  const scope = data.scopes.find((s) => s.key === params.get('scope')) ?? data.scopes[0]
  const meta = data.meta
  const alpha = meta.alpha ?? 0.05
  return (
    <section aria-label={t.scopes[scope.key] ?? scope.key}>
      {data.scopes.length > 1 && (
        <Segmented
          label={t.scope}
          value={scope.key}
          onChange={(x) => update({ scope: x === data.scopes[0].key ? null : x }, false)}
          options={data.scopes.map((s) => ({ value: s.key, label: t.scopes[s.key] ?? s.key }))}
        />
      )}
      <p>
        <Verdict holds={scope.holds} /> {t.summary(meta.terms ?? scope.terms.length, meta.min_skip ?? 2, meta.max_skip ?? 0, scope.hits, scope.letters, scope.expected, scope.r)}
      </p>
      <p className="muted small">{t.claim(alpha)}</p>
      <h2>{t.controlsTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.controlsTitle}>
        <table className="change-table els-table">
          <thead>
            <tr>
              <th>{t.ccols.control}</th>
              <th>{t.ccols.n}</th>
              <th>{t.ccols.mean}</th>
              <th>{t.ccols.p}</th>
              <th>{t.ccols.verdict}</th>
            </tr>
          </thead>
          <tbody>
            {CONTROLS.flatMap((c) => {
              const x = scope.controls[c]
              return x
                ? [
                    <tr key={c}>
                      <td>{t.controls[c]}</td>
                      <td>{x.n}</td>
                      <td>{t.range(x.mean, x.q05, x.q95)}</td>
                      <td>{t.p(x.p)}</td>
                      <td>
                        <Verdict holds={x.p > alpha} />
                      </td>
                    </tr>,
                  ]
                : []
            })}
          </tbody>
        </table>
      </div>
      <Strip scope={scope} />
      {scope.blocks.length > 0 && (
        <>
          <h3>{t.blocksTitle}</h3>
          <ul className="els-blocks">
            {scope.blocks.map((b) => (
              <li key={b.block}>
                <Link to={unitLink(`v:${b.first_vid}`)}>{t.block(locale === 'he' ? b.label_he : b.label_en, b.r)}</Link>
              </li>
            ))}
          </ul>
        </>
      )}
      <Terms scope={scope} />
    </section>
  )
}

const W = 560
const ROW = 34
const PAD = { l: 120, r: 16, t: 22, b: 26 }

/** Each control draw's R as a dot, one row per control, with the text's R as a line. */
function Strip({ scope }: { scope: ElsScope }) {
  const t = useLocale().m.els
  const rows = CONTROLS.filter((c) => scope.controls[c]?.values.length)
  if (!rows.length) return null
  const all = [scope.r, ...rows.flatMap((c) => scope.controls[c]!.values)]
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const span = hi - lo || 1
  const x = (v: number) => PAD.l + ((v - lo) / span) * (W - PAD.l - PAD.r)
  const H = PAD.t + rows.length * ROW + PAD.b
  return (
    <figure className="els-strip" dir="ltr">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.stripLabel(scope.r)}>
        {rows.map((c, i) => {
          const y = PAD.t + i * ROW + ROW / 2
          const values = scope.controls[c]!.values
          return (
            <g key={c}>
              <text className="els-row" x={PAD.l - 8} y={y + 4} textAnchor="end">
                {t.stripRows[c]}
              </text>
              <line className="els-axis" x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} />
              {values.map((v, j) => (
                // a little vertical jitter, by draw, so dots on one value stay apart
                <circle key={j} className="els-dot" cx={x(v)} cy={y + (((j * 7) % 11) - 5) * 1.4} r={2.4} />
              ))}
            </g>
          )
        })}
        <line className="els-text" x1={x(scope.r)} x2={x(scope.r)} y1={PAD.t - 6} y2={H - PAD.b + 4} />
        {/* the word and the number apart, so neither direction reorders them */}
        <text className="els-text-label" x={x(scope.r) - 4} y={PAD.t - 9} textAnchor="end">
          {t.stripText}
        </text>
        <text className="els-text-label" x={x(scope.r) + 4} y={PAD.t - 9}>
          {t.r(scope.r)}
        </text>
        <text className="els-tick" x={PAD.l} y={H - 6}>
          {t.r(lo)}
        </text>
        <text className="els-tick" x={W - PAD.r} y={H - 6} textAnchor="end">
          {t.r(hi)}
        </text>
      </svg>
    </figure>
  )
}

function Terms({ scope }: { scope: ElsScope }) {
  const t = useLocale().m.els
  return (
    <>
      <h2>{t.termsTitle}</h2>
      <p className="muted small">{t.termsLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.termsTitle}>
        <table className="change-table els-table els-terms">
          <thead>
            <tr>
              <th>{t.tcols.term}</th>
              <th>{t.tcols.fwd}</th>
              <th>{t.tcols.back}</th>
              <th>{t.tcols.hits}</th>
              <th>{t.tcols.expected}</th>
              <th>{t.tcols.ratio}</th>
              <th>{t.tcols.letters}</th>
              <th>{t.tcols.p}</th>
              <th>{t.tcols.verses}</th>
              <th>{t.tcols.blocks}</th>
            </tr>
          </thead>
          <tbody>
            {scope.terms.map((x) => (
              <tr key={x.term}>
                <td>
                  <span dir="rtl" lang="he" className="he">
                    {x.term}
                  </span>
                </td>
                <td>{t.num(x.forward)}</td>
                <td>{t.num(x.backward)}</td>
                <td>{t.num(x.hits)}</td>
                <td>{t.num(x.expected)}</td>
                <td>{t.ratio(Math.exp(x.log_ratio))}</td>
                <td>{t.lettersRange(x.letters_q05, x.letters_q95)}</td>
                <td>{t.p(x.letters_p)}</td>
                <td>{t.num(x.verses_mean)}</td>
                <td>{x.blocks_log_ratio == null ? '–' : t.ratio(Math.exp(x.blocks_log_ratio))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

function Known({ known }: { known: ElsKnown[] }) {
  const { m, locale } = useLocale()
  const t = m.els
  return (
    <section id="known" aria-label={t.knownTitle}>
      <h2>{t.knownTitle}</h2>
      <p className="muted small">{t.knownLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownTitle}>
        <table className="change-table els-table">
          <thead>
            <tr>
              <th>{t.kcols.verse}</th>
              <th>{t.kcols.term}</th>
              <th>{t.kcols.skip}</th>
              <th>{t.kcols.found}</th>
              <th>{t.kcols.torah}</th>
            </tr>
          </thead>
          <tbody>
            {known.map((k) => (
              <tr key={`${k.verse.verse_id}-${k.term}`}>
                <td>
                  <Link to={unitLink(`v:${k.verse.verse_id}`)}>{unitLabel(k.verse, locale)}</Link>
                </td>
                <td>
                  <span dir="rtl" lang="he" className="he">
                    {k.term}
                  </span>
                </td>
                <td>{k.skip}</td>
                <td>
                  <Verdict holds={k.found} /> {t.found(k.offset ?? null)}
                </td>
                <td>{t.inTorah(k.in_torah, k.expected)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
