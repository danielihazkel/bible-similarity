import { useState, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useParams } from 'react-router'
import { useReader, useStructure, useUnit, useUnitParallelism } from '../api/hooks'
import type { ReaderGap, ReaderResponse, ReaderSpeaker, ReaderVerse, UnitDetail, Verse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText, type WordLook } from '../components/HebrewText'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { WordPanel } from '../components/WordPanel'
import { useLocale, useT } from '../context/localeContext'
import type { Layer } from '../i18n/pages/reader'
import { clauseBreaks, colonBreaks } from '../lib/cola'
import { LAYERS, parseLayers, toggleLayer } from '../lib/layers'
import { readLink, unitLink } from '../lib/links'
import { verseRef } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

// the layers `/reader/{unit}` serves (cola come from /parallelism, Leitworte from /structure)
const READER_LAYERS: Layer[] = ['speakers', 'phrases', 'rare', 'wordplay', 'ketiv', 'turns']
const COMPUTED: Partial<Record<Layer, string>> = {
  speakers: 'speech',
  phrases: 'phrases',
  wordplay: 'wordplay',
  ketiv: 'ketiv',
  turns: 'gaps',
}
const LEITWORTE_SHOWN = 6
const SPEAKER_COLOURS = 8

/** The layered reader (§16.39): one unit with the analyses' word-level findings as layers. */
export function ReaderPage() {
  const unitId = useParams().unitId!
  const { search } = useLocation()
  const detail = useUnit(unitId)
  if (detail.isPending) return <Loading />
  if (detail.error) return <ErrorBox error={detail.error} />
  const { unit, verses } = detail.data
  // a verse is read in its chapter
  if (unit.unit_type === 'verse') return <Navigate replace to={readLink(`c:${unit.book_id}:${verses[0].chapter}`, search)} />
  return <ReaderView key={unitId} detail={detail.data} />
}

