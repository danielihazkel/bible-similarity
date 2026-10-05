import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import { useDomains, useLemmaSenses } from '../api/hooks'
import type { LemmaSense } from '../api/types'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { lemmaLink, unitLink } from '../lib/links'
import { DomainChip } from './DomainName'
import { HebrewText } from './HebrewText'
import { PanelError } from './Status'
import { UnitName } from './UnitName'

/** A lemma's dictionary senses and contextual uses by corpus group (DESIGN.md §16.23). */
export function SensesPanel({ lemma }: { lemma: string }) {
  const { m } = useLocale()
  const t = m.sen
  const res = useLemmaSenses(lemma)
  if (res.error) return <PanelError what={t.panel} error={res.error} />
  if (!res.data) return null
  const d = res.data
  return (
    <section id="senses" className="senses-panel" aria-label={t.panel}>
      <h2>{t.panel}</h2>
      {d.shift === null ? (
        <p className="muted small">{t.notCompared}</p>
      ) : (
        <>
          <p className="muted small">
            {t.panelLede}{' '}
            {t.stats(
              d.shift.sense_excess == null || d.shift.sense_q == null ? t.untested : t.bits(d.shift.sense_excess, d.shift.sense_q),
              t.bits(d.shift.use_excess, d.shift.use_q),
            )}
          </p>
          {d.senses.length > 0 && <SenseTable title={t.dictionary} rows={d.senses} order={d.group_order} />}
          <SenseTable title={t.inContext} rows={d.uses} order={d.group_order} />
        </>
      )}
    </section>
  )
}

function SenseTable({ title, rows, order }: { title: string; rows: LemmaSense[]; order: string[] }) {
  const { m } = useLocale()
  const t = m.sen
  const domains = useDomains()
  const domainOf = new Map(domains.data?.map((x) => [x.code, x]) ?? [])
  const totals = Object.fromEntries(order.map((g) => [g, rows.reduce((s, r) => s + (r.groups[g] ?? 0), 0)]))
  return (
    <>
      <h3>{title}</h3>
      <div className="table-wrap">
        <table className="change-table senses-table">
          <thead>
            <tr>
              <th />
              {order.map((g) => (
                <th key={g} className="num" title={t.groupsTitle}>
                  {t.groups[g] ?? g}
                </th>
              ))}
              <th>{t.examples}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.sense}>
                <th scope="row">
                  {r.kind === 'use' ? t.use(i) : t.meaning(i)} <span className="muted small">({m.num(r.n)})</span>
                  <div className="chips">
                    {r.domains.map((c) => (
                      <DomainChip key={c} domain={domainOf.get(c) ?? { code: c, label_en: c }} />
                    ))}
                    {r.collocates.length > 0 && <span className="muted small">{t.withWords}</span>}
                    {r.collocates.map((c) => (
                      <Link key={c.lemma} className="chip lemma-chip" to={lemmaLink(c.lemma)}>
                        <span dir="rtl" lang="he">
                          {c.he_lemma}
                        </span>
                      </Link>
                    ))}
                  </div>
                </th>
                {order.map((g) => {
                  const share = totals[g] ? (r.groups[g] ?? 0) / totals[g] : 0
                  return (
                    <td key={g} className="num share-cell" style={{ '--share': share } as CSSProperties}>
                      {totals[g] ? `${Math.round(share * 100)}%` : '—'}
                    </td>
                  )
                })}
                <td className="sense-examples">
                  {r.examples.map((e) => (
                    <div key={e.verse.verse_id}>
                      <Link className="hit-ref" to={unitLink(`v:${e.verse.verse_id}`)}>
                        <UnitName en={e.label_en} he={e.label_he} />
                      </Link>{' '}
                      <HebrewText
                        verse={e.verse}
                        highlight={new Map(e.display_idx == null ? [] : [[e.display_idx, 'shared']]) as Highlight}
                      />
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
