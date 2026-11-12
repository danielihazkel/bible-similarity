import { type RefObject, useLayoutEffect } from 'react'

/** An open menu that would spill past the window's edge is slid back inside it: the shift is
 * written as `--menu-shift`, which the menu's `transform` reads. */
export function useFitInWindow(menuRef: RefObject<HTMLElement | null>, open: boolean) {
  useLayoutEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const fit = () => {
      menu.style.setProperty('--menu-shift', '0px')
      if (!open) return
      const { left, right } = menu.getBoundingClientRect()
      const edge = document.documentElement.clientWidth - 8
      const shift = right > edge ? edge - right : left < 8 ? 8 - left : 0
      menu.style.setProperty('--menu-shift', `${Math.round(shift)}px`)
    }
    fit()
    if (!open) return
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [menuRef, open])
}
