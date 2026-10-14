import type { Breakdown, Mode } from '../api/types'
import { useT } from '../context/localeContext'
import { formatScore, rankFraction } from '../lib/format'

// Stored lists hold the top 50 per mode (retrieval.k): a rank bar spans that range.
const LIST_K = 50

function RankBar({ kind, rank, score }: { kind: 'lex' | 'sem' | 'phr'; rank: number | null; score: number | null }) {
  const m = useT()
  const label = m.rank[kind]
  const title = rank === null ? m.rank.notInTop(label, LIST_K) : m.rank.rank(label, rank, formatScore(score ?? 0))
  return (
    <div className="rankbar" title={title}>
      <span className="rankbar-label">{label}</span>
      <span className="rankbar-track">
        <span className={`rankbar-fill ${kind}`} style={{ width: `${rankFraction(rank, LIST_K) * 100}%` }} />
      </span>
      <span className="rankbar-rank">{rank === null ? '—' : `#${rank}`}</span>
    </div>
  )
}

/** Score, plus lexical vs semantic rank bars for fused results, and the phrase list's where the
 * unit type is fused with it (`phrases`, §16.50). */
export function ScoreBreakdown({ hit, mode, phrases = false }: { hit: Breakdown; mode: Mode; phrases?: boolean }) {
  const m = useT()
  return (
    <div className="breakdown">
      <span className="score" title={m.modes.score(m.modes.names[mode])}>
        {formatScore(hit.score)}
      </span>
      {mode === 'fused' && (
        <div className="rankbars">
          <RankBar kind="lex" rank={hit.lex_rank} score={hit.lex_score} />
          <RankBar kind="sem" rank={hit.sem_rank} score={hit.sem_score} />
          {phrases && <RankBar kind="phr" rank={hit.phr_rank} score={hit.phr_score} />}
        </div>
      )}
    </div>
  )
}
