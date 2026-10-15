import type { ComponentType } from 'react'
import { Link, useNavigate } from 'react-router'
import { useBasemap, usePhrasesOf, usePlaces, useSequences, useUnitEntities, useUnitNetwork, useWordplay } from '../api/hooks'
import type { DossierKind, UnitSummary } from '../api/types'
import { useT } from '../context/localeContext'
import { fitBounds, geoPoints } from '../lib/geo'
import { nameLink } from '../lib/links'
import { DatingLine } from './DatingLine'
import { GeoMap } from './GeoMap'
import { PhraseCard } from './PhraseCard'
import { SequenceCard } from './SequenceCard'
import { PanelError } from './Status'
import { ThemesPanel } from './ThemesPanel'
import { WordplayCard } from './WordplayCard'

// Parallel sequences touching this unit: only reasonably strong chains, a few at most.
const SEQUENCE_MAX_Q = 0.2
const SEQUENCES_SHOWN = 5
const WORDPLAY_SHOWN = 5

export interface PanelProps {
  unit: UnitSummary
  /** False when the dossier says the panel's analysis found nothing here: nothing is fetched. */
  enabled: boolean
}

interface PanelSpec {
  id: string
  /** `context`: under the text, before the word panel; `after`: under the similar units. */
  slot: 'context' | 'after'
  /** The unit types the panel is shown for. */
  types: readonly UnitSummary['unit_type'][]
  /** The dossier entry that says whether there is anything to fetch. */
  dossier?: DossierKind
  Panel: ComponentType<PanelProps>
}

const PASSAGES = ['chapter', 'pericope', 'parasha'] as const
const ALL = ['verse', ...PASSAGES] as const

/** The unit page's data panels, in page order. Each fetches its own data. */
const UNIT_PANELS: readonly PanelSpec[] = [
  { id: 'names', slot: 'context', types: PASSAGES, Panel: NamesLine },
  { id: 'network', slot: 'context', types: PASSAGES, Panel: NetworkLine },
  { id: 'where', slot: 'context', types: ['chapter', 'pericope'], Panel: WhereThisHappens },
  { id: 'themes', slot: 'context', types: PASSAGES, Panel: ({ unit }) => <ThemesPanel unitId={unit.unit_id} /> },
  { id: 'dating', slot: 'context', types: ['chapter'], Panel: ({ unit }) => <DatingLine unitId={unit.unit_id} bookId={unit.book_id} /> },
  { id: 'phrases', slot: 'after', types: ['verse'], dossier: 'phrases', Panel: SharedPhrases },
  { id: 'wordplay', slot: 'after', types: ALL, dossier: 'wordplay', Panel: Wordplay },
  { id: 'sequences', slot: 'after', types: ALL, dossier: 'sequences', Panel: Sequences },
]

/** The registered panels of one slot for a unit; `has` says whether a dossier kind found anything. */
export function UnitPanels({ unit, slot, has }: { unit: UnitSummary; slot: PanelSpec['slot']; has: (kind: DossierKind) => boolean }) {
  return (
    <>
      {UNIT_PANELS.filter((p) => p.slot === slot && p.types.includes(unit.unit_type)).map(({ id, dossier, Panel }) => (
        <Panel key={id} unit={unit} enabled={dossier === undefined || has(dossier)} />
      ))}
    </>
  )
}

function NamesLine({ unit }: PanelProps) {
  const m = useT()
  const names = useUnitEntities(unit.unit_id)
  if (names.error) return <PanelError what={m.unit.theNames} error={names.error} />
  if (!names.data || names.data.length === 0) return null
  return (
    <p className="unit-names" id="unit-names" aria-label={m.unit.namesLabel}>
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
  )
}

function NetworkLine({ unit }: PanelProps) {
  const m = useT()
  const network = useUnitNetwork(unit.unit_id)
  if (!network.data) return null
  return (
    <p className="muted small unit-network">
      {m.unit.network(network.data.rank, network.data.of, unit.unit_type, network.data.node.partners, network.data.node.cross_book)}
      <Link to={`/network?type=${unit.unit_type}&unit=${encodeURIComponent(unit.unit_id)}`}>{m.unit.community(network.data.community_size)}</Link>
    </p>
  )
}

function SharedPhrases({ unit, enabled }: PanelProps) {
  const m = useT()
  const phrases = usePhrasesOf(enabled ? unit.start_verse_id : undefined)
  if (phrases.error) return <PanelError what={m.unit.theSharedPhrases} error={phrases.error} />
  if (!phrases.data || phrases.data.total === 0) return null
  return (
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
  )
}

function Wordplay({ unit, enabled }: PanelProps) {
  const m = useT()
  const wordplay = useWordplay({ unit: unit.unit_id, limit: WORDPLAY_SHOWN, offset: 0 }, enabled)
  if (wordplay.error) return <PanelError what={m.unit.theWordplay} error={wordplay.error} />
  if (!wordplay.data || wordplay.data.total === 0) return null
  return (
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
  )
}

function Sequences({ unit, enabled }: PanelProps) {
  const m = useT()
  const sequences = useSequences(
    { unit: unit.unit_id, direction: 'forward', maxQ: SEQUENCE_MAX_Q, limit: SEQUENCES_SHOWN, offset: 0 },
    enabled,
  )
  if (sequences.error) return <PanelError what={m.unit.theSequences} error={sequences.error} />
  if (!sequences.data || sequences.data.total === 0) return null
  return (
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
  )
}

/** The places a chapter or pericope names, on a small map fitted to them (§16.57). */
function WhereThisHappens({ unit }: PanelProps) {
  const m = useT()
  const t = m.pl
  const places = usePlaces({ unit: unit.unit_id })
  const basemap = useBasemap()
  const navigate = useNavigate()
  if (places.error) return <PanelError what={t.whereTitle} error={places.error} />
  const items = places.data?.items ?? []
  const points = geoPoints(items)
  const bounds = fitBounds(points, 1.5)
  if (!bounds) return null
  const open = (p?: number) => `/places?unit=${encodeURIComponent(unit.unit_id)}${p === undefined ? '' : `&p=${p}`}`
  return (
    <section className="where-panel" aria-label={t.whereTitle}>
      <h2>{t.whereTitle}</h2>
      <p className="muted small">
        {t.wherePlaces(items.length, items.length - points.length)} <Link to={open()}>{t.openMap}</Link>
      </p>
      <GeoMap basemap={basemap.data} points={points} bounds={bounds} onSelect={(p) => navigate(open(p))} label={t.whereTitle} labels={8} aspect={1.4} />
    </section>
  )
}
