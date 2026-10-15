import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useGematria, useGematriaForms, useGematriaLemmas, useGematriaValue, useGematriaVerses } from '../api/hooks'
import type { GematriaResponse, GematriaSystem, GematriaView, VerseLabel } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { lemmaLink, unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const DEBOUNCE_MS = 250
const SYSTEMS: GematriaSystem[] = ['standard', 'gadol', 'ordinal', 'katan']
const VIEWS: GematriaView[] = ['forms', 'lemmas', 'verses']
const HEBREW = /[א-ת]/
const NUMBER = /^\d{1,7}$/

/** A word's or a number's letter value, and the words, lemmas and verses of the same value (§16.53). */
export function GematriaPage() {
  const { m } = useLocale()
  const t = m.gm
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const system = (SYSTEMS as string[]).includes(params.get('system') ?? '') ? (params.get('system') as GematriaSystem) : 'standard'
  const view = (VIEWS as string[]).includes(params.get('view') ?? '') ? (params.get('view') as GematriaView) : 'forms'
  // the box follows the URL, and the URL the box (debounced)
  const [text, setText] = useState(q)
  const [seen, setSeen] = useState(q)
  if (q !== seen) {
    setSeen(q)
    if (text.trim() !== q) setText(q)
  }
  useEffect(() => {
    if (text.trim() === q) return
    const timer = window.setTimeout(() => update({ q: text.trim() || null, page: null }), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [text, q, update])

  const isNumber = NUMBER.test(q)
  const calc = useGematriaValue(!isNumber && HEBREW.test(q) ? q : undefined)
  const typed = !isNumber && calc.data?.text === q ? calc.data : undefined
  const value = isNumber ? Number(q) : typed?.values[system]
  const res = useGematria(value, system)
  // the equivalences of the config, also before anything is typed
  const known = useGematria(value ?? 0, 'standard')

  return (
    <div className="page gematria-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <label className="control">
          <span>{t.input}</span>
          <input type="search" dir="auto" value={text} placeholder={t.placeholder} onChange={(e) => setText(e.target.value)} />
        </label>
        <Segmented
          label={t.system}
          value={system}
          onChange={(s) => update({ system: s === 'standard' ? null : s, page: null })}
          options={SYSTEMS.map((s) => ({ value: s, label: t.systems[s], title: t.systemHints[s] }))}
        />
      </div>
      {known.data && !known.data.computed ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          {q && !isNumber && !HEBREW.test(q) && <p className="status">{t.noLetters}</p>}
          {calc.error && <ErrorBox error={calc.error} />}
          {typed && (
            <section aria-label={t.valuesOf(typed.letters)}>
              <p>
                {t.valuesOf(typed.letters)}{' '}
                <span className="chips">
                  {SYSTEMS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={`chip ${s === system ? 'on' : ''}`}
                      aria-pressed={s === system}
                      title={t.systemHints[s]}
                      onClick={() => update({ system: s === 'standard' ? null : s, page: null })}
                    >
                      {t.systems[s]} <b>{m.num(typed.values[s])}</b>
                    </button>
                  ))}
                </span>
              </p>
            </section>
          )}
          {value !== undefined && res.error && <ErrorBox error={res.error} />}
          {value !== undefined && res.data && <Results data={res.data} view={view} onView={(v) => update({ view: v === 'forms' ? null : v, page: null, book: null })} />}
          {known.data && known.data.known.length > 0 && <Known data={known.data} onPick={(s) => setText(s)} />}
        </>
      )}
    </div>
  )
}

function Results({ data, view, onView }: { data: GematriaResponse; view: GematriaView; onView: (v: GematriaView) => void }) {
  const t = useLocale().m.gm
  const n = { forms: data.forms, lemmas: data.lemmas, verses: data.verses }
  return (
    <section aria-label={t.summary(data.value, t.systems[data.system], data.forms, data.words, data.lemmas, data.verses)}>
      <p>{t.summary(data.value, t.systems[data.system], data.forms, data.words, data.lemmas, data.verses)}</p>
      <div className="toolbar">
        <Segmented label={t.view} value={view} onChange={onView} options={VIEWS.map((v) => ({ value: v, label: t.views[v](n[v]) }))} />
      </div>
      <p className="muted small">{t.ledes[view]}</p>
      {view === 'forms' ? <Forms data={data} /> : view === 'lemmas' ? <Lemmas data={data} /> : <Verses data={data} />}
    </section>
  )
}

