import { useLocale } from '../context/localeContext'

/**
 * A unit's or verse's label in the interface language: in English, the English label with the
 * Hebrew one beside it; in Hebrew, the Hebrew label alone.
 */
export function UnitName({ en, he, big, spaced }: { en: string; he: string; big?: boolean; spaced?: boolean }) {
  const { locale } = useLocale()
  if (locale === 'he') return <>{he}</>
  return (
    <>
      {en}
      {spaced && ' '}
      <span className={big ? 'he-label big' : 'he-label'} dir="rtl" lang="he">
        {he}
      </span>
    </>
  )
}
