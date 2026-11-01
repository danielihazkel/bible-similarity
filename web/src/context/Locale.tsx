import { type ReactNode, useEffect, useState } from 'react'
import { catalogOf, dirOf, EN, loadCatalog, LOCALES, type Locale, type Messages } from '../i18n'
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
  // the language shown and its messages change together. A chosen language whose catalog is still
  // loading (Hebrew, a chunk of its own) leaves the current one on screen until it arrives: English
  // on a first Hebrew load, so the app (and its keyboard shortcuts) is there at once.
  const [wanted, setWanted] = useState<Locale>(() => initial ?? load())
  const [shown, setShown] = useState<{ locale: Locale; m: Messages }>(() => {
    const c = catalogOf(wanted)
    return c ? { locale: wanted, m: c } : { locale: 'en', m: EN }
  })
  useEffect(() => {
    if (shown.locale === wanted) return
    let live = true
    loadCatalog(wanted).then((c) => live && setShown({ locale: wanted, m: c }))
    return () => {
      live = false
    }
  }, [wanted, shown.locale])
  useEffect(() => {
    if (shown.locale !== wanted) return // index.html set them for the wanted language already
    document.documentElement.lang = shown.locale
    document.documentElement.dir = dirOf(shown.locale)
  }, [shown.locale, wanted])
  const setLocale = (l: Locale) => {
    try {
      localStorage.setItem(LOCALE_KEY, l)
    } catch {
      // ignore
    }
    setWanted(l)
    const c = catalogOf(l)
    if (c) setShown({ locale: l, m: c })
  }
  return <LocaleContext.Provider value={{ locale: shown.locale, m: shown.m, setLocale }}>{children}</LocaleContext.Provider>
}
