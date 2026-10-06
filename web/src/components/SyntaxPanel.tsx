import { Link } from 'react-router'
import { useUnitSyntax } from '../api/hooks'
import type { ClauseInfo } from '../api/types'
import { useLocale } from '../context/localeContext'
import { lemmaLink, unitLink } from '../lib/links'
import { HebrewPlain } from './HebrewText'
import { Loading, PanelError } from './Status'
import { UnitName } from './UnitName'

/**
 * A unit's BHSA clauses: type, phrases with their functions, and who speaks a quotation; for a
 * verse, the verses built the same way (DESIGN.md §16.26).
 */
export function SyntaxPanel({ unitId }: { unitId: string }) {
  const { m, locale } = useLocale()
  const t = m.syn
  const res = useUnitSyntax(unitId)
  if (res.error) return <PanelError what={t.panel} error={res.error} />
  if (!res.data) return <Loading />
  const { verses, neighbors } = res.data
  if (verses.length === 0) return <p className="muted small">{t.noData}</p>
  return (
    <div className="syntax-panel">
      <p className="muted small">{t.panelLede}</p>
      {verses.map((v) => (
        <div className="syntax-verse" key={v.verse_id}>
          {verses.length > 1 && <h3 className="syntax-ref">{locale === 'he' ? v.ref_he : v.ref}</h3>}
          <ol className="clauses">
            {v.clauses.map((c, i) => (
              <Clause key={i} c={c} showSpeaker={c.speech && !sameSpeaker(c, v.clauses[i - 1])} />
            ))}
          </ol>
        </div>
      ))}
      {neighbors.length > 0 && (
        <section aria-label={t.sameShape} className="same-shape">
          <h3>{t.sameShape}</h3>
          <p className="muted small">{t.sameShapeLede}</p>
          <ol>
            {neighbors.map((n) => (
              <li key={n.unit.unit_id}>
                <Link to={unitLink(n.unit.unit_id)}>
                  <UnitName en={n.unit.label_en} he={n.unit.label_he} />
                </Link>{' '}
                <HebrewPlain text={n.preview} className="small" />
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

const sameSpeaker = (a: ClauseInfo, b: ClauseInfo | undefined) =>
  b !== undefined && b.speech && b.speaker === a.speaker && b.speaker_source === a.speaker_source

function Clause({ c, showSpeaker }: { c: ClauseInfo; showSpeaker: boolean }) {
  const t = useLocale().m.syn
  const kind = c.txt.at(-1) ?? ''
  return (
    <li className={`clause ${c.speech ? 'speech' : ''} ${c.divine ? 'divine' : ''}`}>
      <span className="clause-type small" title={`${c.typ} · ${t.textTypes[kind] ?? kind}`}>
        {t.clauseType(c.typ)}
      </span>
      <span className="segments" dir="rtl" lang="he">
        {c.segments.map((s, j) => (
          <span className="seg" key={j}>
            <HebrewPlain text={s.text} />
            {s.function && (
              <span className="fn" dir="auto" title={s.function}>
                {t.fn(s.function)}
              </span>
            )}
          </span>
        ))}
      </span>
      {showSpeaker && (
        <span className="speaker small">
          {c.speaker && c.speaker_source ? (
            <Link to={lemmaLink(c.speaker)} title={t.speakerTitle[c.speaker_source]}>
              {t.speaker(c.speaker_source, c.speaker_he ?? c.speaker)}
            </Link>
          ) : (
            <span className="muted">{t.noSpeaker}</span>
          )}
        </span>
      )}
    </li>
  )
}
