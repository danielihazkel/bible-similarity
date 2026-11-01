// A person's name as the family tree shows it: Hebrew in its own direction, else plain.
import type { Named } from './shared'

export function Name({ n }: { n: Named }) {
  return n.he ? (
    <span lang="he" dir="rtl" className="he">
      {n.text}
    </span>
  ) : (
    <bdi>{n.text}</bdi>
  )
}
