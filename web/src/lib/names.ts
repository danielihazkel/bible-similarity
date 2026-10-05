// Labels in the interface language (the API sends both English and Hebrew ones).

/** The label of a unit-like object (`label_en` / `label_he`) in the interface language, as text. */
export function unitLabel(u: { label_en: string; label_he: string }, locale: string): string {
  return locale === 'he' ? u.label_he : u.label_en
}

/** A book's name in the interface language. */
export function bookName(b: { name: string; he_name: string }, locale: string): string {
  return locale === 'he' ? b.he_name : b.name
}

/** A book option in a select: both names in English, the Hebrew name alone in Hebrew. */
export function bookOption(b: { name: string; he_name: string }, locale: string): string {
  return locale === 'he' ? b.he_name : `${b.name} · ${b.he_name}`
}

/** A semantic domain's name: the Hebrew interface names the two top levels in Hebrew (`top`, from
 * the catalog); deeper domains keep SDBH's English name in both languages. */
export function domainLabel(d: { code: string; label_en: string }, top: Record<string, string>, locale: string): string {
  return locale === 'he' ? (top[d.code] ?? d.label_en) : d.label_en
}

/** A verse's reference in the interface language ("Genesis 1:1" / "בראשית א:א"). */
export function verseRef(v: { ref: string; ref_he: string }, locale: string): string {
  return locale === 'he' ? v.ref_he : v.ref
}
