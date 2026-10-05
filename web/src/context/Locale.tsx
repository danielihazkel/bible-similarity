import { type ReactNode, useEffect, useState } from 'react'
import { CATALOGS, dirOf, LOCALES, type Locale } from '../i18n'
import { LocaleContext } from './localeContext'

// The interface language: a per-viewer preference (not view state), so it lives in localStorage,
// not the URL. index.html reads the same key to set `dir` / `lang` before the first paint.
export const LOCALE_KEY = 'bsim.locale'

function load(): Locale {
  try {
    const v = localStorage.getItem(LOCALE_KEY)
    if (LOCALES.some((l) => l.value === v)) return v as Locale
  } catch {
    // storage unavailable (private window, blocked site data)
  }
  return 'en'
}

export function LocaleProvider({ children, initial }: { children: ReactNode; initial?: Locale }) {
  const [locale, set] = useState<Locale>(() => initial ?? load())
  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = dirOf(locale)
  }, [locale])
  const setLocale = (l: Locale) => {
    set(l)
    try {
      localStorage.setItem(LOCALE_KEY, l)
    } catch {
      // ignore
    }
  }
  return <LocaleContext.Provider value={{ locale, m: CATALOGS[locale], setLocale }}>{children}</LocaleContext.Provider>
}
