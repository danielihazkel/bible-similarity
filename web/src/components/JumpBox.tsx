import { useQueryClient } from '@tanstack/react-query'
import { type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { getJson } from '../api/client'
import { useLemmaLookup, useResolve } from '../api/hooks'
import type { LemmaLookup, LemmaStat, ResolveResponse, UnitSummary } from '../api/types'
import { useLocale } from '../context/localeContext'
import type { Messages } from '../i18n'
import { unitLink } from '../lib/links'
import { matchPages } from '../lib/nav'
import { unitLabel } from '../lib/names'

const MAX_WORDS = 6
const MAX_PAGES = 6
const DEBOUNCE_MS = 150

type Kind = 'passage' | 'words' | 'pages' | 'search'
interface Option {
  kind: Kind
  to: string
  label: string
  detail?: string
  hebrew?: boolean
}

/** Every choice for a query, best first: the passage it names, the words, the pages, a text search. */
function buildOptions(
  m: Messages,
  locale: 'en' | 'he',
  q: string,
  unit: UnitSummary | null | undefined,
  lemmas: LemmaStat[],
): Option[] {
  const t = m.jump
  if (!q.trim()) return []
  return [
    ...(unit ? [{ kind: 'passage' as const, to: unitLink(unit.unit_id), label: unitLabel(unit, locale) }] : []),
    ...lemmas.slice(0, MAX_WORDS).map((l) => ({
      kind: 'words' as const,
      to: `/lemma/${encodeURIComponent(l.lemma)}`,
      label: l.he_lemma,
      detail: `${l.lemma} · ${t.verses(l.n_verses)}`,
      hebrew: true,
    })),
    ...matchPages(m, q, MAX_PAGES).map((p) => ({ kind: 'pages' as const, to: p.to, label: p.label, detail: p.hint })),
    { kind: 'search', to: `/search?q=${encodeURIComponent(q.trim())}`, label: t.searchFor(q.trim()) },
  ]
}

/** Ctrl+K: a passage by its reference, a word by its form or Strong's number, a page by its name, or
 * else a search of the text. A modal combobox: arrows move, Enter opens, Escape closes. */
export function JumpBox({ onClose }: { onClose: () => void }) {
  const { m, locale } = useLocale()
  const t = m.jump
  const navigate = useNavigate()
  const client = useQueryClient()
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const [q, setQ] = useState('')
  const [settled, setSettled] = useState('')
  const [active, setActive] = useState(0)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(q.trim()), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [q])
  // focus moves in on open and back to where it was on close
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    input.current?.focus()
    return () => before?.focus?.()
  }, [])

  const resolve = useResolve(settled)
  const lemmas = useLemmaLookup(settled)
  const unit = resolve.data?.query === settled ? resolve.data.unit : undefined
  const words = lemmas.data?.query === settled ? lemmas.data.items : []
  const options = buildOptions(m, locale, settled === q.trim() ? q : '', unit, words)
  const shown = options.length > 0 ? options : buildOptions(m, locale, q, undefined, [])
  const current = Math.min(active, shown.length - 1)

  const go = (o: Option | undefined) => {
    if (!o) return
    onClose()
    navigate(o.to)
  }
  // Enter before the lookups have caught up with the typing: look the query up now
  const goNow = async () => {
    const s = q.trim()
    if (!s) return
    const [r, l] = await Promise.all([
      client.fetchQuery({ queryKey: ['resolve', s], queryFn: ({ signal }) => getJson<ResolveResponse>('/resolve', { q: s }, signal) }),
      client.fetchQuery({ queryKey: ['lemma-lookup', s], queryFn: ({ signal }) => getJson<LemmaLookup>('/lemmas', { q: s }, signal) }),
    ]).catch(() => [undefined, undefined] as const)
    go(buildOptions(m, locale, s, r?.unit, l?.items ?? [])[0])
  }

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = shown.length
      if (n) setActive((current + (e.key === 'ArrowDown' ? 1 : n - 1)) % n)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (settled === q.trim() && !resolve.isFetching && !lemmas.isFetching) go(shown[current])
      else void goNow()
    } else if (e.key === 'Tab') {
      e.preventDefault() // the input is the dialog's one stop; the list is reached with the arrows
    }
  }

  const groups: Kind[] = ['passage', 'words', 'pages', 'search']
  const optionId = (i: number) => `${id}-o${i}`
  return (
    <div
      className="jump-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="jump" role="dialog" aria-modal="true" aria-label={t.label}>
        <input
          ref={input}
          className="jump-input"
          type="text"
          role="combobox"
          aria-label={t.label}
          aria-expanded={shown.length > 0}
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          aria-activedescendant={shown.length > 0 ? optionId(current) : undefined}
          placeholder={t.placeholder}
          value={q}
          spellCheck={false}
          autoComplete="off"
          onChange={(e) => {
            setQ(e.target.value)
            setActive(0)
          }}
          onKeyDown={onKey}
        />
        <div id={`${id}-list`} className="jump-list" role="listbox" aria-label={t.label}>
          {groups.map((g) => {
            const items = shown.map((o, i) => [o, i] as const).filter(([o]) => o.kind === g)
            if (items.length === 0) return null
            return (
              <div key={g} role="group" aria-labelledby={`${id}-${g}`}>
                <div id={`${id}-${g}`} className="jump-heading" role="presentation">
                  {g === 'passage' ? t.passage : g === 'words' ? t.words : g === 'pages' ? t.pages : t.search}
                </div>
                {items.map(([o, i]) => (
                  <div
                    key={o.to}
                    id={optionId(i)}
                    role="option"
                    aria-selected={i === current}
                    className="jump-option"
                    onMouseMove={() => i !== current && setActive(i)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => go(o)}
                  >
                    <span className={o.hebrew ? 'he' : undefined} dir={o.hebrew ? 'rtl' : undefined} lang={o.hebrew ? 'he' : undefined}>
                      {o.label}
                    </span>
                    {o.detail && <span className="muted small">{o.detail}</span>}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
        <p className="jump-keys muted small" aria-hidden="true">
          {t.keys}
        </p>
      </div>
    </div>
  )
}
