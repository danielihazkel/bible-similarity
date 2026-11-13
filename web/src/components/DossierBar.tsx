import { Link } from 'react-router'
import type { DivineName, Dossier, DossierEntry, UnitSummary } from '../api/types'
import type { Corpus } from '../i18n/pages/reception'
import '../i18n/pages/reception'
import { useLocale } from '../context/localeContext'
import { entryLink, families, isFound } from '../lib/dossier'
import { useOpenSections, useQueryParams } from '../lib/urlState'
import { PanelError } from './Status'
import '../i18n/pages/divine'
import '../i18n/pages/dossier'
import '../i18n/pages/witnesses'
import '../styles/components/DossierBar.css'

/** The findings of a family shown before "more". */
const SHOWN = 4

/**
 * What every analysis found about this unit (`/dossier`): the findings as links to where they are
 * read in full, grouped under the nav's families (the menu, or the section of Patterns, of the
 * page each belongs to), the first few of a family and the rest behind "more" (`?found=all`);
 * then, folded away, the analyses that found nothing here and those this build did not run.
 */
export function DossierBar({ unit, dossier, error }: { unit: UnitSummary; dossier?: Dossier; error?: unknown }) {
  const { m } = useLocale()
  const t = m.dos
  const [params, update] = useQueryParams()
  const openProps = useOpenSections()
  if (error) return <PanelError what={t.what} error={error} />
  if (!dossier) return null
  const found = dossier.entries.filter(isFound)
  const none = dossier.entries.filter((e) => e.computed && !isFound(e))
  const missing = dossier.entries.filter((e) => !e.computed)
  const all = params.get('found') === 'all'
  const groups = families(found, unit)
  const folded = groups.some((g) => g.entries.length > SHOWN)
  const chip = (e: DossierEntry): string => {
    const c = t.chip
    const text =
      e.kind === 'acrostic' || e.kind === 'structure'
        ? c[e.kind](e.value ?? 1)
        : e.kind === 'dating' || e.kind === 'meter'
          ? c[e.kind](e.value ?? 0)
          : e.kind === 'speech'
            ? c.speech(e.count ?? 0, e.label)
            : e.kind === 'voices'
              ? c.voices(e.label ?? e.key ?? '')
              : e.kind === 'network'
                ? c.network(e.count ?? 0, e.total ?? 0)
                : e.kind === 'divisions'
                  ? c.divisions(e.count ?? 0, e.key)
                  : e.kind === 'places' || e.kind === 'people'
                    ? c[e.kind](e.count ?? 0, e.label)
                    : e.kind === 'ciphers'
                      ? c.ciphers(e.count ?? 0, e.key, e.label)
                      : e.kind === 'divine'
                        ? c.divine(e.count ?? 0, e.key ? m.dv.names[e.key as DivineName] : null, e.value)
                      : e.kind === 'reception'
                        ? c.reception(e.count ?? 0, e.key ? m.rc.corpora[e.key as Corpus] : null)
                      : e.kind === 'witnesses'
                        ? c.witnesses(e.count ?? 0, e.key === 'sp' ? m.wt.sp : e.key)
                      : e.kind === 'gematria'
                        ? c.gematria(e.count ?? 0, e.label, e.value, e.total)
                        : c[e.kind](e.count ?? 0)
    return e.scope === 'chapter' ? text + t.inChapter : text
  }
  return (
    <nav className="dossier" aria-label={t.label}>
      {found.length > 0 && (
        <div className="dossier-found">
          <span className="muted small">{t.found}</span>
          <dl className="dossier-families">
            {groups.map((g) => {
              const shown = all ? g.entries : g.entries.slice(0, SHOWN)
              const more = g.entries.length - shown.length
              return (
                <div key={g.section ?? g.group ?? 'other'} className="dossier-family">
                  <dt className="muted small">{g.section ? m.navSections[g.section] : g.group ? m.nav[g.group] : t.other}</dt>
                  <dd>
                    {shown.map((e) => {
                      const to = entryLink(e, unit)
                      return to ? (
                        <Link key={e.kind} to={to} className="dossier-chip">
                          {chip(e)}
                        </Link>
                      ) : (
                        <span key={e.kind} className="dossier-chip">
                          {chip(e)}
                        </span>
                      )
                    })}
                    {more > 0 && (
                      <button type="button" className="linkish small" aria-expanded={false} onClick={() => update({ found: 'all' })}>
                        {t.more(more)}
                      </button>
                    )}
                  </dd>
                </div>
              )
            })}
          </dl>
          {all && folded && (
            <button type="button" className="linkish small" aria-expanded={true} onClick={() => update({ found: null })}>
              {t.fewer}
            </button>
          )}
        </div>
      )}
      {none.length + missing.length > 0 && (
        <details className="dossier-rest" {...openProps('nothing')}>
          <summary className="muted small">{t.rest(none.length, missing.length)}</summary>
          {none.length > 0 && (
            <p className="muted small">
              {t.none} {none.map((e) => t.kinds[e.kind]).join(' · ')}
            </p>
          )}
          {missing.length > 0 && (
            <p className="muted small">
              {t.notComputed} {missing.map((e) => t.kinds[e.kind]).join(' · ')}
            </p>
          )}
        </details>
      )}
    </nav>
  )
}
