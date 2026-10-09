import { Link } from 'react-router'
import type { Dossier, DossierEntry, UnitSummary } from '../api/types'
import { useLocale } from '../context/localeContext'
import { entryLink, isFound } from '../lib/dossier'
import { PanelError } from './Status'

/**
 * What every analysis found about this unit (`/dossier`): findings as links to where they are
 * read in full, then the analyses that found nothing here and those this build did not run.
 */
export function DossierBar({ unit, dossier, error }: { unit: UnitSummary; dossier?: Dossier; error?: unknown }) {
  const { m } = useLocale()
  const t = m.dos
  if (error) return <PanelError what={t.what} error={error} />
  if (!dossier) return null
  const found = dossier.entries.filter(isFound)
  const none = dossier.entries.filter((e) => e.computed && !isFound(e))
  const missing = dossier.entries.filter((e) => !e.computed)
  const chip = (e: DossierEntry): string => {
    const c = t.chip
    const text =
      e.kind === 'acrostic' || e.kind === 'structure'
        ? c[e.kind](e.value ?? 1)
        : e.kind === 'dating'
          ? c.dating(e.value ?? 0)
          : e.kind === 'speech'
            ? c.speech(e.count ?? 0, e.label)
            : e.kind === 'voices'
              ? c.voices(e.label ?? e.key ?? '')
              : e.kind === 'network'
                ? c.network(e.count ?? 0, e.total ?? 0)
                : e.kind === 'divisions'
                  ? c.divisions(e.count ?? 0, e.key)
                  : c[e.kind](e.count ?? 0)
    return e.scope === 'chapter' ? text + t.inChapter : text
  }
  return (
    <nav className="dossier" aria-label={t.label}>
      {found.length > 0 && (
        <p className="dossier-found">
          <span className="muted small">{t.found}</span>
          {found.map((e) => {
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
        </p>
      )}
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
    </nav>
  )
}
