// The family tree's search box: a person by a Hebrew name.
import { useDeferredValue, useState } from 'react'
import { usePersonLookup } from '../../api/hooks'
import type { PersonMatch } from '../../api/types'
import { useLocale } from '../../context/localeContext'
import { personAbout } from '../../lib/people'
import type { T } from './shared'

export function PersonSearch({ t, onPick }: { t: T; onPick: (id: number) => void }) {
  const { locale } = useLocale()
  const [q, setQ] = useState('')
  const dq = useDeferredValue(q.trim())
  const res = usePersonLookup(dq)
  const items = q.trim() && res.data?.query === dq ? res.data.items : undefined
  const choose = (x: PersonMatch) => {
    setQ('')
    onPick(x.person_id)
  }
  return (
    <div className="gt-search">
      <label className="control">
        <span>{t.search}</span>
        <input
          type="search"
          value={q}
          placeholder={t.searchHint}
          lang="he"
          dir="rtl"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && items?.length) choose(items[0])
            else if (e.key === 'Escape') setQ('')
          }}
        />
      </label>
      {items &&
        (items.length ? (
          <ul className="gt-matches" aria-label={t.matches}>
            {items.map((x) => (
              <li key={x.person_id}>
                <button type="button" className="linkish" onClick={() => choose(x)}>
                  <span lang="he" dir="rtl" className="he">
                    {x.he}
                  </span>
                </button>{' '}
                <span className="muted small" dir="auto">
                  {personAbout(x, t, locale)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted small">{t.noMatch(q.trim())}</p>
        ))}
    </div>
  )
}
