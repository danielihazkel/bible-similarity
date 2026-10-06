import { useState } from 'react'
import { Link } from 'react-router'
import { useLabels, useLabelsEval, useSetLabel } from '../api/hooks'
import type { Label, LabelValue, Mode } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { LabelButtons } from '../components/LabelButtons'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { formatScore } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

const SHOW = ['all', 'real', 'not', 'unsure'] as const
type Show = (typeof SHOW)[number]
const fmt = (x: number | null) => (x === null ? '—' : x.toFixed(2))

/** Your judgements of proposed pairs, and how each mode separates them (DESIGN.md §16.25). */
export function LabelsPage() {
  const { m } = useLocale()
  const t = m.lab
  const [params, update] = useQueryParams()
  const show: Show = SHOW.includes(params.get('show') as Show) ? (params.get('show') as Show) : 'all'
  const labels = useLabels()
  if (labels.isPending) return <Loading />
  if (labels.error) return <ErrorBox error={labels.error} />
  const { items, counts, writable } = labels.data
  const shown = show === 'all' ? items : items.filter((l) => l.label === show)
  return (
    <div className="page labels-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">{t.caveat}</p>
      {!writable && <p className="status">{t.readOnly}</p>}
      {items.length === 0 ? (
        <p className="status">{t.none}</p>
      ) : (
        <>
          <p>{t.counts(counts.real ?? 0, counts.not ?? 0, counts.unsure ?? 0)}</p>
          <Separation />
          <section aria-label={t.pairs}>
            <h2>{t.pairs}</h2>
            <div className="toolbar">
              <Segmented
                label={t.show}
                value={show}
                onChange={(v) => update({ show: v === 'all' ? null : v })}
                options={SHOW.map((v) => ({ value: v, label: v === 'all' ? t.all : t.values[v] }))}
              />
              <span className="muted small">
                <ExportCsv
                  filename="labels.csv"
                  rows={() =>
                    shown.map((l) => ({
                      a: l.a.label_en,
                      b: l.b.label_en,
                      label: l.label,
                      note: l.note,
                      mode: l.mode ?? '',
                      score: l.score ?? '',
                      labeled_at: l.labeled_at,
                    }))
                  }
                />
              </span>
            </div>
            <ul className="labels-list">
              {shown.map((l) => (
                <LabelRow key={`${l.a.unit_id}|${l.b.unit_id}`} l={l} writable={writable} />
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}

function Separation() {
  const { m } = useLocale()
  const t = m.lab
  const ev = useLabelsEval()
  if (ev.isPending) return <Loading />
  if (ev.error) return <ErrorBox error={ev.error} />
  if (ev.data.rows.length === 0) return null
  return (
    <section aria-label={t.evalTitle}>
      <h2>{t.evalTitle}</h2>
      <p className="muted small">{t.evalLede(ev.data.k, ev.data.min_pairs)}</p>
      <div className="table-wrap">
        <table className="change-table">
          <thead>
            <tr>
              <th>{t.unitType}</th>
              <th>{t.mode}</th>
              <th className="num">{t.realFound}</th>
              <th className="num">{t.notFound}</th>
              <th className="num">{t.precision}</th>
              <th className="num">{t.auc}</th>
            </tr>
          </thead>
          <tbody>
            {ev.data.rows.map((r) => (
              <tr key={`${r.unit_type}-${r.mode}`}>
                <td>{m.units.type(r.unit_type)}</td>
                <td>{m.modes.names[r.mode as Mode] ?? r.mode}</td>
                <td className="num">
                  {m.num(r.found_real)} / {m.num(r.n_real)}
                </td>
                <td className="num">
                  {m.num(r.found_not)} / {m.num(r.n_not)}
                </td>
                <td className="num">{fmt(r.precision)}</td>
                <td className="num">{fmt(r.auc)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function LabelRow({ l, writable }: { l: Label; writable: boolean }) {
  const { m } = useLocale()
  const t = m.lab
  const set = useSetLabel()
  const [note, setNote] = useState(l.note)
  const save = () => {
    if (note !== l.note)
      set.mutate({ a_id: l.a.unit_id, b_id: l.b.unit_id, label: l.label as LabelValue, note, mode: l.mode, score: l.score })
  }
  return (
    <li>
      <span className="label-pair">
        <Link to={unitLink(l.a.unit_id)}>
          <UnitName en={l.a.label_en} he={l.a.label_he} />
        </Link>
        {' ↔ '}
        <Link to={unitLink(l.b.unit_id)}>
          <UnitName en={l.b.label_en} he={l.b.label_he} />
        </Link>
        {l.mode && l.score !== null && (
          <span className="muted small">
            {' · '}
            {t.judgedIn(m.modes.names[l.mode as Mode] ?? l.mode, formatScore(l.score))}
          </span>
        )}
      </span>
      <LabelButtons a={l.a.unit_id} b={l.b.unit_id} mode={l.mode ?? undefined} score={l.score ?? undefined} />
      {writable ? (
        <input
          type="text"
          aria-label={t.note}
          placeholder={t.notePlaceholder}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => e.key === 'Enter' && save()}
        />
      ) : (
        l.note && <span className="small">{l.note}</span>
      )}
      <Link className="linkish small" to={compareLink(l.a.unit_id, l.b.unit_id)} title={m.hit.compareTitle}>
        {m.hit.compare}
      </Link>
    </li>
  )
}
