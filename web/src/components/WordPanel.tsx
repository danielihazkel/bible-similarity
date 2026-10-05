import { Link } from 'react-router'
import { useDomains, useWords } from '../api/hooks'
import type { Verse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { lemmaLink } from '../lib/links'
import { DomainChip } from './DomainName'
import { HebrewPlain } from './HebrewText'
import { ErrorBox, Loading } from './Status'

/** Morphology and lemmas of the OSHB words on one display token, with concordance links. */
export function WordPanel({ verse, displayIdx, onClose }: { verse: Verse; displayIdx: number; onClose: () => void }) {
  const { m, locale } = useLocale()
  const words = useWords(verse.verse_id)
  const domains = useDomains()
  const domainOf = new Map(domains.data?.map((d) => [d.code, d]) ?? [])
  const here = words.data?.filter((w) => w.display_idx === displayIdx) ?? []
  return (
    <section className="word-panel" aria-label={m.word.panel}>
      <div className="word-head">
        <HebrewPlain className="word-form" text={verse.display_tokens[displayIdx]} />
        <span className="muted small">{locale === 'he' ? verse.ref_he : verse.ref}</span>
        <button type="button" className="linkish" onClick={onClose}>
          {m.word.close}
        </button>
      </div>
      {words.isPending ? (
        <Loading />
      ) : words.error ? (
        <ErrorBox error={words.error} />
      ) : here.length === 0 ? (
        <p className="status">{m.word.unaligned}</p>
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
                  <Link key={l.lemma} className="chip lemma-chip" to={lemmaLink(l.lemma)} title={m.lemmas.allVerses(l.lemma)}>
                    <span dir="rtl" lang="he">
                      {l.he_lemma}
                    </span>{' '}
                    <span className="muted small">{m.word.verses(l.n_verses)}</span>
                  </Link>
                ))}
              </div>
            )}
            {w.domains.length > 0 && (
              <div className="chips word-domains" aria-label={m.dom.wordDomains}>
                {w.domains.map((code) => (
                  <DomainChip
                    key={code}
                    domain={domainOf.get(code) ?? { code, label_en: code }}
                    title={m.dom.wordDomainTitle}
                  />
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </section>
  )
}
