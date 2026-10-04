export const unitLink = (id: string, search = '') => `/unit/${encodeURIComponent(id)}${search}`

export const compareLink = (a: string, b: string) =>
  `/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`
