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
}

/** A verse's display tokens, right to left, with the text mode and lemma highlights applied. */
export function HebrewText({ verse, highlight, className, onWordClick, selected, breaks }: Props) {
  const { mode } = useTextMode()
  const tokens = verse.display_tokens
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
                tabIndex={0}
                aria-pressed={selected === i}
                onClick={() => onWordClick(i)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onWordClick(i)
                  }
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
