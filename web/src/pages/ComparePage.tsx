import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useCompare, useExplain, useVerseDiff } from '../api/hooks'
import type { CompareResponse, Pair, UnitSummary, Verse, VerseDiff } from '../api/types'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { LemmaChips } from '../components/LemmaChips'
import { ErrorBox, Loading } from '../components/Status'
import { UnitPicker } from '../components/UnitPicker'
import { similarityBand, unitTypeLabel } from '../lib/format'
import { diffHighlight, highlightFor, type Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

/** The hovered verse pair, always as (verse in A, verse in B). */
type Active = { a: number; b: number; from: 'a' | 'b' }
/** What the active pair's words are marked by: shared lemmas, or the word-level changes A → B. */
type Marks = 'shared' | 'changes'

export function ComparePage() {
  const [params, update] = useQueryParams()
  const a = params.get('a') ?? undefined
  const b = params.get('b') ?? undefined
  const cmp = useCompare(a, b)

  return (
    <div className="page compare-page">
      <h1>Compare</h1>
      <p className="lede">
        Every verse is paired with its most similar verse in the other unit (cosine of the semantic embeddings).
        Hover a verse to see its partner and their shared words.
      </p>
      <div className="pickers">
        <UnitPicker key={`a:${a}`} label="A" value={a} onChange={(id) => update({ a: id }, false)} />
        <button
          type="button"
          className="swap"
          title="Swap A and B"
          disabled={!a && !b}
          onClick={() => update({ a: b ?? null, b: a ?? null }, false)}
        >
          ⇄
        </button>
        <UnitPicker key={`b:${b}`} label="B" value={b} onChange={(id) => update({ b: id }, false)} />
      </div>
      {!a || !b ? (
        <p className="status">Choose two units, or use “Compare” on any result.</p>
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
        <span className="muted small">½ (mean best cosine A→B + mean best cosine B→A)</span>
        <span className="legend" aria-hidden>
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className={`sim-swatch sim-${i}`} />
          ))}
          <span className="muted small">low → high</span>
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
            {verse(active.a).ref} ↔ {verse(active.b).ref} · cosine{' '}
            {(pairOf(active.from, active.from === 'a' ? active.a : active.b)?.cosine ?? 0).toFixed(3)}
          </span>
          <span className="segmented" role="group" aria-label="Mark words by">
            {(['shared', 'changes'] as const).map((m) => (
              <button key={m} type="button" className={marks === m ? 'on' : ''} aria-pressed={marks === m} onClick={() => onMarks(m)}>
                {m === 'shared' ? 'Shared words' : 'Changes A → B'}
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
    <section className="column" aria-label={`Unit ${side.toUpperCase()}`}>
      <h2>
        <span className="side-tag">{side.toUpperCase()}</span>
        <Link to={unitLink(unit.unit_id)}>{unit.label_en}</Link>{' '}
        <span className="he-label" dir="rtl" lang="he">
          {unit.label_he}
        </span>
        <span className="type-tag">{unitTypeLabel(unit.unit_type)}</span>
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
                <span className="verse-num">{sameChapter ? v.verse : `${v.chapter}:${v.verse}`}</span>
                <span className="partner-ref" title={`Best match in ${other.label_en}`}>
                  {mutual(p) ? '⇄' : '→'} {t.ref.replace(/^.* (?=\d+:\d+$)/, '')}
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
  if (error) return <span className="status error small">Could not load the changes.</span>
  if (!diff) return loading ? <span className="muted small">Aligning words…</span> : null
  if (diff.loose)
    return (
      <span className="muted small">
        Too different to mark word by word ({Math.round(diff.shared * 100)}% of the words keep their lemma).
      </span>
    )
  return (
    <>
      <span className="muted small">{Math.round(diff.shared * 100)}% of the words keep their lemma; A is read as the earlier passage.</span>
      <DiffLegend />
    </>
  )
}
