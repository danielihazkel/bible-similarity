import { Link } from 'react-router'
import { useCipherValue, useDomains, useGematriaValue, useWords } from '../api/hooks'
import type { CipherName } from '../api/types'
import type { Verse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { lemmaLink, rootLink } from '../lib/links'
import { DomainChip } from './DomainName'
import { HebrewPlain } from './HebrewText'
import { ErrorBox, Loading } from './Status'

const CIPHERS: CipherName[] = ['atbash', 'albam']

/** Morphology and lemmas of the OSHB words on one display token, with concordance links. */
export function WordPanel({ verse, displayIdx, onClose }: { verse: Verse; displayIdx: number; onClose: () => void }) {
  const { m, locale } = useLocale()
  const words = useWords(verse.verse_id)
  const domains = useDomains()
  const domainOf = new Map(domains.data?.map((d) => [d.code, d]) ?? [])
  const here = words.data?.filter((w) => w.display_idx === displayIdx) ?? []
  const token = verse.display_tokens[displayIdx]
  const hebrew = /[א-ת]/.test(token) ? token : undefined
  const gm = useGematriaValue(hebrew)
  const cipherRes = useCipherValue(hebrew)
  const swapped = cipherRes.data?.text === token ? cipherRes.data : undefined
  return (
    <section className="word-panel" aria-label={m.word.panel}>
      <div className="word-head">
        <HebrewPlain className="word-form" text={token} />
        <span className="muted small">{locale === 'he' ? verse.ref_he : verse.ref}</span>
        {gm.data?.text === token && (
          <Link className="chip gm-chip" to={`/gematria?q=${encodeURIComponent(gm.data.letters)}`} title={m.gm.wordValueTitle}>
            {m.gm.wordValue(gm.data.values.standard)}
          </Link>
        )}
        <button type="button" className="linkish" onClick={onClose}>
          {m.word.close}
        </button>
      </div>
      {swapped && (
        <p className="muted small word-ciphers">
          {m.cph.wordCiphers}:{' '}
          {CIPHERS.map((c, i) => {
            const f = swapped[c]
            return (
              <span key={c}>
                {i > 0 && ' · '}
                {m.cph.ciphers[c]}{' '}
                {f.n_words > 0 ? (
                  <Link to={`/search?q=${encodeURIComponent(f.form)}&mode=lexical`} title={m.cph.wordCipherTitle(f.n_words)} dir="rtl" lang="he">
                    {f.form}
                  </Link>
                ) : (
                  <span dir="rtl" lang="he" title={m.cph.wordCipherTitle(0)}>
                    {f.form}
                  </span>
                )}
              </span>
            )
          })}
        </p>
      )}
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
                {w.roots.map((r) => (
                  <Link key={`root-${r.root}`} className="chip root-chip" to={rootLink(r.root)} title={m.root.rootChipTitle}>
                    {m.root.root}{' '}
                    <span dir="rtl" lang="he">
                      {r.root_he}
                    </span>
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