function ReaderView({ detail }: { detail: UnitDetail }) {
  const { m, locale } = useLocale()
  const t = m.reader
  const { unit, verses } = detail
  const [params, update] = useQueryParams()
  const { search } = useLocation()
  const layers = parseLayers(params.get('layers'))
  const on = (l: Layer) => layers.has(l)
  const byRoot = params.get('lw') === 'root'
  const reader = useReader(READER_LAYERS.some(on) ? unit.unit_id : undefined)
  const halves = useUnitParallelism(on('cola') ? unit.unit_id : undefined)
  const structure = useStructure(on('leitworte') ? unit.unit_id : undefined)
  const [word, setWord] = useState<{ verse: Verse; idx: number }>()

  const toggle = (l: Layer) => update({ layers: toggleLayer(layers, l) }, false)
  const rv = new Map((reader.data?.verses ?? []).map((v) => [v.verse_id, v]))
  const speakers = reader.data?.speakers ?? []
  const halvesOf = new Map((halves.data?.verses ?? []).map((h) => [h.verse_id, h]))
  const leitworte = (
    (byRoot ? structure.data?.root_leitworte : structure.data?.leitworte)?.map((l) => ({
      key: 'root' in l ? l.root : l.lemma,
      he: 'root' in l ? l.root_he : l.he_lemma,
      count: l.count,
      expected: l.expected,
      occurrences: l.occurrences,
    })) ?? []
  ).slice(0, LEITWORTE_SHOWN)
  const lwAt = new Map<string, number>()
  leitworte.forEach((l, k) => {
    for (const [v, idxs] of Object.entries(l.occurrences)) for (const i of idxs) if (!lwAt.has(`${v}:${i}`)) lwAt.set(`${v}:${i}`, k)
  })
  // the selected word's sound-alike partners
  const partners = new Set(
    word && on('wordplay')
      ? (rv.get(word.verse.verse_id)?.wordplay ?? []).filter((w) => w.display === word.idx).map((w) => `${w.partner_vid}:${w.partner_display}`)
      : [],
  )

  const decorate =
    (v: Verse, r: ReaderVerse | undefined) =>
    (i: number): WordLook | undefined => {
      const cls: string[] = []
      const titles: string[] = []
      const marks: string[] = []
      const s = on('speakers') ? r?.speech[i] : undefined
      if (s !== undefined && speakers[s]) {
        const sp = speakers[s]
        cls.push('spk', sp.lemma === null ? 'spk-unknown' : `spk-${s % SPEAKER_COLOURS}`)
        titles.push(t.spokenBy(sp.he ?? t.unknownSpeaker))
      }
      const lw = on('leitworte') ? lwAt.get(`${v.verse_id}:${i}`) : undefined
      if (lw !== undefined) {
        const l = leitworte[lw]
        cls.push('lw', `lw-${lw}`)
        titles.push(t.leitwortTitle(l.he, l.count, l.expected.toFixed(1)))
      }
      const ph = on('phrases') ? r?.phrases[i] : undefined
      if (ph !== undefined) {
        cls.push('ph', `ph-${ph >= 5 ? 3 : ph >= 2 ? 2 : 1}`)
        titles.push(t.phraseTitle(ph))
      }
      if (on('wordplay') && r) {
        for (const w of r.wordplay.filter((x) => x.display === i)) {
          titles.push(t.wordplayTitle(w.partner_form, locale === 'he' ? w.partner_label_he : w.partner_label, m.pat.wordplay.kinds[w.kind]))
          if (!cls.includes('wp')) cls.push('wp')
        }
        if (partners.has(`${v.verse_id}:${i}`)) cls.push('wp-partner')
      }
      const rare = on('rare') ? r?.rare[i] : undefined
      if (rare !== undefined) {
        marks.push(String(rare))
        titles.push(t.rareTitle(rare))
      }
      const kq = on('ketiv') ? r?.ketiv.find((k) => k.display.includes(i)) : undefined
      if (kq) {
        marks.push('ק')
        titles.push(t.ketivTitle(kq.ketiv, kq.qere, m.kq.classes[kq.cls].label))
      }
      if (!cls.length && !marks.length) return undefined
      return { className: cls.join(' '), title: titles.join('\n'), marks }
    }

  const pick = (verse: Verse) => (idx: number) =>
    setWord(word?.verse.verse_id === verse.verse_id && word.idx === idx ? undefined : { verse, idx })

  return (
    <div className="page reader-page">
      <nav className="crumbs" aria-label={m.units.context}>
        <Link to={`/browse/${unit.book_id}`}>{m.units.book}</Link>
        {' · '}
        <Link to={unitLink(unit.unit_id)}>{t.unitPage}</Link>
        <span className="prevnext">
          {detail.prev_id ? (
            <Link to={readLink(detail.prev_id, search)} rel="prev">
              {m.unit.previous}
            </Link>
          ) : (
            <span className="muted">{m.unit.previous}</span>
          )}
          {detail.next_id ? (
            <Link to={readLink(detail.next_id, search)} rel="next">
              {m.unit.next}
            </Link>
          ) : (
            <span className="muted">{m.unit.next}</span>
          )}
        </span>
      </nav>
      <h1>
        <UnitName en={unit.label_en} he={unit.label_he} big spaced />
        <span className="type-tag">{t.title}</span>
      </h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar layer-bar" role="group" aria-label={t.layersLabel}>
        {LAYERS.map((l) => (
          <button key={l} type="button" className={`layer-toggle ${on(l) ? 'on' : ''}`} aria-pressed={on(l)} title={t.hints[l]} onClick={() => toggle(l)}>
            {t.layers[l]}
          </button>
        ))}
      </div>
      <Legend
        layers={layers}
        reader={reader.data}
        speakers={speakers}
        leitworte={leitworte}
        byRoot={byRoot}
        hasRoots={!!structure.data?.root_leitworte.length}
        onByRoot={(r) => update({ lw: r ? 'root' : null }, false)}
      />
      {reader.isFetching && !reader.data && (
        <p className="muted small" role="status">
          {t.loading(t.layersLabel)}
        </p>
      )}
      {reader.error && <PanelError what={t.layersLabel} error={reader.error} />}
      {halves.error && <PanelError what={t.layers.cola} error={halves.error} />}
      {structure.error && <PanelError what={t.layers.leitworte} error={structure.error} />}
      <ol className="verse-list reader-text">
        {verses.map((v) => {
          const r = rv.get(v.verse_id)
          const h = on('cola') ? halvesOf.get(v.verse_id) : undefined
          return (
            <li key={v.verse_id}>
              {on('turns') && r?.gap && <GapRow gap={r.gap} />}
              <Link className="verse-num" to={unitLink(`v:${v.verse_id}`)} title={m.units.similarVerses(verseRef(v, locale))}>
                {v.verse}
              </Link>
              <HebrewText
                verse={v}
                decorate={decorate(v, r)}
                onWordClick={pick(v)}
                selected={word?.verse.verse_id === v.verse_id ? word.idx : undefined}
                breaks={colonBreaks(h)}
                minorBreaks={clauseBreaks(h)}
              />
            </li>
          )
        })}
      </ol>
      {word ? <WordPanel verse={word.verse} displayIdx={word.idx} onClose={() => setWord(undefined)} /> : <p className="muted small hint">{m.word.clickHint}</p>}
    </div>
  )
}

