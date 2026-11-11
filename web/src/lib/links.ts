export const unitLink = (id: string, search = '') => `/unit/${encodeURIComponent(id)}${search}`

export const readLink = (id: string, search = '') => `/read/${encodeURIComponent(id)}${search}`

/** A unit's neighbourhood graph (§11.1, D149), with its settings (k, hops, off) if any. */
export const neighbourhoodLink = (id: string, params?: URLSearchParams) => {
  const q = params?.toString()
  return `/neighbourhood/${encodeURIComponent(id)}${q ? `?${q}` : ''}`
}

export const lemmaLink = (lemma: string) => `/lemma/${encodeURIComponent(lemma)}`
export const rootLink = (root: string) => `/root/${encodeURIComponent(root)}`

export const compareLink = (a: string, b: string) =>
  `/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`

export const nameLink = (lemma: string) => `/names?e=${encodeURIComponent(lemma)}`

export const domainLink = (code: string) => `/domains/${encodeURIComponent(code)}`

export const sequenceLink = (id: number) => `/sequences/${id}`

export const placeLink = (id: number) => `/places?p=${id}`

export const personLink = (id: number | string) => `/genealogy?p=${id}`
