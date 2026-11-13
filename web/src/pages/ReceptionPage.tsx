import { useMemo } from 'react'
import { Link } from 'react-router'
import { isStageMissing } from '../api/client'
import { useBooks, useReception, useReceptionCitations, useReceptionVerses, useUnit } from '../api/hooks'
import type { ReceptionChapter, ReceptionCitation, ReceptionResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HeatStrip, type HeatRow } from '../components/HeatStrip'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import type { CorpusChoice } from '../i18n/pages/reception'
import '../i18n/pages/reception'
import { readLink, unitLink } from '../lib/links'
import { bookName, verseRef } from '../lib/names'
import { bounds, CORPORA, countOf, parseCorpus, parts, step, STEPS } from '../lib/reception'
import { parsePage, useQueryParams } from '../lib/urlState'
import '../styles/pages/ReceptionPage.css'

const PAGE = 25

/** Rabbinic reception (§16.77): where the Mishnah, the Tosefta and the two Talmuds cite the Bible,
 * chapter by chapter and verse by verse; a unit's citations (`?unit=`), by corpus (`?corpus=`). */
export function ReceptionPage() {
  const { m } = useLocale()
  const t = m.rc
  const res = useReception()
  const [params, update] = useQueryParams()
  const corpus = parseCorpus(params.get('corpus'))
  const unit = params.get('unit') ?? undefined
  const d = res.data
  return (
    <div className="page reception-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">
        {t.source} (
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
          {t.sourceLicence}
        </a>
        ){t.sourceNote}
      </p>
      {isStageMissing(res.error) ? (
        <NotComputed>{t.notComputed}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <p>{t.described(d.citations, d.verses_cited, Object.values(d.passages).reduce((a, b) => a + b, 0))}</p>
          <Checks d={d} />
          <div className="toolbar">
            <Segmented<CorpusChoice>
              label={t.corpusLabel}
              value={corpus}
              options={(['all', ...CORPORA] as CorpusChoice[]).map((c) => ({ value: c, label: c === 'all' ? t.all : t.corpora[c] }))}
              onChange={(c) => update({ corpus: c === 'all' ? null : c, page: null, cpage: null }, false)}
            />
          </div>
          {unit ? <UnitCitations unit={unit} corpus={corpus} /> : <TopVerses corpus={corpus} />}
          <Strip d={d} corpus={corpus} />
          <Books d={d} corpus={corpus} />
          <p className="muted small">{t.limits(d.max_span, d.dropped_long)}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.rc
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: ReceptionResponse }) {
  const { m, locale } = useLocale()
  const t = m.rc
  return (
    <section aria-labelledby="rc-checks">
      <h2 id="rc-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.law.title} <Verdict holds={d.law_holds} />
          </h3>
          <p>{t.law.text(d.ratios.mishnah, d.law_p, d.shifts, d.legal_verses, d.narrative_verses)}</p>
          <p className="small muted">
            {t.ratiosTitle}: {CORPORA.map((c) => `${t.corpora[c]} ${(d.ratios[c] ?? 0).toFixed(2)}`).join(' · ')}
          </p>
        </article>
        <article className="dv-check">
          <h3>
            {t.bavli.title} <Verdict holds={d.gap_holds} />
          </h3>
          <p>{t.bavli.text(d.ratios.mishnah, d.ratios.bavli, d.gap, d.gap_p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <ul className="rc-known">
            {d.known.map((k) => (
              <li key={`${k.cite}|${k.ref}`}>
                <span dir="ltr">{k.cite}</span> → {k.verse ? <Link to={`/reception?unit=${encodeURIComponent(`v:${k.verse.verse_id}`)}`}>{verseRef(k.verse, locale)}</Link> : k.ref}{' '}
                <span className={k.found ? 'rc-found' : 'muted'}>({k.found ? t.known.found : t.known.missing})</span>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  )
}

function TopVerses({ corpus }: { corpus: CorpusChoice }) {
  const { m, locale } = useLocale()
  const t = m.rc
  const [params] = useQueryParams()
  const page = parsePage(params.get('page'))
  const bp = params.get('book')
  const book = bp !== null && bp !== '' && Number.isInteger(Number(bp)) ? Number(bp) : undefined
  const books = useBooks()
  const bk = books.data?.find((b) => b.book_id === book)
  const res = useReceptionVerses(corpus === 'all' ? undefined : corpus, book, PAGE, (page - 1) * PAGE)
  return (
    <section aria-labelledby="rc-top">
      <h2 id="rc-top">{bk ? t.topIn(bookName(bk, locale)) : t.topTitle}</h2>
      {book !== undefined && (
        <p className="small">
          <Link to={corpus === 'all' ? '/reception' : `/reception?corpus=${corpus}`}>{t.allBooks}</Link>
        </p>
      )}
      <PagedList csv="reception-verses" res={res} empty={t.unitNone}>
        {(d, stale) => (
          <ol className={`rc-verses ${stale}`} start={(page - 1) * PAGE + 1}>
            {d.items.map((v) => (
              <li key={v.verse.verse_id}>
                <Link to={`/reception?unit=${encodeURIComponent(`v:${v.verse.verse_id}`)}${corpus === 'all' ? '' : `&corpus=${corpus}`}`}>{verseRef(v.verse, locale)}</Link>{' '}
                <span className="rc-n">{m.num(countOf(v, corpus))}</span> <span className="muted small">{parts(v, t.corpora, m.num)}</span>
                <p className="hit-text he" dir="rtl" lang="he">
                  {v.verse.text_display}
                </p>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function UnitCitations({ unit, corpus }: { unit: string; corpus: CorpusChoice }) {
  const { m, locale } = useLocale()
  const t = m.rc
  const [params] = useQueryParams()
  const page = parsePage(params.get('cpage'))
  const detail = useUnit(unit)
  const res = useReceptionCitations(unit, corpus === 'all' ? undefined : corpus, PAGE, (page - 1) * PAGE)
  const u = detail.data?.unit
  // the citations of each verse together, in verse order
  const groups = useMemo(() => {
    const out: { verse: number; ref: string; items: ReceptionCitation[] }[] = []
    for (const c of res.data?.items ?? []) {
      const last = out[out.length - 1]
      if (last && last.verse === c.verse_id) last.items.push(c)
      else out.push({ verse: c.verse_id, ref: locale === 'he' ? c.ref_he : c.ref, items: [c] })
    }
    return out
  }, [res.data, locale])
  return (
    <section aria-labelledby="rc-unit" className="rc-unit">
      <h2 id="rc-unit">{u ? t.unitTitle(locale === 'he' ? u.label_he : u.label_en) : t.unitTitle(unit)}</h2>
      <p className="small">
        <Link to={corpus === 'all' ? '/reception' : `/reception?corpus=${corpus}`}>{t.allVerses}</Link>
        {u && (
          <>
            {' · '}
            <Link to={readLink(u.unit_type === 'verse' ? `c:${u.book_id}:${detail.data!.verses[0].chapter}` : u.unit_id, '?layers=reception')}>{t.readWith}</Link>
          </>
        )}
      </p>
      {detail.isError ? (
        <ErrorBox error={detail.error} />
      ) : (
        <PagedList csv="reception-citations" pageParam="cpage" res={res} empty={t.unitNone} summary={(d) => parts(d.counts, t.corpora, m.num)}>
          {(_, stale) => (
            <div className={stale}>
          {groups.map((g) => (
            <div key={g.verse} className="rc-group">
              <h3>
                <Link to={unitLink(`v:${g.verse}`)}>{g.ref}</Link>
              </h3>
              <ul className="rc-cites">
                {g.items.map((c) => (
                  <li key={`${c.cite}|${c.verse_id}`}>
                    <span className={`rc-tag rc-${c.corpus}`}>{t.corpora[c.corpus]}</span>{' '}
                    <a href={c.url} target="_blank" rel="noreferrer" lang="he" dir="rtl">
                      {c.cite_he}
                    </a>
                    {locale === 'en' && (
                      <>
                        {' '}
                        <span className="muted small" dir="ltr">
                          {c.cite}
                        </span>
                      </>
                    )}
                    <span className="sr-only"> {t.onSefaria}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
            </div>
          )}
        </PagedList>
      )}
    </section>
  )
}

function Strip({ d, corpus }: { d: ReceptionResponse; corpus: CorpusChoice }) {
  const { m, locale } = useLocale()
  const t = m.rc
  const books = useBooks()
  const { rows, b } = useMemo(() => {
    const byId = new Map((books.data ?? []).map((x) => [x.book_id, x]))
    const rate = (c: ReceptionChapter) => countOf(c, corpus) / c.verses
    const b = bounds(d.chapters.map(rate))
    const chapters = new Map<number, ReceptionChapter[]>()
    for (const c of d.chapters) chapters.set(c.book_id, [...(chapters.get(c.book_id) ?? []), c])
    const rows: HeatRow[] = d.books.map((bk) => {
      const book = byId.get(bk.book_id)
      const name = book ? bookName(book, locale) : String(bk.book_id)
      return {
        key: bk.book_id,
        name,
        to: `/reception?book=${bk.book_id}${corpus === 'all' ? '' : `&corpus=${corpus}`}#rc-top`,
        label: t.stripLabel(name),
        cells: (chapters.get(bk.book_id) ?? []).map((c) => ({
          key: c.unit_id,
          cls: `rc-${step(rate(c), b)}`,
          title: t.chapterTitle(`${name} ${c.chapter.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')}`, countOf(c, corpus), c.verses),
          to: readLink(c.unit_id, '?layers=reception'),
        })),
      }
    })
    return { rows, b }
  }, [d, corpus, books.data, locale, t])
  return (
    <section aria-labelledby="rc-strip">
      <h2 id="rc-strip">{t.stripTitle}</h2>
      <p className="muted small">{t.stripHint}</p>
      <div className="dv-legend" role="group" aria-label={t.legend.label}>
        <span className="small">{t.legend.label}:</span>
        {Array.from({ length: STEPS + 1 }, (_, s) => (
          <span key={s} className="dv-ramp-step">
            <span className={`dv-swatch rc-${s}`} aria-hidden="true" />
            {s === 0 ? (
              <span className="small">{t.legend.none}</span>
            ) : (
              <span className="small" dir="ltr">
                {t.legend.range(s === 1 ? 0 : b[s - 2], s === STEPS ? null : b[s - 1])}
              </span>
            )}
          </span>
        ))}
      </div>
      <HeatStrip rows={rows} prefix="rc" />
    </section>
  )
}

function Books({ d, corpus }: { d: ReceptionResponse; corpus: CorpusChoice }) {
  const { m, locale } = useLocale()
  const t = m.rc
  const books = useBooks()
  const byId = new Map((books.data ?? []).map((x) => [x.book_id, x]))
  return (
    <section aria-labelledby="rc-books">
      <h2 id="rc-books">{t.booksTitle}</h2>
      <TableCsv name="reception-books">
        <table className="change-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.book}</th>
              <th scope="col">{t.cols.verses}</th>
              {CORPORA.map((c) => (
                <th key={c} scope="col">
                  {t.corpora[c]}
                </th>
              ))}
              <th scope="col">{t.cols.total}</th>
              <th scope="col">{t.cols.perVerse}</th>
            </tr>
          </thead>
          <tbody>
            {d.books.map((bk) => {
              const book = byId.get(bk.book_id)
              return (
                <tr key={bk.book_id}>
                  <th scope="row">
                    <Link to={`/reception?book=${bk.book_id}${corpus === 'all' ? '' : `&corpus=${corpus}`}#rc-top`}>{book ? bookName(book, locale) : bk.book_id}</Link>
                  </th>
                  <td className="num">{m.num(bk.verses)}</td>
                  {CORPORA.map((c) => (
                    <td key={c} className="num">
                      {m.num(bk[c])}
                    </td>
                  ))}
                  <td className="num">{m.num(bk.total)}</td>
                  <td className="num">{(countOf(bk, corpus) / bk.verses).toFixed(2)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}