function GapRow({ gap }: { gap: ReaderGap }) {
  const t = useT().reader
  return (
    <div className={`reader-gap ${gap.kind ? `gap-${gap.kind}` : 'gap-mam'}`} title={t.gapTitle(gap.score)}>
      {gap.mam && (
        <span className="paragraph-mark" dir="rtl" lang="he" title={t.paragraphTitle[gap.mam]}>
          {gap.mam === 'pe' ? 'פ' : 'ס'}
        </span>
      )}
      {gap.kind && <span className="gap-kind">{t.gapKinds[gap.kind]}</span>}
    </div>
  )
}

interface LegendProps {
  layers: Set<Layer>
  reader: ReaderResponse | undefined
  speakers: ReaderSpeaker[]
  leitworte: { key: string; he: string; count: number }[]
  byRoot: boolean
  hasRoots: boolean
  onByRoot: (on: boolean) => void
}

/** One line per layer that is on: what its marks mean, its speakers or Leitworte. */
function Legend({ layers, reader, speakers, leitworte, byRoot, hasRoots, onByRoot }: LegendProps) {
  const m = useT()
  const t = m.reader
  const missing = (l: Layer) => reader && COMPUTED[l] && !reader.computed[COMPUTED[l]]
  const row = (l: Layer, body: ReactNode) =>
    layers.has(l) && (
      <li key={l} className={`legend-${l}`}>
        <b>{t.layers[l]}</b> {missing(l) ? <span className="muted">{t.notComputed(t.layers[l])}</span> : body}
      </li>
    )
  return (
    <ul className="reader-legend small" aria-label={t.layersLabel}>
      {row(
        'speakers',
        speakers.length === 0 ? (
          <span className="muted">{reader ? t.noSpeech : ''}</span>
        ) : (
          <>
            {t.speakersKey}{' '}
            {speakers.map((s, k) => (
            <span key={s.lemma ?? 'unknown'} className={`layer-key spk ${s.lemma === null ? 'spk-unknown' : `spk-${k % SPEAKER_COLOURS}`}`}>
              {s.he ? (
                <span dir="rtl" lang="he">
                  {s.he}
                </span>
              ) : (
                t.unknownSpeaker
              )}
              {s.divine && ` (${t.divine})`} <span className="layer-n">{t.speakerWords(s.n_words)}</span>
            </span>
          ))}
          </>
        ),
      )}
      {row('cola', t.colaKey)}
      {row(
        'leitworte',
        <>
          {hasRoots && (
            <Segmented
              label={t.countBy}
              value={byRoot ? 'root' : 'word'}
              onChange={(v) => onByRoot(v === 'root')}
              options={[
                { value: 'word', label: t.byWord },
                { value: 'root', label: t.byRoot },
              ]}
            />
          )}{' '}
          {leitworte.length === 0 ? (
            <span className="muted">{t.noLeitworte}</span>
          ) : (
            <>
              {t.leitworteKey}{' '}
              {leitworte.map((l, k) => (
                <span key={l.key} className={`layer-key lw lw-${k}`}>
                  <span dir="rtl" lang="he">
                    {l.he}
                  </span>{' '}
                  <span className="layer-n">{l.count}</span>
                </span>
              ))}
            </>
          )}
        </>,
      )}
      {row('phrases', t.phrasesKey)}
      {row('rare', reader ? t.rareKey(reader.rare_verses) : '')}
      {row('wordplay', t.wordplayKey)}
      {row('ketiv', t.ketivKey)}
      {row('turns', t.turnsKey)}
    </ul>
  )
}
