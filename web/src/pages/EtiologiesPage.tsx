import { Link } from 'react-router'
import { useEtiologies } from '../api/hooks'
import type { EtiologiesResponse, Naming } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { EtyOrder, EtyShow } from '../i18n/pages/etiologies'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

/** Naming etiologies (§16.66): every naming the formula finds, the word of its verse that echoes
 * the name best, and the two checks. */
export function EtiologiesPage() {
  const { m } = useLocale()
  const t = m.ety
  const res = useEtiologies()
  const d = res.data
  return (
    <div className="page etiologies-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Namings d={d} />
          <p className="muted small">{t.method}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.ety
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: EtiologiesResponse }) {
  const t = useLocale().m.ety
  const missing = d.known.filter((k) => !k.found).map((k) => k.ref)
  return (
    <section aria-labelledby="ety-checks">
      <h2 id="ety-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.echo.title} <Verdict holds={d.holds} />
          </h3>
          {d.mean_own !== null && d.mean_null !== null && <p>{t.echo.text(d.mean_own, d.mean_null, d.namings.length, d.p)}</p>}
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(d.known_found, d.known_echo, d.known.length, d.known_rank, d.known_share)}</p>
          {missing.length > 0 && <p className="muted small">{t.known.missing(missing.join(', '))}</p>}
        </article>
      </div>
    </section>
  )
}

const isLead = (n: Naming, alpha: number) => n.q !== null && n.q <= alpha

function Namings({ d }: { d: EtiologiesResponse }) {
  const t = useLocale().m.ety
  const [params, update] = useQueryParams()
  const show: EtyShow = params.get('show') === 'leads' || params.get('show') === 'known' ? (params.get('show') as EtyShow) : 'all'
  const order: EtyOrder = params.get('order') === 'strongest' ? 'strongest' : 'canon'
  const counts = { all: d.namings.length, leads: d.namings.filter((n) => isLead(n, d.alpha)).length, known: d.namings.filter((n) => n.known).length }
  const shown = d.namings.filter((n) => (show === 'leads' ? isLead(n, d.alpha) : show === 'known' ? n.known : true))
  if (order === 'strongest') shown.sort((a, b) => (a.p ?? 1) - (b.p ?? 1) || b.score - a.score || a.naming - b.naming)
  return (
    <section aria-labelledby="ety-list">
      <h2 id="ety-list">{t.listTitle}</h2>
      <div className="controls">
        <Segmented<EtyShow>
          label={t.show.label}
          value={show}
          options={(['all', 'leads', 'known'] as const).map((v) => ({ value: v, label: t.show[v](counts[v]) }))}
          onChange={(v) => update({ show: v === 'all' ? null : v })}
        />
        <Segmented<EtyOrder>
          label={t.order.label}
          value={order}
          options={(['canon', 'strongest'] as const).map((v) => ({ value: v, label: t.order[v] }))}
          onChange={(v) => update({ order: v === 'canon' ? null : v })}
        />
      </div>
      {shown.length === 0 ? (
        <p className="muted">{t.empty}</p>
      ) : (
        <ul className="hits ety-list">
          {shown.map((n) => (
            <NamingItem key={n.naming} n={n} alpha={d.alpha} />
          ))}
        </ul>
      )}
    </section>
  )
}

function NamingItem({ n, alpha }: { n: Naming; alpha: number }) {
  const t = useLocale().m.ety
  const hl: Highlight = new Map()
  if (n.name_first !== null && n.name_last !== null) for (let i = n.name_first; i <= n.name_last; i++) hl.set(i, 'focus')
  if (n.echo_disp !== null && !hl.has(n.echo_disp)) hl.set(n.echo_disp, 'shared')
  return (
    <li className={`hit ety-naming${isLead(n, alpha) ? ' ety-lead' : ''}`}>
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${n.verse.verse_id}`)}>
          <UnitName en={n.verse.ref} he={n.verse.ref_he} />
        </Link>{' '}
        <b dir="rtl" lang="he" className="he">
          {n.name}
        </b>{' '}
        <span className="type-tag">{t.kind[n.kind]}</span>{' '}
        {n.echo_word ? (
          <>
            <span className="muted small">{t.echoedBy}</span>{' '}
            <b dir="rtl" lang="he" className="he">
              {n.echo_word}
            </b>{' '}
            <span className="small">{t.score(n.score)}</span>
          </>
        ) : (
          <span className="muted small">{t.noEcho}</span>
        )}
        {n.chance !== null && <span className="muted small"> · {t.chance(n.chance)}</span>}
        {n.p !== null && n.q !== null && <span className="muted small"> · {t.pq(n.p, n.q)}</span>}
        {n.known && <span className="muted small"> · {t.knownTag}</span>}
      </div>
      <p className="hit-text">
        <HebrewText verse={n.verse} highlight={hl} />
      </p>
    </li>
  )
}
