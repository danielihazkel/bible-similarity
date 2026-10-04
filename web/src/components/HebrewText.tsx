import type { Verse } from '../api/types'
import { useTextMode } from '../context/textModeContext'
import { displayForm, endsWithMaqaf } from '../lib/hebrew'
import type { Highlight } from '../lib/highlight'

interface Props {
  verse: Verse
  highlight?: Highlight
  className?: string
}

/** A verse's display tokens, right to left, with the text mode and lemma highlights applied. */
export function HebrewText({ verse, highlight, className }: Props) {
  const { mode } = useTextMode()
  const tokens = verse.display_tokens
  return (
    <span className={`he ${className ?? ''}`} dir="rtl" lang="he">
      {tokens.map((t, i) => {
        const mark = highlight?.get(i)
        const sep = i < tokens.length - 1 && !endsWithMaqaf(t) ? ' ' : ''
        return (
          <span key={i}>
            <span className={mark ? `w w-${mark}` : undefined}>{displayForm(t, mode)}</span>
            {sep}
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
