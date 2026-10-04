import { Link } from 'react-router'
import { useWords } from '../api/hooks'
import type { Verse } from '../api/types'
import { lemmaLink } from '../lib/links'
import { HebrewPlain } from './HebrewText'
import { ErrorBox, Loading } from './Status'

/** Morphology and lemmas of the OSHB words on one display token, with concordance links. */
export function WordPanel({ verse, displayIdx, onClose }: { verse: Verse; displayIdx: number; onClose: () => void }) {
  const words = useWords(verse.verse_id)
  const here = words.data?.filter((w) => w.display_idx === displayIdx) ?? []
  return (
    <section className="word-panel" aria-label="Word analysis">
      <div className="word-head">
        <HebrewPlain className="word-form" text={verse.display_tokens[displayIdx]} />
        <span className="muted small">{verse.ref}</span>
        <button type="button" className="linkish" onClick={onClose}>
          Close
        </button>
      </div>
      {words.isPending ? (
        <Loading />
      ) : words.error ? (
        <ErrorBox error={words.error} />
      ) : here.length === 0 ? (
        <p className="status">No OSHB word is aligned to this token.</p>
      ) : (
        here.map((w) => (
          <div key={w.idx} className="word-row">
            <HebrewPlain className="word-surface" text={w.surface.replaceAll('/', '·')} />
            <ul className="morph" dir="rtl" lang="he" title={w.morph ?? undefined}>
              {w.morph_he.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
            {w.lemmas.length > 0 && (
              <div className="chips">
                {w.lemmas.map((l) => (
                  <Link key={l.lemma} className="chip lemma-chip" to={lemmaLink(l.lemma)} title={`Strong's ${l.lemma}: all verses`}>
                    <span dir="rtl" lang="he">
                      {l.he_lemma}
                    </span>{' '}
                    <span className="muted small">{l.n_verses} verses</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </section>
  )
}
