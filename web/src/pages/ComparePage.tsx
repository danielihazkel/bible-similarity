import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useCompare, useExplain, useVerseDiff } from '../api/hooks'
import type { CompareResponse, Pair, UnitSummary, Verse, VerseDiff } from '../api/types'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { LemmaChips } from '../components/LemmaChips'
import { ErrorBox, Loading } from '../components/Status'
import { UnitPicker } from '../components/UnitPicker'
import { useLocale, useT } from '../context/localeContext'
import { similarityBand } from '../lib/format'
import { unitLabel, verseRef } from '../lib/names'
import { diffHighlight, highlightFor, type Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

/** The hovered verse pair, always as (verse in A, verse in B). */
type Active = { a: number; b: number; from: 'a' | 'b' }
/** What the active pair's words are marked by: shared lemmas, or the word-level changes A → B. */
type Marks = 'shared' | 'changes'

export function ComparePage() {
  const m = useT()
  const [params, update] = useQueryParams()
  const a = params.get('a') ?? undefined
  const b = params.get('b') ?? undefined
  const cmp = useCompare(a, b)

  return (
    <div className="page compare-page">
      <h1>{m.compare.title}</h1>
      <p className="lede">{m.compare.lede}</p>
      <div className="pickers">
        <UnitPicker key={`a:${a}`} label="A" value={a} onChange={(id) => update({ a: id }, false)} />
        <button
          type="button"
          className="swap"
          title={m.compare.swap}
          disabled={!a && !b}
          onClick={() => update({ a: b ?? null, b: a ?? null }, false)}
        >
          ⇄
        </button>
        <UnitPicker key={`b:${b}`} label="B" value={b} onChange={(id) => update({ b: id }, false)} />
      </div>
      {!a || !b ? (
        <p className="status">{m.compare.choose}</p>
      ) : cmp.isPending ? (
        <Loading />
      ) : cmp.error ? (
        <ErrorBox error={cmp.error} />
      ) : (
        <Alignment
          key={`${a}|${b}`}
          data={cmp.data}
          marks={params.get('marks') === 'changes' ? 'changes' : 'shared'}
          onMarks={(m) => update({ marks: m === 'changes' ? m : null }, false)}
        />
      )}
    </div>
  )
}

function Alignment({ data, marks, onMarks }: { data: CompareResponse; marks: Marks; onMarks: (m: Marks) => void }) {
  const { m, locale } = useLocale()
  const [active, setActive] = useState<Active>()
  const [focusLemma, setFocusLemma] = useState<string>()
  const explain = useExplain(marks === 'shared' ? active?.a : undefined, active?.b)
  const ex = explain.data && active && explain.data.a === active.a && explain.data.b === active.b ? explain.data : undefined
  const diff = useVerseDiff(active?.a, active?.b, marks === 'changes')
  const df = diff.data && active && diff.data.a === active.a && diff.data.b === active.b ? diff.data : undefined
  const highlight = (side: 'a' | 'b'): Highlight | undefined =>
    marks === 'changes' ? diffHighlight(side === 'a' ? df?.a_marks : df?.b_marks) : highlightFor(ex, side, focusLemma)

  const bestOfB = new Map(data.b_to_a.map((p) => [p.src, p.tgt]))
  const bestOfA = new Map(data.a_to_b.map((p) => [p.src, p.tgt]))
  const verse = (id: number): Verse => data.verses[String(id)]
  const pairOf = (side: 'a' | 'b', id: number): Pair | undefined =>
    (side === 'a' ? data.a_to_b : data.b_to_a).find((p) => p.src === id)

  return (
    <>
      <div className="bma">
        <span>
          BMA <strong>{data.bma.toFixed(3)}</strong>
        </span>
        <span className="muted small">{m.compare.bmaHint}</span>
        <span className="legend" aria-hidden>
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className={`sim-swatch sim-${i}`} />
          ))}
          <span className="muted small">{m.compare.lowHigh}</span>
        </span>
      </div>
      <div className="columns">
        <Column
          side="a"
          unit={data.a}
          pairs={data.a_to_b}
          other={data.b}
          mutual={(p) => bestOfB.get(p.tgt) === p.src}
          verse={verse}
          active={active}
          highlight={highlight}
          onHover={(p) => setActive(p && { a: p.src, b: p.tgt, from: 'a' })}
        />
        <Column
          side="b"
          unit={data.b}
          pairs={data.b_to_a}
          other={data.a}
          mutual={(p) => bestOfA.get(p.tgt) === p.src}
          verse={verse}
          active={active}
          highlight={highlight}
          onHover={(p) => setActive(p && { a: p.tgt, b: p.src, from: 'b' })}
        />
      </div>
      {active && (
        <div className="pair-panel" aria-live="polite">
          <span className="small">
            {verseRef(verse(active.a), locale)} ↔ {verseRef(verse(active.b), locale)} · {m.compare.cosine}{' '}
            {(pairOf(active.from, active.from === 'a' ? active.a : active.b)?.cosine ?? 0).toFixed(3)}
          </span>
          <span className="segmented" role="group" aria-label={m.hit.markBy}>
            {(['shared', 'changes'] as const).map((k) => (
              <button key={k} type="button" className={marks === k ? 'on' : ''} aria-pressed={marks === k} onClick={() => onMarks(k)}>
                {k === 'shared' ? m.hit.sharedWords : m.compare.changes}
              </button>
            ))}
          </span>
          {marks === 'shared' ? (
            <LemmaChips explain={ex} loading={explain.isFetching} focus={focusLemma} onFocus={setFocusLemma} />
          ) : (
            <ChangesNote diff={df} loading={diff.isFetching} error={diff.error} />
          )}
        </div>
      )}
    </>
  )
}