function usePageQuery(data: GematriaResponse, book?: number) {
  const [params] = useQueryParams()
  const page = parsePage(params.get('page'))
  return { value: data.value, system: data.system, book, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
}

function VerseLink({ v }: { v: VerseLabel }) {
  const { locale } = useLocale()
  return <Link to={unitLink(`v:${v.verse_id}`)}>{locale === 'he' ? v.label_he : v.label_en}</Link>
}

function Forms({ data }: { data: GematriaResponse }) {
  const { m } = useLocale()
  const t = m.gm
  const res = useGematriaForms(usePageQuery(data))
  return (
    <PagedList res={res} empty={t.empty.forms} summary={(_, p, pages) => t.pageOf(p, pages)}>
      {(d, stale) => (
        <ol className={`gm-forms ${stale}`}>
          {d.items.map((f) => (
            <li key={f.form}>
              <span className="he-label" dir="rtl" lang="he">
                {f.form}
              </span>{' '}
              <span className="muted small">
                {t.formCount(f.n_words, f.n_verses)} · {t.firstIn}{' '}
                {f.verses.map((v, i) => (
                  <span key={v.verse_id}>
                    {i > 0 && ', '}
                    <VerseLink v={v} />
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ol>
      )}
    </PagedList>
  )
}

function Lemmas({ data }: { data: GematriaResponse }) {
  const { m } = useLocale()
  const t = m.gm
  const res = useGematriaLemmas(usePageQuery(data))
  return (
    <PagedList res={res} empty={t.empty.lemmas} summary={(_, p, pages) => t.pageOf(p, pages)}>
      {(d, stale) => (
        <div className={`chips gm-lemmas ${stale}`}>
          {d.items.map((l) => (
            <Link key={l.lemma} className="chip lemma-chip" to={lemmaLink(l.lemma)} title={m.lemmas.allVerses(l.lemma)}>
              <span dir="rtl" lang="he">
                {l.he}
              </span>{' '}
              <span className="muted small">
                {l.lemma} · {t.lemmaWords(l.n_words)}
              </span>
            </Link>
          ))}
        </div>
      )}
    </PagedList>
  )
}

function Verses({ data }: { data: GematriaResponse }) {
  const { m, locale } = useLocale()
  const t = m.gm
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  const res = useGematriaVerses(usePageQuery(data, book))
  return (
    <>
      <div className="toolbar">
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => update({ book: e.target.value || null, page: null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <PagedList res={res} empty={t.empty.verses} summary={(_, p, pages) => t.pageOf(p, pages)}>
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((h) => (
              <li key={h.verse.verse_id} className="hit">
                <div className="hit-head">
                  <Link className="hit-ref" to={unitLink(`v:${h.verse.verse_id}`)}>
                    <UnitName en={h.label_en} he={h.label_he} />
                  </Link>{' '}
                  <span className="muted small">{t.verseCount(h.n_letters, h.n_words)}</span>
                </div>
                <p className="hit-text">
                  <HebrewText verse={h.verse} />
                </p>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function Known({ data, onPick }: { data: GematriaResponse; onPick: (text: string) => void }) {
  const { m } = useLocale()
  const t = m.gm
  return (
    <section aria-label={t.knownTitle}>
      <h2>{t.knownTitle}</h2>
      <p className="muted small">{t.knownLede}</p>
      <div className="chips">
        {data.known.map((k) => (
          <button key={k.text} type="button" className="chip" onClick={() => onPick(k.text)}>
            <span dir="rtl" lang="he">
              {k.text}
            </span>{' '}
            <b>{m.num(k.value)}</b>
          </button>
        ))}
      </div>
    </section>
  )
}
