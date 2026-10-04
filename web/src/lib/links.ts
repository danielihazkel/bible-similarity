export const unitLink = (id: string, search = '') => `/unit/${encodeURIComponent(id)}${search}`

export const lemmaLink = (lemma: string) => `/lemma/${encodeURIComponent(lemma)}`

export const compareLink = (a: string, b: string) =>
  `/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`
