import { type ReactNode, useId, useLayoutEffect, useRef, useState } from 'react'
import { useLocale } from '../context/localeContext'
import type { TermKey } from '../i18n/pages/glossary'
import '../i18n/pages/glossary'
import { matches } from '../lib/gloss'

/** A term with its glossary entry in a popover, opened on hover, focus or a tap and closed by
 * Escape; the entry describes the button for screen readers (DESIGN.md §11). */
export function Term({ k, children }: { k: TermKey; children?: ReactNode }) {
  const t = useLocale().m.gloss
  const entry = t.terms[k]
  const id = useId()
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const tip = useRef<HTMLSpanElement>(null)
  // placed in the viewport beside the term (below it, or above near the foot), never past an edge
  useLayoutEffect(() => {
    const b = button.current?.getBoundingClientRect()
    const el = tip.current
    if (!open || !b || !el) return
    const w = el.offsetWidth
    const h = el.offsetHeight
    const rtl = document.documentElement.dir === 'rtl'
    const left = rtl ? b.right - w : b.left
    el.style.left = `${Math.max(8, Math.min(left, window.innerWidth - w - 8))}px`
    el.style.top = `${b.bottom + 4 + h > window.innerHeight && b.top - 4 - h > 0 ? b.top - 4 - h : b.bottom + 4}px`
  }, [open])
  return (
    <span className="term" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        ref={button}
        type="button"
        className="term-button"
        aria-describedby={id}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setOpen(false)
        }}
      >
        {children ?? entry.term}
      </button>
      <span ref={tip} role="tooltip" id={id} className={`term-tip${open ? ' open' : ''}`} data-nocsv="">
        <b>{entry.name}.</b> {entry.def}
      </span>
    </span>
  )
}

/** A text with the given terms marked where they first appear (the locale's patterns). */
export function Glossed({ text, keys }: { text: string; keys: ReadonlySet<TermKey> }) {
  const patterns = useLocale().m.gloss.patterns
  if (keys.size === 0) return <>{text}</>
  const parts: ReactNode[] = []
  let at = 0
  for (const f of matches(text, patterns, keys)) {
    parts.push(text.slice(at, f.start))
    parts.push(
      <Term key={f.key} k={f.key}>
        {text.slice(f.start, f.end)}
      </Term>,
    )
    at = f.end
  }
  parts.push(text.slice(at))
  return <>{parts}</>
}