interface ColumnProps {
  side: 'a' | 'b'
  unit: UnitSummary
  other: UnitSummary
  pairs: Pair[]
  mutual: (p: Pair) => boolean
  verse: (id: number) => Verse
  active?: Active
  highlight: (side: 'a' | 'b') => Highlight | undefined
  onHover: (p: Pair | undefined) => void
}

function Column({ side, unit, other, pairs, mutual, verse, active, highlight, onHover }: ColumnProps) {
  const { m, locale } = useLocale()
  const listRef = useRef<HTMLOListElement>(null)
  const mine = active ? (side === 'a' ? active.a : active.b) : undefined
  const isPartner = active !== undefined && active.from !== side
  const sameChapter = unit.unit_type === 'verse' || unit.unit_type === 'chapter'

  // Bring the partner of the hovered verse into view inside this column.
  useEffect(() => {
    if (!isPartner || mine === undefined) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    listRef.current
      ?.querySelector(`[data-vid="${mine}"]`)
      ?.scrollIntoView({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' })
  }, [isPartner, mine])

  return (
    <section className="column" aria-label={m.compare.unitSide(side.toUpperCase())}>
      <h2>
        <span className="side-tag">{side.toUpperCase()}</span>
        <Link to={unitLink(unit.unit_id)}>{unitLabel(unit, locale)}</Link>
        {locale === 'en' && (
          <>
            {' '}
            <span className="he-label" dir="rtl" lang="he">
              {unit.label_he}
            </span>
          </>
        )}
        <span className="type-tag">{m.units.type(unit.unit_type)}</span>
      </h2>
      <ol className="align-list" ref={listRef} onMouseLeave={() => onHover(undefined)}>
        {pairs.map((p) => {
          const v = verse(p.src)
          const t = verse(p.tgt)
          const on = mine === p.src
          return (
            <li
              key={p.src}
              data-vid={p.src}
              className={`align-row sim-${similarityBand(p.cosine)} ${on ? (isPartner ? 'partner' : 'active') : ''}`}
              onMouseEnter={() => onHover(p)}
              onFocus={() => onHover(p)}
              tabIndex={0}
            >
              <div className="align-meta">
                <span className="verse-num">{sameChapter ? v.verse : m.cv(v.chapter, v.verse)}</span>
                <span className="partner-ref" title={m.compare.bestIn(unitLabel(other, locale))}>
                  {mutual(p) ? '⇄' : locale === 'he' ? '←' : '→'} {m.cv(t.chapter, t.verse)}
                </span>
                <span className="cos">{p.cosine.toFixed(2)}</span>
              </div>
              <HebrewText verse={v} highlight={on ? highlight(side) : undefined} />
            </li>
          )
        })}
      </ol>
    </section>
  )
}

function ChangesNote({ diff, loading, error }: { diff?: VerseDiff; loading: boolean; error: unknown }) {
  const m = useT()
  if (error) return <span className="status error small">{m.diff.loadFailed}</span>
  if (!diff) return loading ? <span className="muted small">{m.diff.aligning}</span> : null
  if (diff.loose) return <span className="muted small">{m.diff.tooDifferentShare(diff.shared)}</span>
  return (
    <>
      <span className="muted small">{m.diff.keepShare(diff.shared)}</span>
      <DiffLegend />
    </>
  )
}
