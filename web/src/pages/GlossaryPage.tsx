import { useEffect } from 'react'
import { useLocation } from 'react-router'
import { useLocale } from '../context/localeContext'
import { TERMS } from '../i18n/pages/glossary'
import '../styles/pages/GlossaryPage.css'

/** The glossary (§11): every term the pages use, each with an anchor (`/glossary#g2`). */
export function GlossaryPage() {
  const t = useLocale().m.gloss
  const { hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(`term-${hash.slice(1)}`)?.scrollIntoView?.({ block: 'start' })
  }, [hash])
  return (
    <div className="page glossary-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <dl className="glossary">
        {TERMS.map((k) => (
          <div key={k} id={`term-${k}`} className="glossary-entry">
            <dt>
              <b>{t.terms[k].term}</b>
              {t.terms[k].name !== t.terms[k].term && <span className="muted"> · {t.terms[k].name}</span>}
            </dt>
            <dd>{t.terms[k].def}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
