import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useStructure } from '../api/hooks'
import type { Leitwort, StructureBasis, StructureScore, Verse } from '../api/types'
import { useT } from '../context/localeContext'
import { compareLink } from '../lib/links'
import { Segmented } from './Controls'
import { ErrorBox, Loading } from './Status'

type Basis = 'semantic' | 'lexical'

interface Props {
  unitId: string
  verses: Verse[]
  lemma: string | undefined
  onLemma: (lemma: string | undefined, leitwort?: Leitwort) => void
}

/** Inner structure of a chapter / pericope / parasha: self-similarity heatmap, inclusio, chiasm,
 * internal echoes and Leitworte (DESIGN.md §16.2). */
export function StructurePanel({ unitId, verses, lemma, onLemma }: Props) {
  const m = useT()
  const t = m.pat.panel
  const res = useStructure(unitId)
  const [basis, setBasis] = useState<Basis>('semantic')
  if (res.isPending) return <Loading label={t.computing} />
  if (res.error) return <ErrorBox error={res.error} />
  const data = res.data[basis]
  const label = (vid: number) => {
    const v = verses.find((x) => x.verse_id === vid)
    return v ? m.cv(v.chapter, v.verse) : String(vid)
  }
  return (
    <div className="structure-panel">
      <div className="toolbar">
        <Segmented
          label={t.basis}
          value={basis}
          onChange={setBasis}
          options={[
            { value: 'semantic', label: m.modes.names.semantic, title: t.hints.semantic },
            { value: 'lexical', label: m.modes.names.lexical, title: t.hints.lexical },
          ]}
        />
        <span className="muted small">{t.verseByVerse(t.hints[basis])}</span>
      </div>
      <div className="structure-grid">
        <Heatmap basis={data} labels={res.data.verse_ids.map(label)} />
        <div className="structure-facts">
          <Fact title={t.inclusio} score={data.inclusio} label={label} hint={t.inclusioHint} />
          <Fact title={t.chiasm} score={data.chiasm} label={label} hint={t.chiasmHint} />
          <p className="muted small">{t.note}</p>
          <h3>{t.echoes}</h3>
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
          <h3>{t.leitworte}</h3>
          <p className="muted small">{t.leitworteLede}</p>
          <div className="chips">
            {res.data.leitworte.map((k) => (
              <button
                key={k.lemma}
                type="button"
                className={`chip ${lemma === k.lemma ? 'on' : ''}`}
                aria-pressed={lemma === k.lemma}
                title={t.leitwortTitle(k.count, k.expected.toFixed(1), k.g2.toFixed(0))}
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
  const t = useT().pat.panel
  return (
    <p className="fact">
      <strong>{title}</strong> <span className="muted small">({hint})</span>
      <br />
      {score === null ? (
        <span className="muted">{t.tooFew}</span>
      ) : (
        <>
          <span className={score.pct >= 0.95 ? 'fact-strong' : undefined}>{t.percentile(score.pct)}</span>
          {' · '}
          {score.pair ? `${label(score.pair[0])} ↔ ${label(score.pair[1])}, ` : t.meanMirror}
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

/** Canvas heatmap; mirror pairs outlined (the chiasm diagonal). Drawn at the screen's pixel
 * density; the mouse or, once focused, the arrow keys read out a cell. */
function Heatmap({ basis, labels }: { basis: StructureBasis; labels: string[] }) {
  const t = useT().pat.panel
  const ref = useRef<HTMLCanvasElement>(null)
  const [cursor, setCursor] = useState<[number, number]>()
  const n = basis.matrix.length
  const size = 360
  const cell = size / n
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
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
    const ink = `rgb(${cssColor('--text', [42, 34, 24]).join(',')})`
    ctx.strokeStyle = ink
    ctx.lineWidth = 1
    for (let i = 0; i < Math.floor(n / 2); i++) {
      const j = n - 1 - i
      if (j - i < 2) continue
      ctx.strokeRect(j * cell + 0.5, i * cell + 0.5, cell - 1, cell - 1)
      ctx.strokeRect(i * cell + 0.5, j * cell + 0.5, cell - 1, cell - 1)
    }
    if (cursor) {
      ctx.lineWidth = 2
      ctx.strokeRect(cursor[1] * cell + 1, cursor[0] * cell + 1, cell - 2, cell - 2)
    }
  }, [basis, n, cell, cursor])
  const keys: Record<string, [number, number]> = {
    ArrowUp: [-1, 0],
    ArrowDown: [1, 0],
    ArrowLeft: [0, -1],
    ArrowRight: [0, 1],
  }
  const clamp = (v: number) => Math.min(n - 1, Math.max(0, v))
  return (
    <figure className="heatmap" dir="ltr">
      <canvas
        ref={ref}
        style={{ width: size, height: size }}
        tabIndex={0}
        role="img"
        aria-label={t.heatmap}
        onFocus={() => setCursor((c) => c ?? [0, n - 1])}
        onBlur={() => setCursor(undefined)}
        onKeyDown={(e) => {
          const d = keys[e.key]
          if (!d) return
          e.preventDefault()
          setCursor(([i, j] = [0, 0]) => [clamp(i + d[0]), clamp(j + d[1])])
        }}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect()
          const j = Math.floor(((e.clientX - r.left) / r.width) * n)
          const i = Math.floor(((e.clientY - r.top) / r.height) * n)
          if (i >= 0 && j >= 0 && i < n && j < n) setCursor([i, j])
        }}
        onMouseLeave={() => setCursor(undefined)}
      />
      <figcaption className="muted small" aria-live="polite">
        {cursor
          ? `${labels[cursor[0]]} ↔ ${labels[cursor[1]]}: ${basis.matrix[cursor[0]][cursor[1]].toFixed(2)}`
          : t.heatmapKey}
      </figcaption>
    </figure>
  )
}
