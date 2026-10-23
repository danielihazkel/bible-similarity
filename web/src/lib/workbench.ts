// The workbench's sets as the API reads them (DESIGN.md §16.64): items `kind:value` separated by
// `;`. The page edits a set item by item and keeps it in the URL as this text.

export interface SetItem {
  kind: string
  value: string
}

/** The items of a set, as written (blank items dropped; an item without a kind keeps it empty). */
export function splitSet(spec: string): SetItem[] {
  return spec
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const i = s.indexOf(':')
      return i < 0 ? { kind: '', value: s } : { kind: s.slice(0, i).trim().toLowerCase(), value: s.slice(i + 1).trim() }
    })
}

export function joinSet(items: SetItem[]): string {
  return items.map((it) => (it.kind ? `${it.kind}:${it.value}` : it.value)).join('; ')
}

/** The set with an item added, unless it is there already. */
export function addItem(spec: string, item: SetItem): string {
  const items = splitSet(spec)
  if (items.some((it) => it.kind === item.kind && it.value === item.value)) return joinSet(items)
  return joinSet([...items, item])
}

export function removeItem(spec: string, index: number): string {
  return joinSet(splitSet(spec).filter((_, i) => i !== index))
}

/** "42-83" -> [42, 83]; "5" -> [5, 5]; anything else -> null. */
export function parseRange(value: string): [number, number] | null {
  const m = /^(\d+)(?:-(\d+))?$/.exec(value)
  if (!m) return null
  return [Number(m[1]), Number(m[2] ?? m[1])]
}

/** p or q for reading: two significant digits, small ones as powers of ten. */
export function formatP(p: number): string {
  if (p === 0) return '0'
  return p < 0.001 ? p.toExponential(1) : String(Number(p.toPrecision(2)))
}

/** The pattern search query that finds a feature's value, where pattern search has the key. */
export function patternFor(feature: string, key: string): string | null {
  return feature === 'domain' ? null : `[${feature}=${key}]`
}
