// Interface languages (DESIGN.md §11.1). English is the default; Hebrew is opt-in.
import { en, type Messages } from './en'
import { he } from './he'

export type Locale = 'en' | 'he'
export type { Messages }

export const CATALOGS: Record<Locale, Messages> = { en, he }

export const LOCALES: { value: Locale; label: string; title: string }[] = [
  { value: 'en', label: 'EN', title: 'English interface' },
  { value: 'he', label: 'עב', title: 'ממשק בעברית' },
]

export const dirOf = (l: Locale) => (l === 'he' ? 'rtl' : 'ltr')
