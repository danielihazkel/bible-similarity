import { Link } from 'react-router'
import type { WordplayPair } from '../api/types'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { useT } from '../context/localeContext'
import { HebrewText } from './HebrewText'

/** Two sound-alike words, both highlighted in their verse(s). */
export function WordplayCard({ p }: { p: WordplayPair }) {
  const m = useT()
  const marks = (vid: number): Highlight => {
    const m: Highlight = new Map()
    if (p.a_vid === vid && p.a_display !== null) m.set(p.a_display, 'focus')
    if (p.b_vid === vid && p.b_display !== null) m.set(p.b_display, 'focus')
    return m
  }
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="pun he" dir="rtl" lang="he">
          {p.a_form} ~ {p.b_form}
        </span>
        <span className="phrase-tag">{m.cards.wordplayKinds[p.kind]}</span>
        <span className="muted small">
          <span dir="rtl" lang="he">
            {p.a_he} / {p.b_he}
          </span>{' '}
          · {p.gap === 1 ? m.cards.adjacent : m.cards.apart(p.gap)}
        </span>
        <span className="score" title={m.cards.wordplayScore}>
          {p.score.toFixed(1)}
        </span>
      </div>
      {p.verses.map((v) => (
        <div key={v.verse_id} className="disc-side">
          <Link className="hit-ref" to={unitLink(`v:${v.verse_id}`)}>
            {v.verse_id === p.a_vid ? p.a_label : p.b_label}
          </Link>
          <p className="hit-text">
            <HebrewText verse={v} highlight={marks(v.verse_id)} />
          </p>
        </div>
      ))}
    </li>
  )
}
