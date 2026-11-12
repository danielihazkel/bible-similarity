import { useT } from '../context/localeContext'
import { NAV_PAGE, navText } from '../lib/nav'
import { togglePin, usePins } from '../lib/recent'
import '../styles/components/PinButton.css'

/** A star that pins a nav page or takes its pin away (`lib/recent.ts`): in the top bar for the page
 * on screen, and on each row of the All pages index. A toggle button: its name stays, its pressed
 * state changes. */
export function PinButton({ to, className = '' }: { to: string; className?: string }) {
  const m = useT()
  const pins = usePins()
  const page = NAV_PAGE.get(to)
  if (!page) return null
  const on = pins.includes(to)
  return (
    <button
      type="button"
      className={`pin-button ${className}`.trim()}
      aria-pressed={on}
      aria-label={m.site.pin(navText(m, page.key).label)}
      title={on ? m.site.unpinTitle : m.site.pinTitle}
      onClick={() => togglePin(to)}
    >
      <span aria-hidden="true">{on ? '★' : '☆'}</span>
    </button>
  )
}
