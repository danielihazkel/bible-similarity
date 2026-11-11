import { type FormEvent, Fragment, useState } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'
import { useSourceExamples, useSourceFind } from '../api/hooks'
import type { SourcePassage, SourceResponse, SourceVerse } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { verseRef } from '../lib/names'
import { useQueryParams } from '../lib/urlState'
import '../i18n/pages/sourceFind'
import '../styles/pages/SourcePage.css'

/** The source finder (§11.1, D131): a pasted Hebrew text with the phrases it takes from the
 * Bible marked, each with its verses; `?example=` fills one of the examples and searches it. */
export function SourcePage() {
  const { m } = useLocale()
  const t = m.sf
  const ex = useSourceExamples()
  const [params, update] = useQueryParams()
  const example = params.get('example')
  const [draft, setDraft] = useState('')
  const [text, setText] = useState<string | undefined>(undefined)
  const max = ex.data?.max_chars ?? Infinity
  // an example named in the address fills the box and is searched, once per example
  const [applied, setApplied] = useState<string | null>(null)
  const chosen = ex.data?.examples.find((x) => x.key === example)
  if (chosen && applied !== chosen.key) {
    setApplied(chosen.key)
    setDraft(chosen.text)
    setText(chosen.text)
  }
  const res = useSourceFind(text)
  const tooLong = draft.length > max
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!tooLong) setText(draft)
  }
  return (
    <div className="page source-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <form className="sf-form" onSubmit={submit}>
        <label htmlFor="sf-text">{t.label}</label>
        <textarea id="sf-text" dir="rtl" lang="he" rows={6} value={draft} placeholder={t.placeholder} onChange={(e) => setDraft(e.target.value)} aria-describedby="sf-count" />
        <p className="small muted" id="sf-count">
          {Number.isFinite(max) && t.chars(draft.length, max)}
        </p>
        {tooLong && <p className="sf-error">{t.tooLong(max)}</p>}
        <p className="sf-actions">
          <button type="submit" className="primary" disabled={tooLong || draft.trim() === ''}>
            {t.submit}
          </button>
          {ex.data && ex.data.examples.length > 0 && (
            <span className="small">
              {t.examples}:{' '}
              {ex.data.examples.map((e, i) => (
                <Fragment key={e.key}>
                  {i > 0 && ' · '}
                  <button type="button" className="linkish" onClick={() => update({ example: e.key }, false)}>
                    {t.exampleNames[e.key] ?? e.key}
                  </button>
                </Fragment>
              ))}
            </span>
          )}
        </p>
      </form>
      {text !== undefined &&
        (res.isError ? (
          res.error instanceof ApiError && res.error.status === 422 ? <p className="sf-error">{t.tooLong(max)}</p> : <ErrorBox error={res.error} />
        ) : !res.data ? (
          <Loading />
        ) : (
          <Result r={res.data} />
        ))}
      <p className="muted small">{t.how}</p>
    </div>
  )
}

function Result({ r }: { r: SourceResponse }) {
  const t = useLocale().m.sf
  if (r.passages.length === 0) return <p className="muted">{t.none}</p>
  // each token's passage (its number from 1), and the tokens a verse matched exactly
  const of = new Map<number, number>()
  const exact = new Set<number>()
  r.passages.forEach((p, k) => {
    for (let i = p.first; i <= p.last; i++) of.set(i, k + 1)
    for (const v of p.verses) for (const i of v.text_tokens) exact.add(i)
  })
  const words = r.passages.reduce((n, p) => n + p.last - p.first + 1, 0)
  return (
    <>
      <p>{t.found(r.passages.length, words)}</p>
      <section aria-labelledby="sf-text-h">
        <h2 id="sf-text-h">{t.textTitle}</h2>
        <p className="sf-text he" dir="rtl" lang="he">
          {r.tokens.map((tok, i) => {
            const k = of.get(i)
            const end = k !== undefined && of.get(i + 1) !== k
            return (
              <Fragment key={i}>
                {i > 0 && ' '}
                {k === undefined ? (
                  tok
                ) : (
                  <mark className={`sf-hit sf-hit-${(k - 1) % 4}${exact.has(i) ? ' sf-exact' : ''}`}>{tok}</mark>
                )}
                {end && (
                  <sup className="sf-num">
                    <a href={`#sf-p${k}`} aria-label={t.passageLabel(k)}>
                      {k}
                    </a>
                  </sup>
                )}
              </Fragment>
            )
          })}
        </p>
      </section>
      <section aria-labelledby="sf-list-h">
        <h2 id="sf-list-h">{t.listTitle}</h2>
        <ol className="sf-passages">
          {r.passages.map((p, k) => (
            <Passage key={k} p={p} k={k + 1} tokens={r.tokens} />
          ))}
        </ol>
      </section>
    </>
  )
}

function Passage({ p, k, tokens }: { p: SourcePassage; k: number; tokens: string[] }) {
  const { m, locale } = useLocale()
  const t = m.sf
  return (
    <li id={`sf-p${k}`}>
      <p className="he sf-quote" dir="rtl" lang="he">
        {tokens.slice(p.first, p.last + 1).join(' ')}
      </p>
      <p className="small">
        {p.verses.map((v, i) => (
          <Fragment key={v.verse.verse_id}>
            {i > 0 && ', '}
            <Link to={unitLink(`v:${v.verse.verse_id}`)}>{verseRef(v.verse, locale)}</Link>
          </Fragment>
        ))}{' '}
        <span className="muted">· {t.matched(p.matched)}</span>
      </p>
      {p.verses.map((v) => (
        <VerseText key={v.verse.verse_id} v={v} />
      ))}
      {p.alternatives.length > 0 && (
        <p className="small muted">
          {t.alsoIn}{' '}
          {p.alternatives.map((a, i) => (
            <Fragment key={a.verse_id}>
              {i > 0 && ', '}
              <Link to={unitLink(`v:${a.verse_id}`)}>{verseRef(a, locale)}</Link>
            </Fragment>
          ))}
        </p>
      )}
    </li>
  )
}

function VerseText({ v }: { v: SourceVerse }) {
  const hit = new Set(v.tokens)
  return (
    <p className="hit-text he" dir="rtl" lang="he">
      {v.verse.display_tokens.map((tok, i) => (
        <Fragment key={i}>
          {i > 0 && !v.verse.display_tokens[i - 1].endsWith('־') && ' '}
          {hit.has(i) ? <mark className="sf-exact">{tok}</mark> : tok}
        </Fragment>
      ))}
    </p>
  )
}
