import { Link } from 'react-router'
import { useChronology } from '../api/hooks'
import type { ChronEvent, ChronologyResponse, ChronSync, Verse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'

const RULES = ['accession', 'non-accession'] as const
const MARKS = ['flood', 'exodus'] as const

/** The text's own chronology (§16.70): years from Adam read from the verses, the two kingdoms
 * on one count with their synchronisms, Genesis 5's numbers, and the checks. */
export function ChronologyPage() {
  const { m } = useLocale()
  const t = m.ch
  const res = useChronology()
  const d = res.data
  return (
    <div className="page chronology-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <FromAdam d={d} />
          <Kingdoms d={d} />
          <Digits d={d} />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.ch
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

/** Labels of events: a person's birth or death by their Hebrew name, else the catalog's. */
function useLabels(d: ChronologyResponse) {
  const t = useLocale().m.ch
  const names = new Map(d.lives.map((l) => [l.person, l.name]))
  return (id: string) => {
    const [person, death] = id.split('.')
    const name = names.get(person)
    if (name) return death ? t.died(name) : t.born(name)
    return t.events[id] ?? id
  }
}

function rulesText(d: ChronologyResponse, t: ReturnType<typeof useLocale>['m']['ch']) {
  return t.rulesPair(t.rule[d.rules.judah] ?? d.rules.judah, t.rule[d.rules.israel] ?? d.rules.israel)
}

function Checks({ d }: { d: ChronologyResponse }) {
  const t = useLocale().m.ch
  const label = useLabels(d)
  return (
    <section aria-labelledby="ch-checks">
      <h2 id="ch-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(d.known.map((k) => t.known.row(label(k.event), k.year, k.expected)).join('; '))}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.syncs.title} <Verdict holds={d.holds} />
          </h3>
          <p>{t.syncs.text(d.agree, d.intervals, d.expected, d.p, rulesText(d, t))}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.digits.title} <Verdict holds={d.digits.holds} />
          </h3>
          <p>{t.digits.text(d.digits.hits, d.digits.n, d.digits.share, d.digits.rest_share, d.digits.p)}</p>
        </article>
      </div>
    </section>
  )
}

function VerseLink({ v }: { v: Verse }) {
  const { locale } = useLocale()
  return (
    <Link className="verse-ref" to={unitLink(`v:${v.verse_id}`)}>
      {locale === 'he' ? v.ref_he : v.ref}
    </Link>
  )
}

/** The words of a verse the number was read from. */
function NumberWords({ e }: { e: { verse: Verse | null; tok_first: number | null; tok_last: number | null } }) {
  if (!e.verse || e.tok_first === null || e.tok_last === null) return null
  return (
    <span className="he" dir="rtl" lang="he">
      {e.verse.display_tokens.slice(e.tok_first, e.tok_last + 1).join(' ')}
    </span>
  )
}

function FromAdam({ d }: { d: ChronologyResponse }) {
  const t = useLocale().m.ch
  const label = useLabels(d)
  const how = (e: ChronEvent) => (e.from_event === null || e.value === null ? t.start : (e.sign < 0 ? t.minus : t.plus)(label(e.from_event), e.value))
  const used = new Map(d.events.filter((e) => e.used).map((e) => [e.event, e.year]))
  const conflicts = d.events.filter((e) => e.conflict)
  return (
    <section aria-labelledby="ch-adam">
      <h2 id="ch-adam">{t.adamTitle}</h2>
      <p className="muted small">{t.adamLede}</p>
      <div className="ch-scroll" tabIndex={0} role="region" aria-label={t.livesLabel}>
        <Lives d={d} />
      </div>
      {conflicts.length > 0 && (
        <>
          <h3>{t.conflictsTitle}</h3>
          <ul className="ch-conflicts">
            {conflicts.map((e) => (
              <li key={e.seq}>
                {t.conflict(label(e.event), used.get(e.event) ?? e.year, e.year, how(e))} {e.verse && <VerseLink v={e.verse} />}
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="ch-adam">
        <table className="change-table ch-events">
          <thead>
            <tr>
              <th scope="col">{t.cols.event}</th>
              <th scope="col" className="num">
                {t.cols.year}
              </th>
              <th scope="col">{t.cols.how}</th>
              <th scope="col">{t.cols.number}</th>
              <th scope="col">{t.cols.verse}</th>
            </tr>
          </thead>
          <tbody>
            {d.events.map((e) => (
              <tr key={e.seq} className={e.conflict ? 'ch-conflict' : e.used ? undefined : 'ch-check'}>
                <th scope="row">
                  {label(e.event)}
                  {!e.used && (
                    <>
                      {' '}
                      <span className="type-tag">{e.conflict ? t.conflictTag : t.checkTag}</span>
                    </>
                  )}
                </th>
                <td className="num">{e.year}</td>
                <td>{how(e)}</td>
                <td>
                  <NumberWords e={e} />
                </td>
                <td>{e.verse && <VerseLink v={e.verse} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

const LW = 760
const LL = 84
const ROW = 18

/** One bar per life on the years from Adam, with the Flood and the Exodus marked. */
function Lives({ d }: { d: ChronologyResponse }) {
  const t = useLocale().m.ch
  const label = useLabels(d)
  const lives = d.lives
  const marks = MARKS.map((id) => ({ id, year: d.events.find((e) => e.used && e.event === id)?.year })).filter((x): x is { id: (typeof MARKS)[number]; year: number } => x.year !== undefined)
  const top = Math.max(...lives.map((l) => l.died ?? l.born), ...marks.map((x) => x.year))
  const max = Math.ceil(top / 500) * 500
  const x = (y: number) => LL + (y / max) * (LW - LL - 12)
  const h = 22 + lives.length * ROW + 26
  const ticks = Array.from({ length: max / 500 + 1 }, (_, i) => i * 500)
  return (
    <svg className="ch-chart" viewBox={`0 0 ${LW} ${h}`} role="img" aria-label={t.livesLabel}>
      {ticks.map((y) => (
        <g key={y}>
          <line className="ch-grid" x1={x(y)} x2={x(y)} y1={18} y2={h - 22} />
          <text className="ch-axis" x={x(y)} y={h - 8} textAnchor="middle">
            {y}
          </text>
        </g>
      ))}
      {marks.map((mk) => (
        <g key={mk.id}>
          <line className="ch-mark" x1={x(mk.year)} x2={x(mk.year)} y1={14} y2={h - 22} />
          <text className="ch-mark-label" x={x(mk.year)} y={11} textAnchor={x(mk.year) > LW - 90 ? 'end' : 'middle'}>
            {`${label(mk.id)} ${mk.year}`}
          </text>
        </g>
      ))}
      {lives.map((l, i) => {
        const y = 22 + i * ROW
        return (
          <g key={l.person} className="ch-life">
            <title>{t.livesTitle(l.name, l.born, l.died)}</title>
            <text className="ch-name" x={LL - 6} y={y + 9} textAnchor="end" lang="he">
              {l.name}
            </text>
            {l.died === null ? <circle className="ch-bar" cx={x(l.born)} cy={y + 5} r={4} /> : <rect className="ch-bar" x={x(l.born)} y={y + 1} width={Math.max(2, x(l.died) - x(l.born))} height={8} rx={2} />}
            <rect className="ch-hit" x={LL} y={y - 2} width={LW - LL} height={ROW} />
          </g>
        )
      })}
    </svg>
  )
}

const KW = 760
const KL = 64
const JY = 22
const BH = 24
const IY = 112

function Kingdoms({ d }: { d: ChronologyResponse }) {
  const t = useLocale().m.ch
  const names = new Map(d.kings.map((k) => [k.king, k.name]))
  const offsets = d.syncs.map((s) => s.t_judah - s.t_israel)
  const statement = (s: ChronSync) => t.syncStatement(names.get(s.king) ?? s.king, s.year, names.get(s.of) ?? s.of)
  const best = `${d.rules.judah}/${d.rules.israel}`
  const tradition = d.tradition.destruction
  return (
    <section aria-labelledby="ch-kings">
      <h2 id="ch-kings">{t.kingsTitle}</h2>
      <p className="muted small">{t.kingsLede}</p>
      <div className="ch-scroll" tabIndex={0} role="region" aria-label={t.kingsLabel}>
        <KingsChart d={d} statement={statement} />
      </div>
      <div className="dv-legend small">
        <span>
          <svg width="22" height="10" aria-hidden="true">
            <line className="ch-sync agrees" x1="1" y1="5" x2="21" y2="5" />
          </svg>{' '}
          {t.legendAgrees}
        </span>
        <span>
          <svg width="22" height="10" aria-hidden="true">
            <line className="ch-sync differs" x1="1" y1="5" x2="21" y2="5" />
          </svg>{' '}
          {t.legendDiffers}
        </span>
        <span>
          <svg width="22" height="10" aria-hidden="true">
            <line className="ch-sync first" x1="1" y1="5" x2="21" y2="5" />
          </svg>{' '}
          {t.legendFirst}
        </span>
      </div>
      <p className="small">{t.ends(d.division, d.ends.judah, d.ends.israel, tradition)}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.kingsLabel}>
        <table className="change-table ch-syncs">
          <thead>
            <tr>
              <th scope="col">{t.cols.verse}</th>
              <th scope="col">{t.cols.statement}</th>
              <th scope="col" className="num">
                {t.cols.judah}
              </th>
              <th scope="col" className="num">
                {t.cols.israel}
              </th>
              <th scope="col">{t.cols.interval}</th>
            </tr>
          </thead>
          <tbody>
            {d.syncs.map((s, i) => (
              <tr key={s.seq} className={s.agrees === false ? 'ch-conflict' : undefined}>
                <td>
                  <VerseLink v={s.verse} />
                </td>
                <td>{statement(s)}</td>
                <td className="num">{s.t_judah}</td>
                <td className="num">{s.t_israel}</td>
                <td>{s.agrees === null ? t.first : s.agrees ? t.agrees : t.differs(offsets[i] - offsets[i - 1])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>{t.rulesTitle}</h3>
      <p className="muted small">{t.rulesLede}</p>
      <table className="change-table ch-rules">
        <thead>
          <tr>
            <th scope="col">{t.cols.rules}</th>
            <th scope="col" className="num">
              {t.cols.agree}
            </th>
          </tr>
        </thead>
        <tbody>
          {RULES.flatMap((j) =>
            RULES.map((i) => (
              <tr key={`${j}/${i}`} className={`${j}/${i}` === best ? 'selected' : undefined}>
                <th scope="row">
                  {t.rule[j]} / {t.rule[i]}
                </th>
                <td className="num">
                  {d.rule_counts[`${j}/${i}`] ?? 0} / {d.intervals}
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
      <details className="ch-reigns">
        <summary>{t.kingsTable}</summary>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.kingsTable}>
          <table className="change-table">
            <thead>
              <tr>
                <th scope="col">{t.cols.king}</th>
                <th scope="col">{t.cols.reign}</th>
                <th scope="col" className="num">
                  {t.cols.start}
                </th>
                <th scope="col" className="num">
                  {t.cols.am}
                </th>
                <th scope="col">{t.cols.verse}</th>
              </tr>
            </thead>
            <tbody>
              {d.kings.map((k) => (
                <tr key={k.king}>
                  <th scope="row">
                    <span className="he" dir="rtl" lang="he">
                      {k.name}
                    </span>{' '}
                    <span className="muted small">{t.kingdom[k.kingdom]}</span>
                  </th>
                  <td>{k.short ? t.short : t.years(k.reign)}</td>
                  <td className="num">{k.start}</td>
                  <td className="num">{k.am}</td>
                  <td>
                    <VerseLink v={k.verse} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}

/** The reigns of the two kingdoms from the division, and a line for each synchronism. */
function KingsChart({ d, statement }: { d: ChronologyResponse; statement: (s: ChronSync) => string }) {
  const { m, locale } = useLocale()
  const t = m.ch
  const end = Math.max(...d.kings.map((k) => k.start + Math.max(k.reign, 1)))
  const max = Math.ceil(end / 50) * 50
  const x = (y: number) => KL + (y / max) * (KW - KL - 12)
  const h = IY + BH + 30
  const ticks = Array.from({ length: max / 50 + 1 }, (_, i) => i * 50)
  const rowY = (k: string) => (k === 'judah' ? JY : IY)
  return (
    <svg className="ch-chart" viewBox={`0 0 ${KW} ${h}`} role="img" aria-label={t.kingsLabel}>
      {ticks.map((y) => (
        <g key={y}>
          <line className="ch-grid" x1={x(y)} x2={x(y)} y1={JY - 4} y2={IY + BH + 4} />
          <text className="ch-axis" x={x(y)} y={h - 8} textAnchor="middle">
            {y}
          </text>
        </g>
      ))}
      {(['judah', 'israel'] as const).map((k) => (
        <text key={k} className="ch-row-label" x={KL - 8} y={rowY(k) + BH / 2 + 4} textAnchor="end">
          {t.kingdom[k]}
        </text>
      ))}
      {d.kings.map((k) => {
        const x0 = x(k.start)
        const w = Math.max(2, x(k.start + (k.short ? 0.5 : k.reign)) - x0)
        const y = rowY(k.kingdom)
        return (
          <g key={k.king} className={`ch-reign ${k.kingdom}${k.seq % 2 ? ' odd' : ''}`}>
            <title>{`${k.name}: ${k.short ? t.short : t.years(k.reign)} (${locale === 'he' ? k.verse.ref_he : k.verse.ref})`}</title>
            <rect x={x0} y={y} width={w} height={BH} rx={2} />
            {w >= k.name.length * 7 + 4 && (
              <text className="ch-reign-name" x={x0 + w / 2} y={y + BH / 2 + 4} textAnchor="middle" lang="he">
                {k.name}
              </text>
            )}
          </g>
        )
      })}
      {d.syncs.map((s) => (
        <line key={s.seq} className={`ch-sync ${s.agrees === null ? 'first' : s.agrees ? 'agrees' : 'differs'}`} x1={x(s.t_judah + 0.5)} y1={JY + BH} x2={x(s.t_israel + 0.5)} y2={IY}>
          <title>{t.syncTitle(statement(s), locale === 'he' ? s.verse.ref_he : s.verse.ref, s.t_judah, s.t_israel)}</title>
        </line>
      ))}
    </svg>
  )
}

function Digits({ d }: { d: ChronologyResponse }) {
  const t = useLocale().m.ch
  const g = d.digits
  const ends = new Set(d.digits_ends)
  const rest = Object.values(g.rest_by_digit).reduce((a, b) => a + b, 0) || 1
  return (
    <section aria-labelledby="ch-digits">
      <h2 id="ch-digits">{t.digitsTitle}</h2>
      <p className="muted small">{t.digitsLede(g.n, d.digits_min)}</p>
      <table className="change-table ch-digits">
        <thead>
          <tr>
            <th scope="col" className="num">
              {t.digit}
            </th>
            <th scope="col" className="num">
              {t.gen5}
            </th>
            <th scope="col" className="num">
              {t.rest}
            </th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 10 }, (_, i) => (
            <tr key={i} className={ends.has(i) ? 'ch-end' : undefined}>
              <th scope="row" className="num">
                {i}
              </th>
              <td className="num">{g.by_digit[String(i)] ?? 0}</td>
              <td className="num">{Math.round(((g.rest_by_digit[String(i)] ?? 0) / rest) * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="small">
        {t.uniform(g.uniform_p)} {g.compare_share !== null && t.compare(g.compare_share, g.compare_n)}
      </p>
      <h3>{t.numbersTitle}</h3>
      <ul className="ch-numbers">
        {d.numbers.map((n, i) => (
          <li key={i} className={ends.has(n.value % 10) ? undefined : 'ch-odd-end'}>
            <b>{n.value}</b> <NumberWords e={n} /> <VerseLink v={n.verse} />
          </li>
        ))}
      </ul>
    </section>
  )
}
