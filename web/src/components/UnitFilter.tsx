import { Link } from 'react-router'
import { useUnit } from '../api/hooks'
import { useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { UnitName } from './UnitName'

/** The `unit=` filter of a list page: which unit the list is limited to, and a way back to all. */
export function UnitFilter({ unitId, onClear }: { unitId: string; onClear: () => void }) {
  const m = useT()
  const unit = useUnit(unitId).data?.unit
  return (
    <p className="unit-filter" role="status">
      {m.filter.onlyTouching}{' '}
      <Link to={unitLink(unitId)}>{unit ? <UnitName en={unit.label_en} he={unit.label_he} spaced /> : unitId}</Link>{' '}
      ·{' '}
      <button type="button" className="linkish" onClick={onClear}>
        {m.filter.showAll}
      </button>
    </p>
  )
}
