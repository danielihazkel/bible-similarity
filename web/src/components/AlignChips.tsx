import { ApiError } from '../api/client'
import type { AlignResponse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { HebrewPlain } from './HebrewText'

interface Props {
  align?: AlignResponse
  loading: boolean
  error: unknown
  focus?: number
  onFocus: (link: number | undefined) => void
}

/** The word links of two verses (`/align`): each word the other's best match through the
 * encoder's token vectors; links of meaning (no shared lemma) set apart from shared words. */
export function AlignChips({ align, loading, error, focus, onFocus }: Props) {
  const { m, locale } = useLocale()
  const t = m.compare
  if (error) return <p className="chips status error small">{error instanceof ApiError && error.status === 503 ? t.alignLoading : t.alignFailed}</p>
  if (!align) return loading ? <p className="chips muted">{t.aligning}</p> : null
  if (!align.links.length) return <p className="chips muted">{t.alignNone(align.min_cos)}</p>
  return (
    <div className="chips" aria-label={t.alignLinks}>
      <span className="chips-label">{t.alignLinks}</span>
      {align.links.map((l, i) => (
        <button
          key={i}
          type="button"
          dir={locale === 'he' ? 'rtl' : 'ltr'} // A's word first in reading order
          className={`chip align-chip ${l.same_lemma ? 'same' : 'meaning'} ${focus === i ? 'on' : ''}`}
          title={t.alignTitle(l.cos, l.same_lemma)}
          onMouseEnter={() => onFocus(i)}
          onMouseLeave={() => onFocus(undefined)}
          onFocus={() => onFocus(i)}
          onBlur={() => onFocus(undefined)}
        >
          <HebrewPlain text={l.a_form} /> ↔ <HebrewPlain text={l.b_form} /> <span className="cos">{l.cos.toFixed(2)}</span>
        </button>
      ))}
      <span className="muted small">{t.alignNote}</span>
    </div>
  )
}
