import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router'
import { useT } from '../context/localeContext'
import { useFitInWindow } from '../lib/menuFit'
import { LocaleToggle, TextModeToggle, ThemeToggle } from './Controls'
import { CopyButton } from './CopyButton'
import '../styles/components/DisplayMenu.css'

/** The viewer's own settings behind one button of the top bar: how the Hebrew text is shown, the
 * interface language, the theme, and the link to this view. Opens on click; closes on Escape (the
 * focus back on the button), a click outside it or a new page. */
export function DisplayMenu() {
  const m = useT()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const [seenPath, setSeenPath] = useState(pathname)
  if (seenPath !== pathname) {
    setSeenPath(pathname)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])
  useFitInWindow(panelRef, open)

  return (
    <div className={`display-menu ${open ? 'open' : ''}`} ref={ref}>
      <button
        type="button"
        ref={buttonRef}
        className="copy-link display-button"
        title={m.site.displayTitle}
        aria-expanded={open}
        aria-controls={open ? 'display-panel' : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {m.site.display} <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div id="display-panel" ref={panelRef} className="display-panel" role="group" aria-label={m.site.display}>
          <div className="display-row">
            <span className="display-label">{m.site.textDisplay}</span>
            <TextModeToggle />
          </div>
          <div className="display-row">
            <span className="display-label">{m.site.language}</span>
            <LocaleToggle />
          </div>
          <div className="display-row">
            <span className="display-label">{m.site.theme}</span>
            <ThemeToggle />
          </div>
          {/* every view's state is in its URL */}
          <CopyButton className="copy-link" text={() => window.location.href} label={m.site.copyLink} title={m.site.copyLinkTitle} />
        </div>
      )}
    </div>
  )
}
