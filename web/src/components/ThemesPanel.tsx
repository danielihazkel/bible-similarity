import { useUnitDomains } from '../api/hooks'
import { useLocale } from '../context/localeContext'
import { DomainChip } from './DomainName'
import { PanelError } from './Status'

/** The semantic domains a passage uses most against the whole Tanakh (DESIGN.md §16.22). */
export function ThemesPanel({ unitId }: { unitId: string }) {
  const { m } = useLocale()
  const t = m.dom
  const res = useUnitDomains(unitId)
  if (res.error) return <PanelError what={t.themes} error={res.error} />
  if (!res.data || res.data.total === 0) return null
  const fmt = (x: number) => m.num(Math.round(x * 10) / 10)
  return (
    <p className="unit-themes" aria-label={t.themes} title={t.themesLede}>
      <span className="muted small">{t.themes}</span>
      {res.data.themes.length === 0 ? (
        <span className="muted small">{t.noThemes}</span>
      ) : (
        res.data.themes.map((s) => (
          <DomainChip
            key={s.domain.code}
            domain={s.domain}
            extra={`×${s.lift.toFixed(1)}`}
            title={t.themeTitle(fmt(s.weight), fmt(s.expected), s.lift.toFixed(1))}
          />
        ))
      )}
    </p>
  )
}
