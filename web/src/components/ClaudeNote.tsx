import type { LabelValue } from '../api/types'
import { useLocale } from '../context/localeContext'
import '../i18n/pages/labels'
import '../styles/components/ClaudeNote.css'

/** What a note needs: Claude's verdict on a pair, its probability, kind and rationale. */
export interface NoteLike {
  verdict: string
  p_real: number
  kind: string
  rationale: string | null
}

/** Claude's reading of a pair (DESIGN.md §16.81, §16.88): a suggestion beside the pair, never a
 * label. The rationale is shown in the language it was written in. */
export function ClaudeNote({ note, hebrew = true }: { note: NoteLike; hebrew?: boolean }) {
  const t = useLocale().m.lab
  return (
    <p className={`queue-suggestion small suggest-${note.verdict}`}>
      <span className="queue-suggestion-head">
        {t.suggests(t.values[note.verdict as LabelValue] ?? note.verdict, note.p_real.toFixed(2), t.kinds[note.kind] ?? note.kind)}
      </span>{' '}
      {note.rationale && (
        <span lang={hebrew ? 'he' : 'en'} dir={hebrew ? 'rtl' : 'ltr'}>
          {note.rationale}
        </span>
      )}
    </p>
  )
}
