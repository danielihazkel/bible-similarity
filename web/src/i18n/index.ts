// Interface languages (DESIGN.md §11.1). English is the default and ships with the viewer;
// Hebrew is opt-in and its catalog (`he.ts` and `pages/he/`) is a chunk loaded when it is chosen.
import { en, type Messages } from './en'

export type Locale = 'en' | 'he'
export type { Messages }

export const EN: Messages = en

const loaded: Partial<Record<Locale, Messages>> = { en }

/** A language's messages if they are loaded (English always is). */
export const catalogOf = (l: Locale): Messages | undefined => loaded[l]

/** Load a language's messages (once). */
export async function loadCatalog(l: Locale): Promise<Messages> {
  if (!loaded[l]) loaded[l] = (await import('./he')).he
  return loaded[l]
}

export const LOCALES: { value: Locale; label: string; title: string }[] = [
  { value: 'en', label: 'EN', title: 'English interface' },
  { value: 'he', label: 'עב', title: 'ממשק בעברית' },
]

export const dirOf = (l: Locale) => (l === 'he' ? 'rtl' : 'ltr')
