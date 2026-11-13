import { useState } from 'react'
import { useBooks, useVocabulary } from '../api/hooks'
import type { Book, VocabularyBook, VocabularyResponse } from '../api/types'
import { isStageMissing } from '../api/client'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import { x2 } from '../i18n/pages/vocabulary'
import '../styles/pages/VocabularyPage.css'

/** The vocabulary over the canon (§16.76): each book's new lemmas against Heaps' law and random
 * orders of the books, words found once, and the checks. */
export function VocabularyPage() {
  const { m } = useLocale()
  const t = m.vc
  const res = useVocabulary()
  const books = useBooks()
  const d = res.data
  return (
    <div className="page vocabulary-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {isStageMissing(res.error) ? (
        <NotComputed>{t.notComputed}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <Checks d={d} books={books.data} />
          <NoveltyChart d={d} books={books.data} />
          <BookTable d={d} books={books.data} />
        </>
      )}
    </div>
  )
}

function useBookName(books: Book[] | undefined) {
  const { locale } = useLocale()
  const by = new Map((books ?? []).map((b) => [b.book_id, b]))
  return (id: number) => {
    const b = by.get(id)
    return b ? (locale === 'he' ? b.he_name : b.name) : String(id)
  }
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.vc
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d, books }: { d: VocabularyResponse; books: Book[] | undefined }) {
  const t = useLocale().m.vc
  const name = useBookName(books)
  const one = d.one_corpus
  return (
    <section aria-labelledby="vc-checks">
      <h2 id="vc-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.late.title} <Verdict holds={d.late_holds} />
          </h3>
          <p>{t.late.text(d.late_novelty, d.early_novelty, d.late_p, d.splits)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <ul className="vc-known">
            {d.known.map((k) => (
              <li key={k.book}>{t.known.rank(name(k.book_id), k.rank, k.at_most)}</li>
            ))}
          </ul>
        </article>
      </div>
      <p className="muted small">{t.described(d.words, d.lemmas, d.hapax, d.heaps_k, d.heaps_b)}</p>
      <p className="muted small">{t.oneCorpus(one.Torah ?? 0, one.Prophets ?? 0, one.Writings ?? 0)}</p>
    </section>
  )
}

const ROW = 15
const PAD = { l: 92, r: 12, t: 8, b: 22 }
const W = 560

/** Each book's novelty as a bar from zero, in canon order; the early and late books coloured, the
 * others neutral. Hovering or focusing a row reads its numbers out below the legend. */
function NoveltyChart({ d, books }: { d: VocabularyResponse; books: Book[] | undefined }) {
  const { m } = useLocale()
  const t = m.vc
  const name = useBookName(books)
  const [hover, setHover] = useState<VocabularyBook | null>(null)
  const max = Math.max(0.5, ...d.books.map((b) => Math.abs(b.novelty)))
  const lim = Math.ceil(max * 2) / 2
  const H = PAD.t + d.books.length * ROW + PAD.b
  const x = (v: number) => PAD.l + ((v + lim) / (2 * lim)) * (W - PAD.l - PAD.r)
  const ticks = [-lim, -lim / 2, 0, lim / 2, lim]
  const shown = hover ?? null
  return (
    <section aria-labelledby="vc-chart">
      <h2 id="vc-chart">{t.chartTitle}</h2>
      <p className="muted small">{t.chartLede}</p>
      <ul className="vc-legend" aria-label={t.chartLabel}>
        {(['early', 'late', 'other'] as const).map((k) => (
          <li key={k}>
            <span className={`vc-swatch vc-${k}`} aria-hidden="true" />
            {t.legend[k]}
          </li>
        ))}
      </ul>
      <p className="vc-readout small" aria-live="polite">
        {shown ? t.readout(name(shown.book_id), shown.new, shown.expected, shown.novelty) : ' '}
      </p>
      <svg className="vc-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.chartLabel} direction="ltr">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={PAD.t} y2={H - PAD.b} className={v === 0 ? 'chart-zero' : 'chart-grid'} />
            <text x={x(v)} y={H - 6} textAnchor="middle" className="axis">
              {x2(v)}
            </text>
          </g>
        ))}
        {d.books.map((b, i) => {
          const y = PAD.t + i * ROW
          const x0 = x(0)
          const x1 = x(b.novelty)
          const cls = b.period ?? 'other'
          return (
            <g
              key={b.book_id}
              className={`vc-row${hover?.book_id === b.book_id ? ' on' : ''}`}
              tabIndex={0}
              onMouseEnter={() => setHover(b)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(b)}
              onBlur={() => setHover(null)}
            >
              <title>{t.readout(name(b.book_id), b.new, b.expected, b.novelty)}</title>
              <rect x={0} y={y} width={W} height={ROW} className="vc-hit" />
              <text x={PAD.l - 6} y={y + ROW - 4} textAnchor="end" className="axis">
                {name(b.book_id)}
              </text>
              <rect x={Math.min(x0, x1)} y={y + 3} width={Math.max(1, Math.abs(x1 - x0))} height={ROW - 6} rx={2} className={`vc-bar vc-${cls}`} />
            </g>
          )
        })}
      </svg>
    </section>
  )
}

function BookTable({ d, books }: { d: VocabularyResponse; books: Book[] | undefined }) {
  const { m } = useLocale()
  const t = m.vc
  const name = useBookName(books)
  const cols = ['words', 'lemmas', 'new', 'perK', 'expected', 'novelty', 'hapax', 'hapaxK', 'one'] as const
  const cell = (b: VocabularyBook, c: (typeof cols)[number]) => {
    switch (c) {
      case 'words':
        return m.num(b.words)
      case 'lemmas':
        return m.num(b.lemmas)
      case 'new':
        return m.num(b.new)
      case 'perK':
        return b.new_per_k.toFixed(1)
      case 'expected':
        return b.expected.toFixed(1)
      case 'novelty':
        return x2(b.novelty)
      case 'hapax':
        return m.num(b.hapax)
      case 'hapaxK':
        return b.hapax_per_k.toFixed(1)
      case 'one':
        return m.num(b.one_corpus)
    }
  }
  return (
    <section aria-labelledby="vc-table">
      <h2 id="vc-table">{t.tableTitle}</h2>
      <p className="muted small">{t.limits}</p>
      <TableCsv name="vocabulary-1" tabIndex={0} role="region" aria-labelledby="vc-table">
        <table className="data-table vc-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.book}</th>
              {cols.map((c) => (
                <th key={c} scope="col" className="num">
                  {t.cols[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => (
              <tr key={b.book_id} className={b.period ? `vc-${b.period}-row` : ''}>
                <th scope="row">
                  {b.period && <span className={`vc-swatch vc-${b.period}`} aria-hidden="true" />}
                  {name(b.book_id)}
                </th>
                {cols.map((c) => (
                  <td key={c} className="num">
                    {cell(b, c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}
