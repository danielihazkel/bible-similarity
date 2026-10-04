import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useStructure } from '../api/hooks'
import type { Leitwort, StructureBasis, StructureScore, Verse } from '../api/types'
import { compareLink } from '../lib/links'
import { Segmented } from './Controls'
import { ErrorBox, Loading } from './Status'

type Basis = 'semantic' | 'lexical'

const BASIS_HINT: Record<Basis, string> = {
  semantic: 'cosine of the semantic verse embeddings',
  lexical: 'cosine of idf-weighted lemma bags (shared rare words)',
}

const pct = (p: number) => `${Math.round(p * 100)}th percentile`

interface Props {
  unitId: string
  verses: Verse[]
  lemma: string | undefined
  onLemma: (lemma: string | undefined, leitwort?: Leitwort) => void
}

/** Inner structure of a chapter / pericope / parasha: self-similarity heatmap, inclusio, chiasm,
 * internal echoes and Leitworte (DESIGN.md §16.2). */
export function StructurePanel({ unitId, verses, lemma, onLemma }: Props) {
  const res = useStructure(unitId)
  const [basis, setBasis] = useState<Basis>('semantic')
  if (res.isPending) return <Loading label="Computing structure…" />
  if (res.error) return <ErrorBox error={res.error} />
  const data = res.data[basis]
  const label = (vid: number) => {
    const v = verses.find((x) => x.verse_id === vid)
    return v ? `${v.chapter}:${v.verse}` : String(vid)
  }
  return (
    <div className="structure-panel">
      <div className="toolbar">
        <Segmented
          label="Similarity basis"
          value={basis}
          onChange={setBasis}
          options={[
            { value: 'semantic', label: 'Semantic', title: BASIS_HINT.semantic },
            { value: 'lexical', label: 'Lexical', title: BASIS_HINT.lexical },
          ]}
        />
        <span className="muted small">Verse × verse similarity: {BASIS_HINT[basis]}.</span>
      </div>
      <div className="structure-grid">
        <Heatmap basis={data} labels={res.data.verse_ids.map(label)} />
        <div className="structure-facts">
          <Fact title="Inclusio" score={data.inclusio} label={label} hint="opening and closing verses echo each other" />
          <Fact title="Chiasm" score={data.chiasm} label={label} hint="mirror pairs (1st ↔ last, 2nd ↔ second-to-last …) are more alike than other pairs at the same distance" />
          <p className="muted small">
            Percentiles compare the unit with itself (random pairs of the same unit). Across thousands of units some reach the
            95th by chance: treat them as leads to read.
          </p>
          <h3>Strongest internal echoes</h3>
          <ol className="echoes">
            {data.echoes.map((e) => (
              <li key={`${e.a}-${e.b}`}>
                <Link to={compareLink(`v:${e.a}`, `v:${e.b}`)}>
                  {label(e.a)} ↔ {label(e.b)}
                </Link>{' '}
                <span className="muted small">{e.sim.toFixed(2)}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
      {res.data.leitworte.length > 0 && (
        <div className="leitworte">
          <h3>Leitworte</h3>
          <p className="muted small">Lemmas this unit uses far more than the rest of the Tanakh (log-likelihood). Click to highlight.</p>
          <div className="chips">
            {res.data.leitworte.map((k) => (
              <button
                key={k.lemma}
                type="button"
                className={`chip ${lemma === k.lemma ? 'on' : ''}`}
                aria-pressed={lemma === k.lemma}
                title={`${k.count} times here, ${k.expected.toFixed(1)} expected · G² ${k.g2.toFixed(0)}`}
                onClick={() => onLemma(lemma === k.lemma ? undefined : k.lemma, k)}
              >
                <span dir="rtl" lang="he">
                  {k.he_lemma}
                </span>{' '}
                <span className="small">×{k.count}</span>
                {k.multiple_of.length > 0 && <span className="multiple"> ({k.multiple_of.map((m) => `${m}·${k.count / m}`).join(', ')})</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Fact({ title, score, label, hint }: { title: string; score: StructureScore | null; label: (v: number) => string; hint: string }) {
  return (
    <p className="fact">
      <strong>{title}</strong> <span className="muted small">({hint})</span>
      <br />
      {score === null ? (
        <span className="muted">Too few verses.</span>
      ) : (
        <>
          <span className={score.pct >= 0.95 ? 'fact-strong' : undefined}>{pct(score.pct)}</span>
          {' · '}
          {score.pair ? `${label(score.pair[0])} ↔ ${label(score.pair[1])}, ` : 'mean mirror similarity '}
          {score.value.toFixed(2)}
          {score.z !== null && score.z !== undefined && ` · z ${score.z.toFixed(1)}`}
        </>
      )}
    </p>
  )
}

function cssColor(name: string, fallback: [number, number, number]): [number, number, number] {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  const m = /^#([0-9a-f]{6})$/i.exec(v)
  if (!m) return fallback
  const n = parseInt(m[1], 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** Canvas heatmap; mirror pairs outlined (the chiasm diagonal). */
function Heatmap({ basis, labels }: { basis: StructureBasis; labels: string[] }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [hover, setHover] = useState<string>()
  const n = basis.matrix.length
  const size = 360
  const cell = size / n
  useEffect(() => {
    const ctx = ref.current?.getContext('2d')
    if (!ctx) return
    const off = basis.matrix.flatMap((row, i) => row.filter((_, j) => j !== i))
    const lo = Math.min(...off)
    const hi = Math.max(...off)
    const a = cssColor('--surface-2', [243, 236, 223])
    const b = cssColor('--accent', [138, 90, 31])
    ctx.clearRect(0, 0, size, size)
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) {
        const t = i === j ? 1 : hi > lo ? (basis.matrix[i][j] - lo) / (hi - lo) : 0
        ctx.fillStyle = `rgb(${a.map((c, k) => Math.round(c + (b[k] - c) * t)).join(',')})`
        ctx.fillRect(j * cell, i * cell, Math.ceil(cell), Math.ceil(cell))
      }
    ctx.strokeStyle = `rgb(${cssColor('--text', [42, 34, 24]).join(',')})`
    ctx.lineWidth = 1
    for (let i = 0; i < Math.floor(n / 2); i++) {
      const j = n - 1 - i
      if (j - i < 2) continue
      ctx.strokeRect(j * cell + 0.5, i * cell + 0.5, cell - 1, cell - 1)
      ctx.strokeRect(i * cell + 0.5, j * cell + 0.5, cell - 1, cell - 1)
    }
  }, [basis, n, cell])
  return (
    <figure className="heatmap">
      <canvas
        ref={ref}
        width={size}
        height={size}
        role="img"
        aria-label="Verse-by-verse similarity heatmap"
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect()
          const j = Math.floor(((e.clientX - r.left) / r.width) * n)
          const i = Math.floor(((e.clientY - r.top) / r.height) * n)
          if (i >= 0 && j >= 0 && i < n && j < n) setHover(`${labels[i]} ↔ ${labels[j]}: ${basis.matrix[i][j].toFixed(2)}`)
        }}
        onMouseLeave={() => setHover(undefined)}
      />
      <figcaption className="muted small">{hover ?? 'Darker = more similar · outlined cells = mirror pairs'}</figcaption>
    </figure>
  )
}
