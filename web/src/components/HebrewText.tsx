import type { KeyboardEvent } from 'react'
import type { Verse } from '../api/types'
import { useTextMode } from '../context/textModeContext'
import { displayForm, endsWithMaqaf } from '../lib/hebrew'
import type { Highlight } from '../lib/highlight'

interface Props {
  verse: Verse
  highlight?: Highlight
  className?: string
  /** Makes every token a button reporting its display index (word analysis). */
  onWordClick?: (displayIdx: number) => void
  selected?: number
  /** Display indexes after which a verse member (colon) ends: shown as ‖. */
  breaks?: Set<number>
  /** Display indexes after which a clause (a weaker accent pause) ends: shown as a thin |. */
  minorBreaks?: Set<number>
}

/** A verse's display tokens, right to left, with the text mode and lemma highlights applied. */
export function HebrewText({ verse, highlight, className, onWordClick, selected, breaks, minorBreaks }: Props) {
  const { mode } = useTextMode()
  const tokens = verse.display_tokens
  // roving tabindex: the verse is one tab stop (the selected word, else the first); arrow keys move
  // between its words — ← is the next word in right-to-left reading
  const stop = selected !== undefined && selected < tokens.length ? selected : 0
  const move = (e: KeyboardEvent<HTMLSpanElement>, i: number) => {
    const to =
      e.key === 'ArrowLeft' ? i + 1 : e.key === 'ArrowRight' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? tokens.length - 1 : -1
    if (to < 0 || to >= tokens.length || to === i) return
    e.preventDefault()
    const word = e.currentTarget.parentElement?.parentElement?.querySelectorAll<HTMLElement>('[data-word]')[to]
    word?.focus()
  }
  return (
    <span className={`he ${className ?? ''}`} dir="rtl" lang="he">
      {tokens.map((t, i) => {
        const mark = highlight?.get(i)
        const sep = i < tokens.length - 1 && !endsWithMaqaf(t) ? ' ' : ''
        const cls = [mark && `w w-${mark}`, onWordClick && 'w-click', selected === i && 'w-selected']
          .filter(Boolean)
          .join(' ')
        return (
          <span key={i}>
            {onWordClick ? (
              <span
                className={cls}
                role="button"
                data-word=""
                tabIndex={i === stop ? 0 : -1}
                aria-pressed={selected === i}
                onClick={() => onWordClick(i)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onWordClick(i)
                  } else move(e, i)
                }}
              >
                {displayForm(t, mode)}
              </span>
            ) : (
              <span className={cls || undefined}>{displayForm(t, mode)}</span>
            )}
            {breaks?.has(i) ? (
              <span className="colon-break" aria-label="pause">
                {' ‖ '}
              </span>
            ) : minorBreaks?.has(i) ? (
              <span className="clause-break" aria-hidden="true">
                {' | '}
              </span>
            ) : (
              sep
            )}
          </span>
        )
      })}
      {verse.ketiv_note && (
        <span className="ketiv" title="Ketiv (written form)">
          {' '}
          [כתיב: {verse.ketiv_note}]
        </span>
      )}
    </span>
  )
}

/** Plain Hebrew string (previews, lemma chips) with the text mode applied word by word. */
export function HebrewPlain({ text, className }: { text: string; className?: string }) {
  const { mode } = useTextMode()
  return (
    <span className={`he ${className ?? ''}`} dir="rtl" lang="he">
      {displayForm(text, mode)}
    </span>
  )
}
