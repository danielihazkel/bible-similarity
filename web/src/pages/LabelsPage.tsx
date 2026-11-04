import { useState } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'
import { useLabelQueue, useLabels, useLabelsEval, useSetLabel } from '../api/hooks'
import type { Label, LabelValue, Mode, QueueItem, QueueSide } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { LabelButtons } from '../components/LabelButtons'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { formatScore } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { verseRef } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const SHOW = ['all', 'real', 'not', 'unsure'] as const
type Show = (typeof SHOW)[number]
const SIDES: QueueSide[] = ['all', 'lexical', 'semantic']
/** The `mode` a label from the queue records (the list that proposed the pair). */
const QUEUE = 'queue'
const fmt = (x: number | null) => (x === null ? '—' : x.toFixed(2))

/** Your judgements of proposed pairs, how each mode separates them (DESIGN.md §16.25), and the
 * queue of pairs worth judging next (`?tab=queue`, §16.79). */
export function LabelsPage() {
  const { m } = useLocale()
  const t = m.lab
  const [params, update] = useQueryParams()
  const queue = params.get('tab') === 'queue'
  return (
    <div className="page labels-page">
      <h1>{t.title}</h1>
      <div className="toolbar">
        <Segmented
          label={t.view}
          value={queue ? 'queue' : 'labels'}
          onChange={(v) => update({ tab: v === 'queue' ? v : null, show: null, side: null })}
          options={(['labels', 'queue'] as const).map((v) => ({ value: v, label: t.views[v] }))}
        />
      </div>
      {queue ? <Queue /> : <Labelled />}
    </div>
  )
}

function Labelled() {
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
    <>
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
    </>
  )
}

function Queue() {
  const { m } = useLocale()
  const t = m.lab
  const [params, update] = useQueryParams()
  const side: QueueSide = SIDES.includes(params.get('side') as QueueSide) ? (params.get('side') as QueueSide) : 'all'
  const q = useLabelQueue(side)
  if (q.isPending) return <Loading />
  if (q.error)
    return q.error instanceof ApiError && q.error.status === 503 ? <p className="status">{t.queueMissing}</p> : <ErrorBox error={q.error} />
  const d = q.data
  return (
    <section aria-labelledby="lq-h">
      <h2 id="lq-h">{t.views.queue}</h2>
      <p className="lede">{t.queueLede}</p>
      <p className="muted small">{t.queueTraining(d.train_real, d.min_train)}</p>
      {!d.writable && <p className="status">{t.readOnly}</p>}
      <div className="toolbar">
        <Segmented
          label={t.queueSide}
          value={side}
          onChange={(v) => update({ side: v === 'all' ? null : v })}
          options={SIDES.map((v) => ({ value: v, label: v === 'all' ? t.either : m.modes.names[v] }))}
        />
        <span className="muted small">{t.queueCounts(d.total, d.pool, d.labelled)}</span>
      </div>
      {d.items.length === 0 ? (
        <p className="status">{t.queueNone}</p>
      ) : (
        <>
          <ol className="queue-list">
            {d.items.map((i) => (
              <QueueRow key={`${i.a_id}|${i.b_id}`} i={i} k={d.k} />
            ))}
          </ol>
          <button type="button" className="primary" title={t.queueMoreTitle} disabled={q.isFetching} onClick={() => void q.refetch()}>
            {t.queueMore}
          </button>
        </>
      )}
    </section>
  )
}

function QueueRow({ i, k }: { i: QueueItem; k: number }) {
  const { m, locale } = useLocale()
  const t = m.lab
  const rank = (r: number | null | undefined) => (r == null ? t.beyond(k) : m.num(r))
  return (
    <li>
      <p className="queue-head">
        <Link to={unitLink(i.a_id)}>{verseRef(i.a, locale)}</Link>
        {' ↔ '}
        <Link to={unitLink(i.b_id)}>{verseRef(i.b, locale)}</Link>
        <span className="muted small">
          {' · '}
          {t.ranks(rank(i.lex_rank), rank(i.sem_rank))}
        </span>
      </p>
      <p className="queue-text">
        <HebrewText verse={i.a} />
      </p>
      <p className="queue-text">
        <HebrewText verse={i.b} />
      </p>
      <p className="queue-actions">
        <LabelButtons a={i.a_id} b={i.b_id} mode={QUEUE} score={i.score} />
        <Link className="linkish small" to={compareLink(i.a_id, i.b_id)} title={m.hit.compareTitle}>
          {m.hit.compare}
        </Link>
      </p>
    </li>
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
            {t.judgedIn(l.mode === QUEUE ? t.queueMode : (m.modes.names[l.mode as Mode] ?? l.mode), formatScore(l.score))}
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
