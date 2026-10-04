import type { Breakdown, Mode } from '../api/types'
import { formatScore, rankFraction } from '../lib/format'

// Stored lists hold the top 50 per mode (retrieval.k): a rank bar spans that range.
const LIST_K = 50

function RankBar({ label, rank, score }: { label: string; rank: number | null; score: number | null }) {
  const title =
    rank === null ? `${label}: not in the top ${LIST_K}` : `${label}: rank ${rank}, score ${formatScore(score ?? 0)}`
  return (
    <div className="rankbar" title={title}>
      <span className="rankbar-label">{label}</span>
      <span className="rankbar-track">
        <span className={`rankbar-fill ${label.toLowerCase()}`} style={{ width: `${rankFraction(rank, LIST_K) * 100}%` }} />
      </span>
      <span className="rankbar-rank">{rank === null ? '—' : `#${rank}`}</span>
    </div>
  )
}

/** Score, plus lexical vs semantic rank bars for fused results. */
export function ScoreBreakdown({ hit, mode }: { hit: Breakdown; mode: Mode }) {
  return (
    <div className="breakdown">
      <span className="score" title={`${mode} score`}>
        {formatScore(hit.score)}
      </span>
      {mode === 'fused' && (
        <div className="rankbars">
          <RankBar label="Lex" rank={hit.lex_rank} score={hit.lex_score} />
          <RankBar label="Sem" rank={hit.sem_rank} score={hit.sem_score} />
        </div>
      )}
    </div>
  )
}
