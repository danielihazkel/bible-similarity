// A person's round avatar in the family tree (D103): a man's or a woman's silhouette, three heads
// for a nation or clan, a book for the "unattached" groups. Drawn in `currentColor` on a 44 × 44
// box; the circle, its fill and its ring are the stylesheet's (`.gt-avatar`).

import type { TreeNode } from '../api/types'

const MAN = (
  <>
    <circle cx="22" cy="16.5" r="7.5" />
    <path d="M7 44c0-10 6.5-15.5 15-15.5S37 34 37 44z" />
  </>
)

const WOMAN = (
  <>
    <path d="M22 7.5c-6.2 0-9.6 4.6-9.6 10.6 0 4.2-1.2 7.4-3.4 10.4h26c-2.2-3-3.4-6.2-3.4-10.4 0-6-3.4-10.6-9.6-10.6z" />
    <path d="M7 44c0-8.6 6.5-13.5 15-13.5S37 35.4 37 44z" />
  </>
)

const GROUP = (
  <>
    <circle cx="12.5" cy="20" r="4.6" />
    <circle cx="31.5" cy="20" r="4.6" />
    <path d="M3 40c0-6.5 4.2-10.5 9.5-10.5S22 33.5 22 40zM22 40c0-6.5 4.2-10.5 9.5-10.5S41 33.5 41 40z" />
    <circle className="front" cx="22" cy="16" r="5.8" />
    <path className="front" d="M10 44c0-8 5.4-12.5 12-12.5S34 36 34 44z" />
  </>
)

const BOOK = <path d="M11 13h9.5c.9 0 1.5.6 1.5 1.5V33c0-1-.8-1.8-1.8-1.8H11zM33 13h-9.5c-.9 0-1.5.6-1.5 1.5V33c0-1 .8-1.8 1.8-1.8H33z" />

export function Avatar({ sex, kind }: { sex: TreeNode['sex']; kind: TreeNode['kind'] }) {
  const shape = kind === 'group' ? GROUP : kind === 'virtual' ? BOOK : sex === 'f' ? WOMAN : MAN
  return (
    <svg className="gt-avatar-svg" viewBox="0 0 44 44" fill="currentColor" aria-hidden="true" focusable="false">
      {shape}
    </svg>
  )
}
