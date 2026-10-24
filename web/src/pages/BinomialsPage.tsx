import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { useBinomialOccurrences, useBinomials } from '../api/hooks'
import type { Binomial, BinomialOccurrence, BinomialsResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { useLocale } from '../context/localeContext'
import type { BnOrder, BnShow } from '../i18n/pages/binomials'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

/** Word pairs (§16.72): the recurring pairs joined by ו, how fixed each order is, its words'
 * lengths and its turns by period, a pair's occurrences, and the checks. */
export function BinomialsPage() {
  const { m } = useLocale()
  const t = m.bn
  const res = useBinomials()
  const d = res.data
  return (
    <div className="page binomials-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Pairs d={d} />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.bn
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: BinomialsResponse }) {
  const t = useLocale().m.bn
  const [sky, man] = d.known
  return (
    <section aria-labelledby="bn-checks">
      <h2 id="bn-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.short.title} <Verdict holds={d.short_holds} />
          </h3>
          <p>{t.short.text(d.letters.shorter_first, d.letters.differ, d.letters.p, d.syllables.shorter_first, d.syllables.differ, d.syllables.p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.late.title} <Verdict holds={d.late_holds} />
          </h3>
          <p>{t.late.text(d.rate_early, d.rate_late, d.late_p, d.without_known.p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(sky?.share ?? null, man?.share ?? null, d.known_late.share_early, d.known_late.share_late)}</p>
        </article>
      </div>
    </section>
  )
}

const pairText = (b: Binomial) => `${b.first_form} ו${b.second_form}`
const turned = (b: Binomial) => (b.n - b.n_own) / b.n

function Pairs({ d }: { d: BinomialsResponse }) {
  const t = useLocale().m.bn
  const [params, update] = useQueryParams()
  const show: BnShow = params.get('show') === 'both' ? 'both' : 'all'
  const order: BnOrder = params.get('order') === 'turned' ? 'turned' : 'common'
  const sel = d.items.find((b) => b.pair === params.get('pair'))
  const shown = d.items.filter((b) => show === 'all' || b.n_own < b.n)
  if (order === 'turned') shown.sort((a, b) => turned(b) - turned(a) || b.n - a.n)
  return (
    <section aria-labelledby="bn-list">
      <h2 id="bn-list">{t.listTitle(d.binomials, d.min_pairs)}</h2>
      <div className="controls">
        <Segmented<BnShow> label={t.show.label} value={show} options={(['all', 'both'] as const).map((v) => ({ value: v, label: t.show[v] }))} onChange={(v) => update({ show: v === 'all' ? null : v })} />
        <Segmented<BnOrder> label={t.order.label} value={order} options={(['common', 'turned'] as const).map((v) => ({ value: v, label: t.order[v] }))} onChange={(v) => update({ order: v === 'common' ? null : v })} />
      </div>
      <p className="muted small">{t.limits}</p>
      {sel && <PairPanel b={sel} examples={d.examples} onClose={() => update({ pair: null }, false)} />}
      {shown.length === 0 ? (
        <p className="muted">{t.empty}</p>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="bn-list">
          <table className="change-table bn-table">
            <thead>
              <tr>
                <th scope="col">{t.cols.pair}</th>
                <th scope="col">{t.cols.kind}</th>
                <th scope="col" className="num">
                  {t.cols.n}
                </th>
                <th scope="col" className="num">
                  {t.cols.fixed}
                </th>
                <th scope="col" className="num">
                  {t.cols.letters}
                </th>
                <th scope="col" className="num">
                  {t.cols.syll}
                </th>
                <th scope="col" className="num">
                  {t.cols.early}
                </th>
                <th scope="col" className="num">
                  {t.cols.late}
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((b) => (
                <tr key={b.pair} className={sel?.pair === b.pair ? 'selected' : undefined}>
                  <th scope="row">
                    <button type="button" className="linkish he" lang="he" dir="rtl" aria-label={t.showPair(pairText(b))} aria-pressed={sel?.pair === b.pair} onClick={() => update({ pair: sel?.pair === b.pair ? null : b.pair }, false)}>
                      {pairText(b)}
                    </button>
                  </th>
                  <td>{t.kind[b.kind]}</td>
                  <td className="num">{b.n}</td>
                  <td className="num">{Math.round(b.fixed * 100)}%</td>
                  <td className="num">
                    {b.first_letters} · {b.second_letters}
                  </td>
                  <td className="num">
                    {b.first_syll} · {b.second_syll}
                  </td>
                  <td className="num">{t.of(b.rev_early, b.n_early)}</td>
                  <td className={b.rev_late > 0 ? 'num bn-turned' : 'num'}>{t.of(b.rev_late, b.n_late)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function PairPanel({ b, examples, onClose }: { b: Binomial; examples: number; onClose: () => void }) {
  const t = useLocale().m.bn
  const res = useBinomialOccurrences(b.pair)
  const items = res.data?.items ?? []
  const ref = useRef<HTMLElement>(null)
  // the pair is chosen from a long table below: bring its panel into view
  useEffect(() => ref.current?.scrollIntoView?.({ block: 'nearest' }), [b.pair])
  return (
    <section ref={ref} className="hf-list bn-panel" aria-labelledby="bn-panel">
      <h3 id="bn-panel">{t.pairTitle(`⁨${pairText(b)}⁩`)}</h3>
      <p className="muted small">{t.listed(examples)}</p>
      {([true, false] as const).map((own) => {
        const list = items.filter((o) => o.own === own)
        if (list.length === 0) return null
        return (
          <div key={String(own)}>
            <h4>{own ? t.ownOrder : t.rarerOrder}</h4>
            <ul className="hits bn-occurrences">
              {list.map((o) => (
                <Occurrence key={`${o.verse.verse_id}-${o.a_tok}`} o={o} />
              ))}
            </ul>
          </div>
        )
      })}
      <button type="button" className="linkish small" onClick={onClose}>
        {t.close}
      </button>
    </section>
  )
}

function Occurrence({ o }: { o: BinomialOccurrence }) {
  const { locale } = useLocale()
  const hl: Highlight = new Map()
  if (o.a_tok !== null) hl.set(o.a_tok, 'focus')
  if (o.b_tok !== null) hl.set(o.b_tok, 'focus')
  return (
    <li className="hit">
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${o.verse.verse_id}`)}>
          {locale === 'he' ? o.verse.ref_he : o.verse.ref}
        </Link>
      </div>
      <p className="hit-text">
        <HebrewText verse={o.verse} highlight={hl} />
      </p>
    </li>
  )
}
