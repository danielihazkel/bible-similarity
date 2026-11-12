import { useEffect, useState } from 'react'
import type { Verse } from '../api/types'
import { useLocale, useT } from '../context/localeContext'
import { useTextMode } from '../context/textModeContext'
import { displayText } from '../lib/hebrew'

/** A button that copies a text and says so for a moment. `text` may be a function, read on the
 * click (the address of the view, a long passage). */
export function CopyButton({ text, label, title, className = 'linkish' }: { text: string | (() => string); label: string; title?: string; className?: string }) {
  const m = useT()
  const [done, setDone] = useState(false)
  useEffect(() => {
    if (!done) return
    const t = window.setTimeout(() => setDone(false), 1500)
    return () => window.clearTimeout(t)
  }, [done])
  return (
    <button
      type="button"
      className={className}
      title={title}
      onClick={() => {
        navigator.clipboard
          ?.writeText(typeof text === 'function' ? text() : text)
          .then(() => setDone(true))
          .catch(() => setDone(false))
      }}
    >
      <span aria-live="polite">{done ? m.site.copied : label}</span>
    </button>
  )
}

/** Two copy buttons for a passage: its reference in the interface language, and, when its verses
 * are at hand, its text as the text display shows it (a verse to a line). */
export function CopyPassage({ en, he, verses }: { en: string; he: string; verses?: Verse[] }) {
  const { m, locale } = useLocale()
  const { mode } = useTextMode()
  const t = m.copy
  return (
    <>
      <CopyButton text={locale === 'he' ? he : en} label={t.ref} title={t.refTitle} />
      {verses && verses.length > 0 && <CopyButton text={() => verses.map((v) => displayText(v.display_tokens, mode)).join('\n')} label={t.text} title={t.textTitle} />}
    </>
  )
}
