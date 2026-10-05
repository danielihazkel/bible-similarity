import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { useExplain, usePhrasesOf, useSequences, useSimilar, useUnit, useUnitParallelism } from '../api/hooks'
import type { Leitwort, UnitDetail, UnitSummary, Verse, VerseHalves } from '../api/types'
import { ExcludeFilters, KSelect, ModeToggle } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { HitCard } from '../components/HitCard'
import { PhraseCard } from '../components/PhraseCard'
import { SequenceCard } from '../components/SequenceCard'
import { StructurePanel } from '../components/StructurePanel'
import { WordPanel } from '../components/WordPanel'
import { ErrorBox, Loading } from '../components/Status'
import { unitLink } from '../lib/links'
import { MODE_HINTS, unitTypeLabel } from '../lib/format'
import { highlightFor, type Highlight } from '../lib/highlight'
import { DEFAULT_K, DEFAULT_MODE, parseExclude, parseK, parseMode, useQueryParams } from '../lib/urlState'

// Parallel sequences touching this unit: only reasonably strong chains, a few at most.
const SEQUENCE_MAX_Q = 0.2
const SEQUENCES_SHOWN = 5

export function UnitPage() {
  const unitId = useParams().unitId!
  const detail = useUnit(unitId)
  if (detail.isPending) return <Loading />
  if (detail.error) return <ErrorBox error={detail.error} />
  // key: reset hover / pin state when navigating to another unit
  return <UnitView key={unitId} detail={detail.data} />
}

