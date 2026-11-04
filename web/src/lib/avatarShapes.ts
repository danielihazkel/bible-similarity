// The family tree's avatar figures (D103) as data: drawn by `components/Avatar.tsx` on the page
// and by the printed poster (`lib/treePoster.ts`), so both draw the same figures.
import type { TreeNode } from '../api/types'

/** One part of a figure on the 44 × 44 box: a circle (cx, cy, r) or a path; `front` parts are
 * outlined in the avatar's own colour, to stand apart from those behind them. */
export type AvatarPart = { c: [number, number, number]; front?: boolean } | { d: string; front?: boolean }
export type AvatarShape = 'man' | 'woman' | 'group' | 'book'

export const AVATAR_PARTS: Record<AvatarShape, AvatarPart[]> = {
  man: [{ c: [22, 16.5, 7.5] }, { d: 'M7 44c0-10 6.5-15.5 15-15.5S37 34 37 44z' }],
  woman: [
    { d: 'M22 7.5c-6.2 0-9.6 4.6-9.6 10.6 0 4.2-1.2 7.4-3.4 10.4h26c-2.2-3-3.4-6.2-3.4-10.4 0-6-3.4-10.6-9.6-10.6z' },
    { d: 'M7 44c0-8.6 6.5-13.5 15-13.5S37 35.4 37 44z' },
  ],
  group: [
    { c: [12.5, 20, 4.6] },
    { c: [31.5, 20, 4.6] },
    { d: 'M3 40c0-6.5 4.2-10.5 9.5-10.5S22 33.5 22 40zM22 40c0-6.5 4.2-10.5 9.5-10.5S41 33.5 41 40z' },
    { c: [22, 16, 5.8], front: true },
    { d: 'M10 44c0-8 5.4-12.5 12-12.5S34 36 34 44z', front: true },
  ],
  book: [{ d: 'M11 13h9.5c.9 0 1.5.6 1.5 1.5V33c0-1-.8-1.8-1.8-1.8H11zM33 13h-9.5c-.9 0-1.5.6-1.5 1.5V33c0-1 .8-1.8 1.8-1.8H33z' }],
}

export const avatarShape = (sex: TreeNode['sex'], kind: TreeNode['kind']): AvatarShape =>
  kind === 'group' ? 'group' : kind === 'virtual' ? 'book' : sex === 'f' ? 'woman' : 'man'
