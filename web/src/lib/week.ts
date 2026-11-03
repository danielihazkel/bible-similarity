// Dates for this week's parasha (DESIGN.md §11.1): the viewer's own date, and a Shabbat's date
// written in the interface's language.

/** Today in the viewer's time zone, as YYYY-MM-DD (the API counts from it). */
export function localToday(now = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`
}

export const isIsoDate = (v: string | null): v is string => v !== null && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v))

/** A date (YYYY-MM-DD) as the interface writes it: "7 November 2026", "7 בנובמבר 2026". */
export function longDate(iso: string, locale: 'en' | 'he'): string {
  return new Intl.DateTimeFormat(locale === 'he' ? 'he-IL' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`))
}