function UnitView({ detail }: { detail: UnitDetail }) {
  const { unit, verses } = detail
  const [params, update] = useQueryParams()
  const { search } = useLocation()
  const mode = parseMode(params.get('mode'))
  const k = parseK(params.get('k'))
  const exclude = parseExclude(params.get('exclude'), unit.unit_type)
  const similar = useSimilar(unit.unit_id, mode, k, exclude)

  // Shared-lemma explanation (verse units): the pinned hit, else the hovered one.
  const [hovered, setHovered] = useState<number>()
  const [pinned, setPinned] = useState<number>()
  const [focusLemma, setFocusLemma] = useState<string>()
  const hoverTimer = useRef<number>(undefined)
  useEffect(() => () => window.clearTimeout(hoverTimer.current), [])
  const [word, setWord] = useState<{ verse: Verse; idx: number }>()
  const pick = (verse: Verse) => (idx: number) =>
    setWord(word?.verse.verse_id === verse.verse_id && word.idx === idx ? undefined : { verse, idx })
  const selectedIn = (verse: Verse) => (word?.verse.verse_id === verse.verse_id ? word.idx : undefined)
  // Structure (larger units): open from the URL (`?structure=1`), Leitwort highlight in the text.
  const structureOpen = params.get('structure') === '1'
  const [leitwort, setLeitwort] = useState<Leitwort>()
  const leitwortMarks = (v: Verse): Highlight | undefined =>
    leitwort ? new Map((leitwort.occurrences[v.verse_id] ?? []).map((i) => [i, 'focus'])) : undefined
  const isVerse = unit.unit_type === 'verse'
  const activeTgt = isVerse ? (pinned ?? hovered) : undefined
  const explain = useExplain(isVerse ? unit.start_verse_id : undefined, activeTgt)
  const phrases = usePhrasesOf(isVerse ? unit.start_verse_id : undefined)
  const halvesOn = params.get('halves') === '1'
  const halves = useUnitParallelism(halvesOn ? unit.unit_id : undefined)
  const halvesOf = new Map((halves.data?.verses ?? []).map((h) => [h.verse_id, h]))
  const breaksOf = (v: Verse) => colonBreaks(halvesOf.get(v.verse_id))
  const sequences = useSequences({ unit: unit.unit_id, maxQ: SEQUENCE_MAX_Q, limit: SEQUENCES_SHOWN, offset: 0 })

  const onHover = (tgt: number, on: boolean) => {
    window.clearTimeout(hoverTimer.current)
    // a short delay so sweeping the mouse over the list does not fire a request per card
    hoverTimer.current = window.setTimeout(() => {
      setHovered(on ? tgt : undefined)
      if (!on) setFocusLemma(undefined)
    }, on ? 120 : 200)
  }

  return (
    <div className="page unit-page">
      <Crumbs detail={detail} search={search} />
      <h1>
        {unit.label_en}{' '}
        <span className="he-label big" dir="rtl" lang="he">
          {unit.label_he}
        </span>
        <span className="type-tag">{unitTypeLabel(unit.unit_type)}</span>
      </h1>

      <div className="toolbar halves-bar">
        <label className="check" title="Split each verse at its main accent pauses (etnahta; oleh-ve-yored in Psalms, Proverbs, Job)">
          <input type="checkbox" checked={halvesOn} onChange={(e) => update({ halves: e.target.checked ? '1' : null }, false)} />
          Verse halves (te'amim)
        </label>
        {halvesOn && halves.data && halves.data.n_scored > 0 && (
          <span className="muted small">
            ∥ marks verses whose halves are parallel like poetry
            {!isVerse && halves.data.share_parallel !== null && ` · ${Math.round(halves.data.share_parallel * 100)}% of this ${unitTypeLabel(unit.unit_type).toLowerCase()}`}
          </span>
        )}
      </div>
      <section className={`source ${isVerse ? 'single' : ''}`} aria-label="Source text">
        {isVerse ? (
          <p className="source-text">
            <HebrewText
              verse={verses[0]}
              highlight={highlightFor(explain.data, 'a', focusLemma)}
              onWordClick={pick(verses[0])}
              selected={selectedIn(verses[0])}
              breaks={breaksOf(verses[0])}
            />
            {halvesOn && <ParallelBadge h={halvesOf.get(verses[0].verse_id)} at={halves.data?.parallel_at} />}
          </p>
        ) : (
          <ol className="verse-list">
            {verses.map((v) => (
              <li key={v.verse_id}>
                <Link className="verse-num" to={unitLink(`v:${v.verse_id}`)} title={`${v.ref}: similar verses`}>
                  {v.verse}
                </Link>
                <HebrewText
                  verse={v}
                  highlight={leitwortMarks(v)}
                  onWordClick={pick(v)}
                  selected={selectedIn(v)}
                  breaks={breaksOf(v)}
                />
                {halvesOn && <ParallelBadge h={halvesOf.get(v.verse_id)} at={halves.data?.parallel_at} />}
              </li>
            ))}
          </ol>
        )}
      </section>
      {word ? (
        <WordPanel verse={word.verse} displayIdx={word.idx} onClose={() => setWord(undefined)} />
      ) : (
        <p className="muted small hint">Click a word for its morphology and concordance.</p>
      )}

      {!isVerse && (
        <details
          className="structure"
          open={structureOpen}
          onToggle={(e) => {
            const open = (e.currentTarget as HTMLDetailsElement).open
            if (open !== structureOpen) update({ structure: open ? '1' : null })
            if (!open) setLeitwort(undefined)
          }}
        >
          <summary>Structure: inclusio, chiasm, Leitworte</summary>
          {structureOpen && (
            <StructurePanel
              unitId={unit.unit_id}
              verses={verses}
              lemma={leitwort?.lemma}
              onLemma={(_, k) => setLeitwort(k && k.lemma !== leitwort?.lemma ? k : undefined)}
            />
          )}
        </details>
      )}

      <section className="results" aria-label="Similar units">
        <div className="results-head">
          <h2>Similar {unit.unit_type === 'parasha' ? 'parashot' : `${unit.unit_type}s`}</h2>
          <div className="toolbar">
            <ModeToggle value={mode} onChange={(m) => update({ mode: m === DEFAULT_MODE ? null : m })} />
            <KSelect value={k} onChange={(v) => update({ k: v === DEFAULT_K ? null : String(v) })} />
            <ExcludeFilters type={unit.unit_type} value={exclude} onChange={(v) => update({ exclude: v.join(',') })} />
          </div>
          <p className="muted small">{MODE_HINTS[mode]}</p>
        </div>
        {similar.isPending ? (
          <Loading />
        ) : similar.error ? (
          <ErrorBox error={similar.error} />
        ) : similar.data.hits.length === 0 ? (
          <p className="status">No results left after the filters.</p>
        ) : (
          <ol className={`hits ${similar.isPlaceholderData ? 'stale' : ''}`}>
            {similar.data.hits.map((hit) => {
              const tgt = hit.unit.start_verse_id
              return (
                <HitCard
                  key={hit.unit.unit_id}
                  hit={hit}
                  mode={similar.data.mode}
                  source={unit}
                  active={activeTgt === tgt}
                  pinned={pinned === tgt}
                  explain={explain.data?.b === tgt ? explain.data : undefined}
                  explainLoading={explain.isFetching}
                  focusLemma={focusLemma}
                  onHover={(on) => onHover(tgt, on)}
                  onTogglePin={() => setPinned(pinned === tgt ? undefined : tgt)}
                  onFocusLemma={setFocusLemma}
                />
              )
            })}
          </ol>
        )}
      </section>

      {isVerse && phrases.data && phrases.data.length > 0 && (
        <section className="results" aria-label="Shared phrases">
          <h2>
            Shared phrases <span className="muted small">({phrases.data.length})</span>
          </h2>
          <p className="muted small">Verses that share an aligned run of lemmas with this one (rare words weigh more).</p>
          <ol className="disc-list">
            {phrases.data.map((p) => (
              <PhraseCard key={p.b.unit_id} p={p} />
            ))}
          </ol>
        </section>
      )}

      {sequences.data && sequences.data.total > 0 && (
        <section className="results" aria-label="Parallel sequences">
          <h2>
            Runs parallel to <span className="muted small">({sequences.data.total})</span>
          </h2>
          <p className="muted small">
            Passages that follow this one verse by verse in the same order (q ≤ {SEQUENCE_MAX_Q}).{' '}
            <Link to="/sequences">All sequences</Link>
          </p>
          <ol className="disc-list">
            {sequences.data.items.map((s) => (
              <SequenceCard key={s.seq_id} s={s} />
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

/** Display indexes ending a colon (every colon but the last). */
function colonBreaks(h: VerseHalves | undefined): Set<number> | undefined {
  return h && h.n_cola > 1 ? new Set(h.cola.slice(0, -1).map(([, end]) => end)) : undefined
}

function ParallelBadge({ h, at }: { h?: VerseHalves; at?: number }) {
  if (!h || h.prob === null || at === undefined || h.prob < at) return null
  const tip =
    `Parallel halves: p = ${h.prob.toFixed(2)} · meaning ${h.cos?.toFixed(2)} · shared lemmas ${h.shared}` +
    ` · grammar ${h.shape?.toFixed(2)} · balance ${h.balance?.toFixed(2)}`
  return (
    <span className="parallel-badge" title={tip}>
      ∥
    </span>
  )
}

function Crumbs({ detail, search }: { detail: UnitDetail; search: string }) {
  const { unit, parents, prev_id, next_id } = detail
  const label = (u: UnitSummary) => `${unitTypeLabel(u.unit_type)} ${u.label_en}`
  return (
    <nav className="crumbs" aria-label="Context">
      <Link to={`/browse/${unit.book_id}`}>Book</Link>
      {parents.map((p) => (
        <span key={p.unit_id}>
          {' · '}
          <Link to={unitLink(p.unit_id)}>{label(p)}</Link>
        </span>
      ))}
      <span className="prevnext">
        {prev_id ? (
          <Link to={unitLink(prev_id, search)} rel="prev">
            ← Previous
          </Link>
        ) : (
          <span className="muted">← Previous</span>
        )}
        {next_id ? (
          <Link to={unitLink(next_id, search)} rel="next">
            Next →
          </Link>
        ) : (
          <span className="muted">Next →</span>
        )}
      </span>
    </nav>
  )
}
