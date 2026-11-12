import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useEncoderStatus, useResolve, useSearch, useServer } from '../api/hooks'
import { BookSelect, KSelect, ModeToggle } from '../components/Controls'
import { HebrewKeypad } from '../components/HebrewKeypad'
import { CopyPassage } from '../components/CopyButton'
import { HebrewText } from '../components/HebrewText'
import { KeepButton } from '../components/NotebookPanel'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale, useT } from '../context/localeContext'
import { hasHebrew } from '../lib/hebrew'
import { unitLabel } from '../lib/names'
import { readLink, unitLink } from '../lib/links'
import { DEFAULT_K, DEFAULT_MODE, parseK, parseMode, SEARCH_K_OPTIONS, SEARCH_MODES, useQueryParams } from '../lib/urlState'
import '../styles/pages/SearchPage.css'

export function SearchPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  // a server without the query encoder (a public deploy) searches lexically only
  const server = useServer()
  const mode = server.encoder ? parseMode(params.get('mode'), SEARCH_MODES) : 'lexical'
  const k = parseK(params.get('k'), SEARCH_K_OPTIONS)
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' || !Number.isInteger(Number(bookParam)) ? undefined : Number(bookParam)
  const books = useBooks()
  const resolved = useResolve(q).data?.unit
  const needsEncoder = mode !== 'lexical'
  const encoder = useEncoderStatus(needsEncoder)
  const encoderLoading = needsEncoder && !encoder.ready && !encoder.error
  // the server answers semantic / fused queries only once the encoder has loaded
  const search = useSearch(q, mode, k, !needsEncoder || encoder.ready === true, book)

  return (
    <div className="page search-page">
      <h1>{m.search.title}</h1>
      {/* key: the draft restarts from the URL query on back / forward navigation */}
      <SearchForm key={q} initial={q} onSubmit={(text) => update({ q: text.trim() || null }, false)} />
      <div className="toolbar">
        {server.encoder && (
          <ModeToggle modes={SEARCH_MODES} value={mode} onChange={(m) => update({ mode: m === DEFAULT_MODE ? null : m })} />
        )}
        <KSelect
          value={k}
          options={SEARCH_K_OPTIONS}
          onChange={(v) => update({ k: v === DEFAULT_K ? null : String(v) })}
        />
        <BookSelect label={m.search.book} all={m.search.allBooks} books={books.data} value={book} onChange={(v) => update({ book: v })} />
      </div>
      <p className="muted small">
        {m.modes.hints[mode]}. {m.search.hint}
        {!server.encoder && <> {m.server.encoderOff}</>}
      </p>

      {needsEncoder && encoder.error ? (
        <p className="status error" role="alert">
          {m.search.encoderFailed(encoder.error)}{' '}
          <button type="button" className="linkish" onClick={() => update({ mode: 'lexical' })}>
            {m.search.searchLexically}
          </button>
        </p>
      ) : (
        needsEncoder &&
        encoder.ready === false && (
          <p className="status" role="status">
            {m.search.encoderLoading(m.modes.names[mode].toLowerCase())}
          </p>
        )
      )}

      {resolved && (
        <p className="goto">
          {m.search.reference} <Link to={unitLink(resolved.unit_id)}>{unitLabel(resolved, locale)}</Link>{' '}
          {locale === 'en' && (
            <>
              <span className="he-label" dir="rtl" lang="he">
                {resolved.label_he}
              </span>{' '}
            </>
          )}
          {m.locale === 'he' ? '←' : '→'}
        </p>
      )}

      {!q ? null : !hasHebrew(q) ? (
        !resolved && <p className="status">{m.search.notRef}</p>
      ) : needsEncoder && encoder.error ? null : search.isPending ? (
        <Loading label={encoderLoading ? m.search.waiting : m.search.searching} />
      ) : search.error ? (
        <ErrorBox error={search.error} />
      ) : (
        <>
          <p className="muted small">
            {m.search.normalized} <span className="he" dir="rtl" lang="he">{search.data.normalized}</span>
            {mode !== 'semantic' && search.data.tokens.length > 0 && (
              <>
                {' '}
                · {m.search.terms}{' '}
                <span className="he" dir="rtl" lang="he">
                  {search.data.tokens.join(' · ')}
                </span>
              </>
            )}
          </p>
          {search.data.hits.length === 0 ? (
            <p className="status">{m.search.noMatches}</p>
          ) : (
            <ol className="hits">
              {search.data.hits.map((h) => (
                <li key={h.verse.verse_id} className="hit">
                  <div className="hit-head">
                    <span className="hit-rank">{h.rank}</span>
                    <Link className="hit-ref" to={unitLink(`v:${h.verse.verse_id}`)}>
                      <UnitName en={h.label_en} he={h.label_he} />
                    </Link>
                    <ScoreBreakdown hit={h} mode={search.data.mode} />
                    <span className="hit-actions">
                      <Link className="linkish" to={readLink(`v:${h.verse.verse_id}`)} title={m.hit.readTitle}>
                        {m.hit.read}
                      </Link>
                      <KeepButton unitId={`v:${h.verse.verse_id}`} />
                      <CopyPassage en={h.label_en} he={h.label_he} verses={[h.verse]} />
                    </span>
                  </div>
                  <p className="hit-text">
                    <HebrewText verse={h.verse} />
                  </p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  )
}

function SearchForm({ initial, onSubmit }: { initial: string; onSubmit: (text: string) => void }) {
  const m = useT()
  const [draft, setDraft] = useState(initial)
  const [keypad, setKeypad] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  return (
    <>
      <form
        className="search-form"
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit(draft)
        }}
      >
        <input
          ref={input}
          className="he search-input"
          dir="rtl"
          lang="he"
          type="search"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={m.search.placeholder}
          aria-label={m.search.inputLabel}
          autoFocus
        />
        <button type="submit" className="primary">
          {m.search.submit}
        </button>
        <button type="button" className="linkish" aria-expanded={keypad} onClick={() => setKeypad(!keypad)}>
          {keypad ? m.search.hideKeyboard : m.search.showKeyboard}
        </button>
      </form>
      {keypad && (
        <HebrewKeypad
          onKey={(ch) => {
            setDraft((d) => d + ch)
            input.current?.focus()
          }}
          onBackspace={() => setDraft((d) => [...d].slice(0, -1).join(''))}
        />
      )}
    </>
  )
}

