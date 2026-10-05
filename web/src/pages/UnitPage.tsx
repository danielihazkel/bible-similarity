import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import {
  useExplain,
  usePhrasesOf,
  useSequences,
  useSimilar,
  useUnit,
  useUnitAcrostic,
  useUnitNetwork,
  useVerseDiff,
  useUnitEntities,
  useUnitParallelism,
  useWordplay,
} from '../api/hooks'
import type { Acrostic, Leitwort, UnitDetail, UnitSummary, Verse, VerseHalves } from '../api/types'
import { ExcludeFilters, KSelect, ModeToggle, Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { HitCard } from '../components/HitCard'
import { PhraseCard } from '../components/PhraseCard'
import { SequenceCard } from '../components/SequenceCard'
import { StructurePanel } from '../components/StructurePanel'
import { WordPanel } from '../components/WordPanel'
import { WordplayCard } from '../components/WordplayCard'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { nameLink, unitLink } from '../lib/links'
import { granularityLabel, MODE_HINTS, qLabel, unitTypeLabel } from '../lib/format'
import { diffHighlight, highlightFor, type Highlight } from '../lib/highlight'
import { DEFAULT_K, DEFAULT_MODE, parseExclude, parseK, parseMode, useQueryParams } from '../lib/urlState'

// Parallel sequences touching this unit: only reasonably strong chains, a few at most.
const SEQUENCE_MAX_Q = 0.2
const SEQUENCES_SHOWN = 5
const WORDPLAY_SHOWN = 5
const ACROSTIC_MAX_Q = 0.05

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
  // Acrostic (chapters): shown when significant; `?acrostic=1` marks the words carrying the letters.
  const acrosticQuery = useUnitAcrostic(unit.unit_type === 'chapter' ? unit.unit_id : undefined)
  const acrostic = acrosticQuery.data && acrosticQuery.data.q <= ACROSTIC_MAX_Q ? acrosticQuery.data : undefined
  const acrosticOn = !!acrostic && params.get('acrostic') === '1'
  const leitwortMarks = (v: Verse): Highlight | undefined => {
    const marks: Highlight = new Map()
    if (acrosticOn) for (const l of acrostic.chain) if (l.verse_id === v.verse_id) marks.set(l.display_idx, 'acrostic')
    if (leitwort) for (const i of leitwort.occurrences[v.verse_id] ?? []) marks.set(i, 'focus')
    return marks.size ? marks : undefined
  }
  const isVerse = unit.unit_type === 'verse'
  const activeTgt = isVerse ? (pinned ?? hovered) : undefined
  const marks = isVerse && params.get('marks') === 'changes' ? 'changes' : 'shared'
  const explain = useExplain(isVerse && marks === 'shared' ? unit.start_verse_id : undefined, activeTgt)
  const diff = useVerseDiff(unit.start_verse_id, activeTgt, isVerse && marks === 'changes')
  const diffData = diff.data && diff.data.b === activeTgt ? diff.data : undefined
  useHitKeys(similar.data?.hits.map((h) => h.unit.start_verse_id) ?? [], activeTgt, isVerse ? setPinned : undefined)
  const phrases = usePhrasesOf(isVerse ? unit.start_verse_id : undefined)
  const halvesOn = params.get('halves') === '1'
  const halves = useUnitParallelism(halvesOn ? unit.unit_id : undefined)
  const halvesOf = new Map((halves.data?.verses ?? []).map((h) => [h.verse_id, h]))
  const breaksOf = (v: Verse) => colonBreaks(halvesOf.get(v.verse_id))
  const clausesOn = halvesOn && params.get('clauses') === '1'
  const minorOf = (v: Verse) => (clausesOn ? clauseBreaks(halvesOf.get(v.verse_id)) : undefined)
  const names = useUnitEntities(isVerse ? undefined : unit.unit_id)
  const network = useUnitNetwork(isVerse ? undefined : unit.unit_id)
  const wordplay = useWordplay({ unit: unit.unit_id, limit: WORDPLAY_SHOWN, offset: 0 })
  const sequences = useSequences({
    unit: unit.unit_id,
    direction: 'forward',
    maxQ: SEQUENCE_MAX_Q,
    limit: SEQUENCES_SHOWN,
    offset: 0,
  })

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
        {halvesOn && (
          <label className="check" title="Also split at the weaker pauses (zaqef, segolta, tipeha; revia and tsinnor in poetry)">
            <input type="checkbox" checked={clausesOn} onChange={(e) => update({ clauses: e.target.checked ? '1' : null }, false)} />
            Finer clauses
          </label>
        )}
        {halvesOn && halves.isPending && (
          <span className="muted small" role="status">
            Loading verse halves…
          </span>
        )}
        {halvesOn && halves.error && <PanelError what="the verse halves" error={halves.error} />}
        {halvesOn && halves.data && halves.data.n_scored > 0 && (
          <span className="muted small">
            ∥ marks verses whose halves are parallel like poetry
            {!isVerse && halves.data.share_parallel !== null && ` · ${Math.round(halves.data.share_parallel * 100)}% of this ${unitTypeLabel(unit.unit_type).toLowerCase()}`}
          </span>
        )}
      </div>
      {acrostic && (
        <AcrosticBar
          a={acrostic}
          on={acrosticOn}
          onToggle={(on) => update({ acrostic: on ? '1' : null }, false)}
        />
      )}
      <section className={`source ${isVerse ? 'single' : ''}`} aria-label="Source text">
        {isVerse ? (
          <p className="source-text">
            <HebrewText
              verse={verses[0]}
              highlight={marks === 'changes' ? diffHighlight(diffData?.a_marks) : highlightFor(explain.data, 'a', focusLemma)}
              onWordClick={pick(verses[0])}
              selected={selectedIn(verses[0])}
              breaks={breaksOf(verses[0])}
              minorBreaks={minorOf(verses[0])}
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
                  minorBreaks={minorOf(v)}
                />
                {halvesOn && <ParallelBadge h={halvesOf.get(v.verse_id)} at={halves.data?.parallel_at} />}
              </li>
            ))}
          </ol>
        )}
      </section>
      {names.error && <PanelError what="the names in this unit" error={names.error} />}
      {names.data && names.data.length > 0 && (
        <p className="unit-names" aria-label="People and places">
          <span className="muted small">Names: </span>
          {names.data.map((e) => (
            <Link key={e.lemma} to={nameLink(e.lemma)} className={`name-chip kind-${e.kind}`} title={`${e.n_here} here, ${e.n_mentions} in all`}>
              <span dir="rtl" lang="he" className="he">
                {e.he}
              </span>
              <span className="muted small">{e.n_here}</span>
            </Link>
          ))}
        </p>
      )}
      {network.data && (
        <p className="muted small unit-network">
          Echo network: {ordinal(network.data.rank)} most echoed of {network.data.of}{' '}
          {unitTypeLabel(unit.unit_type).toLowerCase()}s · {network.data.node.partners} echoes,{' '}
          {Math.round(network.data.node.cross_book * 100)}% to other books ·{' '}
          <Link to={`/network?type=${unit.unit_type}&unit=${encodeURIComponent(unit.unit_id)}`}>
            its community of {network.data.community_size}
          </Link>
        </p>
      )}
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
            {isVerse && (
              <Segmented
                label="Mark words by"
                value={marks}
                onChange={(m) => update({ marks: m === 'changes' ? m : null }, false)}
                options={[
                  { value: 'shared', label: 'Shared words' },
                  { value: 'changes', label: 'Changes' },
                ]}
              />
            )}
          </div>
          {similar.data && similar.data.hits.length > 1 && (
            <p className="muted small">
              Keys: <kbd>j</kbd> / <kbd>k</kbd> next / previous hit
              {isVerse ? ' (its words marked)' : ''}.
            </p>
          )}
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
                  marks={marks}
                  diff={activeTgt === tgt ? diffData : undefined}
                />
              )
            })}
          </ol>
        )}
      </section>

      {isVerse && phrases.error && <PanelError what="shared phrases" error={phrases.error} />}
      {isVerse && phrases.data && phrases.data.total > 0 && (
        <section className="results" aria-label="Shared phrases">
          <h2>
            Shared phrases <span className="muted small">({phrases.data.total})</span>
          </h2>
          <p className="muted small">
            Verses that share an aligned run of lemmas with this one (rare words weigh more)
            {phrases.data.total > phrases.data.items.length && `; the strongest ${phrases.data.items.length} are shown`}.
          </p>
          <ol className="disc-list">
            {phrases.data.items.map((p) => (
              <PhraseCard key={p.b.unit_id} p={p} />
            ))}
          </ol>
        </section>
      )}

      {wordplay.error && <PanelError what="wordplay" error={wordplay.error} />}
      {wordplay.data && wordplay.data.total > 0 && (
        <section className="results" aria-label="Wordplay">
          <h2>
            Wordplay <span className="muted small">({wordplay.data.total})</span>
          </h2>
          <p className="muted small">
            Sound-alike words close together, rarest first.{' '}
            <Link to={`/wordplay?unit=${encodeURIComponent(unit.unit_id)}`}>
              {wordplay.data.total > wordplay.data.items.length ? `All ${wordplay.data.total} here` : 'In the wordplay list'}
            </Link>
          </p>
          <ol className="disc-list">
            {wordplay.data.items.map((p) => (
              <WordplayCard key={`${p.a_vid}:${p.a_display}|${p.b_vid}:${p.b_display}`} p={p} />
            ))}
          </ol>
        </section>
      )}

      {sequences.error && <PanelError what="parallel sequences" error={sequences.error} />}
      {sequences.data && sequences.data.total > 0 && (
        <section className="results" aria-label="Parallel sequences">
          <h2>
            Runs parallel to <span className="muted small">({sequences.data.total})</span>
          </h2>
          <p className="muted small">
            Passages that follow this one verse by verse in the same order (q ≤ {SEQUENCE_MAX_Q}).{' '}
            <Link to={`/sequences?unit=${encodeURIComponent(unit.unit_id)}&q=${SEQUENCE_MAX_Q}`}>
              {sequences.data.total > sequences.data.items.length ? `All ${sequences.data.total} here` : 'In the sequences list'}
            </Link>
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

function AcrosticBar({ a, on, onToggle }: { a: Acrostic; on: boolean; onToggle: (on: boolean) => void }) {
  return (
    <div className="toolbar acrostic-bar" role="note">
      <span>
        <b>Acrostic</b>: {a.n_letters} letters in alphabetical order, {a.first_letter}–{a.last_letter}
        {a.missing > 0 && ` (${a.missing} skipped)`}, {granularityLabel(a.granularity)}
        {a.order_name === 'pe-ayin' && ', פ before ע'} · <span className="q-strong">{qLabel(a.q)}</span>
      </span>
      <label className="check">
        <input type="checkbox" checked={on} onChange={(e) => onToggle(e.target.checked)} />
        Mark the letters
      </label>
      <Link to="/acrostics">All acrostics</Link>
    </div>
  )
}

const ordinal = (n: number) => {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${s}`
}

/** Display indexes ending a colon (every colon but the last). */
function colonBreaks(h: VerseHalves | undefined): Set<number> | undefined {
  return h && h.n_cola > 1 ? new Set(h.cola.slice(0, -1).map(([, end]) => end)) : undefined
}

/** Display indexes ending a clause that are not colon ends (every clause but the last). */
function clauseBreaks(h: VerseHalves | undefined): Set<number> | undefined {
  if (!h?.clauses || h.clauses.length < 2) return undefined
  const major = colonBreaks(h) ?? new Set<number>()
  return new Set(h.clauses.slice(0, -1).map(([, end]) => end).filter((e) => !major.has(e)))
}

function ParallelBadge({ h, at }: { h?: VerseHalves; at?: number }) {
  if (h && at !== undefined && h.next_prob != null && h.next_prob >= at)
    return (
      <span className="parallel-badge" title={`Parallel with the next verse (one bicolon over two verses): p = ${h.next_prob.toFixed(2)}`}>
        ∥↓
      </span>
    )
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

/**
 * j / k move to the next / previous similar unit: the card scrolls into view and takes focus,
 * and for verse units it is pinned so its words stay marked. Ignored while typing in a field.
 */
function useHitKeys(targets: number[], active: number | undefined, pin?: (t: number) => void) {
  const state = useRef({ targets, active, pin })
  useEffect(() => {
    state.current = { targets, active, pin }
  })
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'j' && e.key !== 'k') return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const t = e.target as HTMLElement | null
      if (t && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName))) return
      const { targets, active, pin } = state.current
      if (!targets.length) return
      const cards = document.querySelectorAll<HTMLElement>('ol.hits > li')
      const focused = [...cards].findIndex((c) => c.contains(document.activeElement))
      const at = active !== undefined ? targets.indexOf(active) : focused
      const next = Math.min(targets.length - 1, Math.max(0, at < 0 ? 0 : at + (e.key === 'j' ? 1 : -1)))
      e.preventDefault()
      pin?.(targets[next])
      const card = cards[next]
      if (card) {
        card.tabIndex = -1
        card.focus({ preventScroll: true })
        const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
        card.scrollIntoView({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' })
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])
}
