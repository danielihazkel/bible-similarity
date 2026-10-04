import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { useExplain, useSimilar, useUnit } from '../api/hooks'
import type { UnitDetail, UnitSummary } from '../api/types'
import { ExcludeFilters, KSelect, ModeToggle } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { HitCard } from '../components/HitCard'
import { ErrorBox, Loading } from '../components/Status'
import { unitLink } from '../lib/links'
import { MODE_HINTS, unitTypeLabel } from '../lib/format'
import { highlightFor } from '../lib/highlight'
import { DEFAULT_K, DEFAULT_MODE, parseExclude, parseK, parseMode, useQueryParams } from '../lib/urlState'

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
  const isVerse = unit.unit_type === 'verse'
  const activeTgt = isVerse ? (pinned ?? hovered) : undefined
  const explain = useExplain(isVerse ? unit.start_verse_id : undefined, activeTgt)

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

      <section className={`source ${isVerse ? 'single' : ''}`} aria-label="Source text">
        {isVerse ? (
          <p className="source-text">
            <HebrewText verse={verses[0]} highlight={highlightFor(explain.data, 'a', focusLemma)} />
          </p>
        ) : (
          <ol className="verse-list">
            {verses.map((v) => (
              <li key={v.verse_id}>
                <Link className="verse-num" to={unitLink(`v:${v.verse_id}`)} title={`${v.ref}: similar verses`}>
                  {v.verse}
                </Link>
                <HebrewText verse={v} />
              </li>
            ))}
          </ol>
        )}
      </section>

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
    </div>
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
