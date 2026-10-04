import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useSearch } from '../api/hooks'
import { KSelect, ModeToggle } from '../components/Controls'
import { HebrewKeypad } from '../components/HebrewKeypad'
import { HebrewText } from '../components/HebrewText'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { ErrorBox, Loading } from '../components/Status'
import { MODE_HINTS } from '../lib/format'
import { unitLink } from '../lib/links'
import { DEFAULT_K, DEFAULT_MODE, parseK, parseMode, useQueryParams } from '../lib/urlState'

export function SearchPage() {
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const mode = parseMode(params.get('mode'))
  const k = parseK(params.get('k'))
  const search = useSearch(q, mode, k)
  const slow = useSlow(search.isFetching && mode !== 'lexical')

  return (
    <div className="page search-page">
      <h1>Search</h1>
      {/* key: the draft restarts from the URL query on back / forward navigation */}
      <SearchForm key={q} initial={q} onSubmit={(text) => update({ q: text.trim() || null }, false)} />
      <div className="toolbar">
        <ModeToggle value={mode} onChange={(m) => update({ mode: m === DEFAULT_MODE ? null : m })} />
        <KSelect value={k} onChange={(v) => update({ k: v === DEFAULT_K ? null : String(v) })} />
      </div>
      <p className="muted small">
        {MODE_HINTS[mode]}. Pointed or unpointed input; lexical matching strips prefixes (ו ה ב כ ל מ ש).
      </p>

      {!q ? null : search.isPending ? (
        <Loading
          label={slow ? 'Searching… the semantic encoder may still be loading after startup (about 30 s).' : 'Searching…'}
        />
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
          placeholder="חיפוש בתנ״ך…"
          aria-label="Hebrew search text"
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

/** True once `busy` has lasted more than 1.5 s. */
function useSlow(busy: boolean) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    if (!busy) return
    const t = window.setTimeout(() => setSlow(true), 1500)
    return () => {
      window.clearTimeout(t)
      setSlow(false)
    }
  }, [busy])
  return busy && slow
}
