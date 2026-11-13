import { type MouseEvent, useEffect, useLayoutEffect, useRef, useState } from 'react'
import '../styles/components/SectionStrip.css'

export interface PageSection {
  id: string
  label: string
}

/** A strip of links to a long page's sections, sticky under the top bar. It is given every section
 * the page may have, in page order, and lists those that are drawn (a panel with nothing to show
 * draws nothing); the one being read is marked. A link scrolls its section to the top of the
 * window and gives it the focus; the address does not change. */
export function SectionStrip({ sections, label }: { sections: PageSection[]; label: string }) {
  const ref = useRef<HTMLElement>(null)
  const [present, setPresent] = useState<string[]>([])
  const [current, setCurrent] = useState<string>()
  const ids = sections.map((s) => s.id).join(' ')
  const look = useRef(() => {})
  useLayoutEffect(() => {
    look.current = () => {
      const here = ids.split(' ').filter((id) => document.getElementById(id))
      setPresent((was) => (was.join(' ') === here.join(' ') ? was : here))
      // the last section whose top has passed under the strip; before any has, the first
      const line = (ref.current?.getBoundingClientRect().bottom ?? 0) + 12
      const passed = here.filter((id) => document.getElementById(id)!.getBoundingClientRect().top <= line).at(-1)
      setCurrent(passed ?? here[0])
    }
    look.current()
  }, [ids])
  useEffect(() => {
    const root = ref.current?.parentElement
    if (!root) return
    let frame = 0
    const soon = () => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        look.current()
      })
    }
    // panels draw themselves when their data arrives
    const seen = new MutationObserver(soon)
    seen.observe(root, { childList: true, subtree: true })
    window.addEventListener('scroll', soon, { passive: true })
    window.addEventListener('resize', soon)
    return () => {
      cancelAnimationFrame(frame)
      seen.disconnect()
      window.removeEventListener('scroll', soon)
      window.removeEventListener('resize', soon)
    }
  }, [])

  const go = (e: MouseEvent, id: string) => {
    e.preventDefault()
    const el = document.getElementById(id)
    if (!el) return
    el.scrollIntoView?.({ block: 'start' })
    if (!el.hasAttribute('tabindex')) el.tabIndex = -1
    el.focus({ preventScroll: true })
  }
  const shown = sections.filter((s) => present.includes(s.id))
  return (
    <nav ref={ref} className="section-strip no-print" aria-label={label} hidden={shown.length < 2}>
      {shown.map((s) => (
        <a key={s.id} href={`#${s.id}`} aria-current={current === s.id ? 'true' : undefined} onClick={(e) => go(e, s.id)}>
          {s.label}
        </a>
      ))}
    </nav>
  )
}
