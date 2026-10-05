import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { useEncoderStatus, useResolve, useSearch } from '../api/hooks'
import { KSelect, ModeToggle } from '../components/Controls'
import { HebrewKeypad } from '../components/HebrewKeypad'
import { HebrewText } from '../components/HebrewText'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { ErrorBox, Loading } from '../components/Status'
import { MODE_HINTS } from '../lib/format'
import { hasHebrew } from '../lib/hebrew'
import { unitLink } from '../lib/links'
import { DEFAULT_K, DEFAULT_MODE, parseK, parseMode, SEARCH_MODES, useQueryParams } from '../lib/urlState'

export function SearchPage() {
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const mode = parseMode(params.get('mode'), SEARCH_MODES)
  const k = parseK(params.get('k'))
  const resolved = useResolve(q).data?.unit
  const needsEncoder = mode !== 'lexical'
  const encoder = useEncoderStatus(needsEncoder)
  const encoderLoading = needsEncoder && !encoder.ready && !encoder.error
  // the server answers semantic / fused queries only once the encoder has loaded
  const search = useSearch(q, mode, k, !needsEncoder || encoder.ready === true)

  return (
    <div className="page search-page">
      <h1>Search</h1>
      {/* key: the draft restarts from the URL query on back / forward navigation */}
      <SearchForm key={q} initial={q} onSubmit={(text) => update({ q: text.trim() || null }, false)} />
      <div className="toolbar">
        <ModeToggle modes={SEARCH_MODES} value={mode} onChange={(m) => update({ mode: m === DEFAULT_MODE ? null : m })} />
        <KSelect value={k} onChange={(v) => update({ k: v === DEFAULT_K ? null : String(v) })} />
      </div>
      <p className="muted small">
        {MODE_HINTS[mode]}. Pointed or unpointed input; lexical matching strips prefixes (ו ה ב כ ל מ ש).
      </p>

      {needsEncoder && encoder.error ? (
        <p className="status error" role="alert">
          The semantic encoder failed to load on the server ({encoder.error}); only lexical search is available.{' '}
          <button type="button" className="linkish" onClick={() => update({ mode: 'lexical' })}>
            Search lexically
          </button>
        </p>
      ) : (
        needsEncoder &&
        encoder.ready === false && (
          <p className="status" role="status">
            The semantic encoder is still loading on the server; {mode} search will answer as soon as it is ready
            (lexical search works now).
          </p>
        )
      )}

      {resolved && (
        <p className="goto">
          Reference: <Link to={unitLink(resolved.unit_id)}>{resolved.label_en}</Link>{' '}
          <span className="he-label" dir="rtl" lang="he">
            {resolved.label_he}
          </span>{' '}
          →
        </p>
      )}

      {!q ? null : !hasHebrew(q) ? (
        !resolved && <p className="status">Not a reference; free-text search needs Hebrew letters.</p>
      ) : needsEncoder && encoder.error ? null : search.isPending ? (
        <Loading label={encoderLoading ? 'Waiting for the semantic encoder…' : 'Searching…'} />
      ) : search.error ? (
        <ErrorBox error={search.error} />
      ) : (
        <>
          <p className="muted small">
            Normalized: <span className="he" dir="rtl" lang="he">{search.data.normalized}</span>
            {mode !== 'semantic' && search.data.tokens.length > 0 && (
              <>
                {' '}
                · lexical terms:{' '}
                <span className="he" dir="rtl" lang="he">
                  {search.data.tokens.join(' · ')}
                </span>
              </>
            )}
          </p>
          {search.data.hits.length === 0 ? (
            <p className="status">No matches.</p>
          ) : (
            <ol className="hits">
              {search.data.hits.map((h) => (
                <li key={h.verse.verse_id} className="hit">
                  <div className="hit-head">
                    <span className="hit-rank">{h.rank}</span>
                    <Link className="hit-ref" to={unitLink(`v:${h.verse.verse_id}`)}>
                      {h.label_en}
                      <span className="he-label" dir="rtl" lang="he">
                        {h.label_he}
                      </span>
                    </Link>
                    <ScoreBreakdown hit={h} mode={search.data.mode} />
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
          placeholder="חיפוש בתנ״ך… או הפניה: בראשית א א / Gen 1:1"
          aria-label="Hebrew search text or reference"
          autoFocus
        />
        <button type="submit" className="primary">
          Search
        </button>
        <button type="button" className="linkish" aria-expanded={keypad} onClick={() => setKeypad(!keypad)}>
          {keypad ? 'Hide keyboard' : 'Hebrew keyboard'}
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

