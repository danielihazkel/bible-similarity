// A person's round avatar in the family tree (D103): a man's or a woman's silhouette, three heads
// for a nation or clan, a book for the "unattached" groups. Drawn in `currentColor` on a 44 × 44
// box; the circle, its fill and its ring are the stylesheet's (`.gt-avatar`); the figures are
// `lib/avatarShapes.ts`'s.

import type { TreeNode } from '../api/types'
import { AVATAR_PARTS, avatarShape } from '../lib/avatarShapes'
import '../styles/components/Avatar.css'

export function Avatar({ sex, kind }: { sex: TreeNode['sex']; kind: TreeNode['kind'] }) {
  return (
    <svg className="gt-avatar-svg" viewBox="0 0 44 44" fill="currentColor" aria-hidden="true" focusable="false">
      {AVATAR_PARTS[avatarShape(sex, kind)].map((p, i) =>
        'c' in p ? (
          <circle key={i} className={p.front ? 'front' : undefined} cx={p.c[0]} cy={p.c[1]} r={p.c[2]} />
        ) : (
          <path key={i} className={p.front ? 'front' : undefined} d={p.d} />
        ),
      )}
    </svg>
  )
}
