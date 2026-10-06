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
import { DatingLine } from '../components/DatingLine'
import { ThemesPanel } from '../components/ThemesPanel'
import { SyntaxPanel } from '../components/SyntaxPanel'
import { WordPanel } from '../components/WordPanel'
import { WordplayCard } from '../components/WordplayCard'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale, useT } from '../context/localeContext'
import { nameLink, unitLink } from '../lib/links'
import { unitLabel, verseRef } from '../lib/names'
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
  const { m, locale } = useLocale()
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
  const syntaxOpen = params.get('syntax') === '1'
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
        <UnitName en={unit.label_en} he={unit.label_he} big spaced />
        <span className="type-tag">{m.units.type(unit.unit_type)}</span>
      </h1>

      <div className="toolbar halves-bar">
        <label className="check" title={m.unit.halvesTitle}>
          <input type="checkbox" checked={halvesOn} onChange={(e) => update({ halves: e.target.checked ? '1' : null }, false)} />
          {m.unit.halves}
        </label>
        {halvesOn && (
          <label className="check" title={m.unit.clausesTitle}>
            <input type="checkbox" checked={clausesOn} onChange={(e) => update({ clauses: e.target.checked ? '1' : null }, false)} />
            {m.unit.clauses}
          </label>
        )}
        {halvesOn && halves.isPending && (
          <span className="muted small" role="status">
            {m.unit.loadingHalves}
          </span>
        )}
        {halvesOn && halves.error && <PanelError what={m.unit.theHalves} error={halves.error} />}
        {halvesOn && halves.data && halves.data.n_scored > 0 && (
          <span className="muted small">
            {m.unit.parallelHalves}
            {!isVerse && halves.data.share_parallel !== null && m.unit.shareOf(halves.data.share_parallel, unit.unit_type)}
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
      <section className={`source ${isVerse ? 'single' : ''}`} aria-label={m.unit.source}>
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
                <Link className="verse-num" to={unitLink(`v:${v.verse_id}`)} title={m.units.similarVerses(verseRef(v, locale))}>
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
      {names.error && <PanelError what={m.unit.theNames} error={names.error} />}
      {names.data && names.data.length > 0 && (
        <p className="unit-names" aria-label={m.unit.namesLabel}>
          <span className="muted small">{m.unit.names}</span>
          {names.data.map((e) => (
            <Link key={e.lemma} to={nameLink(e.lemma)} className={`name-chip kind-${e.kind}`} title={m.unit.nameTitle(e.n_here, e.n_mentions)}>
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
          {m.unit.network(
            network.data.rank,
            network.data.of,
            unit.unit_type,
            network.data.node.partners,
            network.data.node.cross_book,
          )}
          <Link to={`/network?type=${unit.unit_type}&unit=${encodeURIComponent(unit.unit_id)}`}>
            {m.unit.community(network.data.community_size)}
          </Link>
        </p>
      )}
      {!isVerse && <ThemesPanel unitId={unit.unit_id} />}
      {unit.unit_type === 'chapter' && <DatingLine unitId={unit.unit_id} bookId={unit.book_id} />}
      {word ? (
        <WordPanel verse={word.verse} displayIdx={word.idx} onClose={() => setWord(undefined)} />
      ) : (
        <p className="muted small hint">{m.word.clickHint}</p>
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
          <summary>{m.unit.structure}</summary>
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

      <details
        className="structure syntax"
        open={syntaxOpen}
        onToggle={(e) => {
          const open = (e.currentTarget as HTMLDetailsElement).open
          if (open !== syntaxOpen) update({ syntax: open ? '1' : null })
        }}
      >
        <summary>{m.syn.panel}</summary>
        {syntaxOpen && <SyntaxPanel unitId={unit.unit_id} />}
      </details>

      <section className="results" aria-label={m.unit.similar}>
        <div className="results-head">
          <h2>{m.unit.similarOf(unit.unit_type)}</h2>
          <div className="toolbar">
            <ModeToggle value={mode} onChange={(m) => update({ mode: m === DEFAULT_MODE ? null : m })} />
            <KSelect value={k} onChange={(v) => update({ k: v === DEFAULT_K ? null : String(v) })} />
            <ExcludeFilters type={unit.unit_type} value={exclude} onChange={(v) => update({ exclude: v.join(',') })} />
            {isVerse && (
              <Segmented
                label={m.hit.markBy}
                value={marks}
                onChange={(v) => update({ marks: v === 'changes' ? v : null }, false)}
                options={[
                  { value: 'shared', label: m.hit.sharedWords },
                  { value: 'changes', label: m.hit.changes },
                ]}
              />
            )}
          </div>
          {similar.data && similar.data.hits.length > 1 && (
            <p className="muted small">
              {m.unit.keys} <kbd>j</kbd> / <kbd>k</kbd> {m.unit.keysNext}
              {isVerse ? m.unit.keysMarked : ''}.
            </p>
          )}
          <p className="muted small">{m.modes.hints[mode]}</p>
        </div>
        {similar.isPending ? (
          <Loading />
        ) : similar.error ? (
          <ErrorBox error={similar.error} />
        ) : similar.data.hits.length === 0 ? (
          <p className="status">{m.unit.noResults}</p>
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

      {isVerse && phrases.error && <PanelError what={m.unit.theSharedPhrases} error={phrases.error} />}
      {isVerse && phrases.data && phrases.data.total > 0 && (
        <section className="results" aria-label={m.unit.sharedPhrases}>
          <h2>
            {m.unit.sharedPhrases} <span className="muted small">({phrases.data.total})</span>
          </h2>
          <p className="muted small">
            {m.unit.phrasesLede}
            {phrases.data.total > phrases.data.items.length && m.unit.strongestShown(phrases.data.items.length)}.
          </p>
          <ol className="disc-list">
            {phrases.data.items.map((p) => (
              <PhraseCard key={p.b.unit_id} p={p} />
            ))}
          </ol>
        </section>
      )}

      {wordplay.error && <PanelError what={m.unit.theWordplay} error={wordplay.error} />}
      {wordplay.data && wordplay.data.total > 0 && (
        <section className="results" aria-label={m.unit.wordplay}>
          <h2>
            {m.unit.wordplay} <span className="muted small">({wordplay.data.total})</span>
          </h2>
          <p className="muted small">
            {m.unit.wordplayLede}{' '}
            <Link to={`/wordplay?unit=${encodeURIComponent(unit.unit_id)}`}>
              {wordplay.data.total > wordplay.data.items.length ? m.unit.allHere(wordplay.data.total) : m.unit.inWordplay}
            </Link>
          </p>
          <ol className="disc-list">
            {wordplay.data.items.map((p) => (
              <WordplayCard key={`${p.a_vid}:${p.a_display}|${p.b_vid}:${p.b_display}`} p={p} />
            ))}
          </ol>
        </section>
      )}

      {sequences.error && <PanelError what={m.unit.theSequences} error={sequences.error} />}
      {sequences.data && sequences.data.total > 0 && (
        <section className="results" aria-label={m.unit.runsLabel}>
          <h2>
            {m.unit.runs} <span className="muted small">({sequences.data.total})</span>
          </h2>
          <p className="muted small">
            {m.unit.runsLede(SEQUENCE_MAX_Q)}{' '}
            <Link to={`/sequences?unit=${encodeURIComponent(unit.unit_id)}&q=${SEQUENCE_MAX_Q}`}>
              {sequences.data.total > sequences.data.items.length ? m.unit.allHere(sequences.data.total) : m.unit.inSequences}
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
  const m = useT()
  return (
    <div className="toolbar acrostic-bar" role="note">
      <span>
        <b>{m.unit.acrostic}</b>
        {m.unit.acrosticLetters(a.n_letters, a.first_letter, a.last_letter)}
        {a.missing > 0 && m.unit.skipped(a.missing)}, {m.granularity[a.granularity]}
        {a.order_name === 'pe-ayin' && m.unit.peAyin} · <span className="q-strong">{m.q(a.q)}</span>
      </span>
      <label className="check">
        <input type="checkbox" checked={on} onChange={(e) => onToggle(e.target.checked)} />
        {m.unit.markLetters}
      </label>
      <Link to="/acrostics">{m.unit.allAcrostics}</Link>
    </div>
  )
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
  const m = useT()
  if (h && at !== undefined && h.next_prob != null && h.next_prob >= at)
    return (
      <span className="parallel-badge" title={m.unit.nextVerseTitle(h.next_prob.toFixed(2))}>
        ∥↓
      </span>
    )
  if (!h || h.prob === null || at === undefined || h.prob < at) return null
  const p = m.pat.poetry
  const typed = h.relation
    ? ` · ${p.relations[h.relation]}: ${h.relation_pairs.map((r) => `${r.a_he} / ${r.b_he} (${p.pairKinds[r.kind]})`).join(', ')}`
    : ''
  const tip =
    m.unit.halvesTip(
      h.prob.toFixed(2),
      String(h.cos?.toFixed(2)),
      h.shared,
      String(h.shape?.toFixed(2)),
      String(h.balance?.toFixed(2)),
    ) + typed
  return (
    <span className={`parallel-badge ${h.relation === 'antithetic' ? 'antithetic' : ''}`} title={tip}>
      {h.relation === 'antithetic' ? '∥≠' : '∥'}
    </span>
  )
}

function Crumbs({ detail, search }: { detail: UnitDetail; search: string }) {
  const { m, locale } = useLocale()
  const { unit, parents, prev_id, next_id } = detail
  const label = (u: UnitSummary) => `${m.units.type(u.unit_type)} ${unitLabel(u, locale)}`
  return (
    <nav className="crumbs" aria-label={m.units.context}>
      <Link to={`/browse/${unit.book_id}`}>{m.units.book}</Link>
      {parents.map((p) => (
        <span key={p.unit_id}>
          {' · '}
          <Link to={unitLink(p.unit_id)}>{label(p)}</Link>
        </span>
      ))}
      <span className="prevnext">
        {prev_id ? (
          <Link to={unitLink(prev_id, search)} rel="prev">
            {m.unit.previous}
          </Link>
        ) : (
          <span className="muted">{m.unit.previous}</span>
        )}
        {next_id ? (
          <Link to={unitLink(next_id, search)} rel="next">
            {m.unit.next}
          </Link>
        ) : (
          <span className="muted">{m.unit.next}</span>
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
