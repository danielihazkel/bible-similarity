// Number and plural helpers shared by the catalogs.

export const numEn = (n: number) => n.toLocaleString('en-US')
export const numHe = (n: number) => n.toLocaleString('he-IL')
/** English count: "1 verse", "2 verses". */
export const countEn = (n: number, one: string, other: string) => `${numEn(n)} ${n === 1 ? one : other}`
/** Hebrew count with its one / two / many forms: "פסוק אחד", "שני פסוקים", "5 פסוקים". */
export const countHe = (n: number, one: string, two: string, many: string) =>
  n === 1 ? one : n === 2 ? two : `${numHe(n)} ${many}`
export const pct = (x: number) => `${Math.round(x * 100)}%`
