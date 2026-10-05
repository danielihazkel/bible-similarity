import { Link } from 'react-router'
import { useUnit } from '../api/hooks'
import { unitLink } from '../lib/links'

/** The `unit=` filter of a list page: which unit the list is limited to, and a way back to all. */
export function UnitFilter({ unitId, onClear }: { unitId: string; onClear: () => void }) {
  const unit = useUnit(unitId).data?.unit
  return (
    <p className="unit-filter" role="status">
      Only those touching{' '}
      <Link to={unitLink(unitId)}>{unit ? unit.label_en : unitId}</Link>
      {unit && (
        <>
          {' '}
          <span className="he-label" dir="rtl" lang="he">
            {unit.label_he}
          </span>
        </>
      )}{' '}
      ·{' '}
      <button type="button" className="linkish" onClick={onClear}>
        Show all
      </button>
    </p>
  )
}
