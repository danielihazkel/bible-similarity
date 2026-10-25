import { useState, type CSSProperties } from 'react'
import { Link, useParams } from 'react-router'
import { useSynopsis } from '../api/hooks'
import type { SynopsisCell, Verse } from '../api/types'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { diffHighlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { verseRef } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

/** One synopsis: its passages in columns, row by row, each column's words marked against the
 * `?base=` column's (DESIGN.md §16.74). */
export function SynopsisPage() {
  const { m, locale } = useLocale()
  const t = m.par.synopsis
  const { synId } = useParams()
  const id = Number(synId)
  const valid = Number.isInteger(id) && id > 0
  const [params, update] = useQueryParams()
  const base = Math.max(0, Number(params.get('base')) || 0)
  const res = useSynopsis(valid ? id : undefined, base)
  const [showChanges, setShowChanges] = useState(true)
  if (!valid) return <p className="status">{t.notId}</p>
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { synopsis: s, rows, verses } = res.data
  const label = (k: number) => (locale === 'he' ? s.columns[k].label_he : s.columns[k].label)
  const style = { '--syn-cols': s.columns.length } as CSSProperties

  return (
    <div className="page synopsis-page">
      <nav className="crumbs" aria-label={m.units.context}>
        <Link to="/synopses">{m.par.synopses.title}</Link>
      </nav>
      <h1>{s.columns.map((_, k) => label(k)).join(' · ')}</h1>
      <p className="lede">
        {t.summary(s.n_rows, s.n_aligned, s.columns.length)} {t.order}
      </p>
      <p className="muted small">
        {t.joined}{' '}
        {s.seq_ids.map((q, i) => (
          <span key={q}>
            {i > 0 && ', '}
            <Link to={`/sequences/${q}`}>#{q}</Link>
          </span>
        ))}
        .{s.breaks > 0 && ` ${t.breaks(s.breaks)}`}
        {s.dropped > 0 && ` ${t.dropped(s.dropped)}`}
      </p>
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={showChanges} onChange={(e) => setShowChanges(e.target.checked)} />
          {m.par.sequence.markChanges}
        </label>
        {showChanges && (
          <label className="control" title={t.baseHint}>
            <span>{t.base}</span>
            <select value={res.data.base} onChange={(e) => update({ base: e.target.value === '0' ? null : e.target.value })}>
              {s.columns.map((_, k) => (
                <option key={k} value={k}>
                  {label(k)}
                </option>
              ))}
            </select>
          </label>
        )}
        {showChanges && <DiffLegend />}
      </div>
      <p className="muted small">
        {showChanges && `${t.loose} · `}
        {t.reordered}
      </p>
      <div className="syn-head" style={style} aria-hidden="true">
        {s.columns.map((_, k) => (
          <span key={k} className={k === res.data.base && showChanges ? 'base' : undefined}>
            {label(k)}
          </span>
        ))}
      </div>
      <ol className="synopsis" style={style} aria-label={t.rows}>
        {rows.map((r, i) => (
          <li key={i} className="syn-row">
            {r.map((c, k) => (
              <Cell
                key={k}
                cell={c}
                verse={c.verse === null || c.verse === undefined ? undefined : verses[String(c.verse)]}
                base={k === res.data.base && showChanges}
                marks={showChanges}
              />
            ))}
          </li>
        ))}
      </ol>
    </div>
  )
}

function Cell({ cell, verse, base, marks }: { cell: SynopsisCell; verse?: Verse; base: boolean; marks: boolean }) {
  const { m, locale } = useLocale()
  const t = m.par.synopsis
  if (!verse) return <div className="syn-cell empty" />
  return (
    <div className={`syn-cell${base ? ' base' : ''}`}>
      <Link className="hit-ref" to={unitLink(`v:${verse.verse_id}`)}>
        {verseRef(verse, locale)}
      </Link>
      {cell.reordered && (
        <span className="syn-flag" role="img" aria-label={t.reordered} title={t.reordered}>
          ↶
        </span>
      )}
      {marks && cell.loose && (
        <span className="syn-flag" role="img" aria-label={t.looseTitle} title={t.looseTitle}>
          ≈
        </span>
      )}
      <p className="hit-text">
        <HebrewText verse={verse} highlight={marks ? diffHighlight(cell.marks) : undefined} />
      </p>
    </div>
  )
}
