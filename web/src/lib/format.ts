/** Scores differ per mode (BM25, CSLS, RRF): show 3 significant digits. */
export function formatScore(s: number): string {
  if (s === 0) return '0'
  const abs = Math.abs(s)
  return abs >= 100 ? s.toFixed(0) : abs >= 1 ? s.toPrecision(3) : s.toFixed(3)
}

/** Bar length for a rank in a stored top-`k` list: 1 at rank 1, falling linearly towards 0. */
export function rankFraction(rank: number | null, k: number): number {
  if (rank === null) return 0
  return Math.max(0, 1 - (rank - 1) / k)
}

/** Map a cosine to 0..1 for colouring: below `lo` is 0, at or above `hi` is 1. */
export function similarityLevel(cosine: number, lo = 0.3, hi = 0.9): number {
  return Math.min(1, Math.max(0, (cosine - lo) / (hi - lo)))
}

/** 5 discrete similarity bands (CSS classes `sim-0` … `sim-4`). */
export function similarityBand(cosine: number): number {
  return Math.min(4, Math.floor(similarityLevel(cosine) * 5))
}
