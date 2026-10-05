import { Link } from 'react-router'
import type { DomainInfo } from '../api/types'
import { useLocale } from '../context/localeContext'
import { domainLink } from '../lib/links'
import { domainLabel } from '../lib/names'

/** A semantic domain's name. In the Hebrew interface a deeper domain keeps its English SDBH name,
 * isolated from the right-to-left text around it. */
export function DomainName({ domain }: { domain: Pick<DomainInfo, 'code' | 'label_en'> }) {
  const { m, locale } = useLocale()
  const label = domainLabel(domain, m.dom.top, locale)
  const english = locale === 'en' || label === domain.label_en
  return (
    <bdi lang={english ? 'en' : 'he'} dir={english ? 'ltr' : 'rtl'}>
      {label}
    </bdi>
  )
}

/** A chip linking to a domain's verses, with an optional count after the name. */
export function DomainChip({
  domain,
  extra,
  title,
}: {
  domain: Pick<DomainInfo, 'code' | 'label_en'>
  extra?: string
  title?: string
}) {
  return (
    <Link className="chip domain-chip" to={domainLink(domain.code)} title={title}>
      <DomainName domain={domain} />
      {extra && <span className="muted small"> {extra}</span>}
    </Link>
  )
}
