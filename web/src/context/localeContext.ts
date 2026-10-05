import { createContext, useContext } from 'react'
import { CATALOGS, type Locale, type Messages } from '../i18n'

export const LocaleContext = createContext<{ locale: Locale; m: Messages; setLocale: (l: Locale) => void }>({
  locale: 'en',
  m: CATALOGS.en,
  setLocale: () => {},
})

export const useLocale = () => useContext(LocaleContext)
/** The interface messages of the current language. */
export const useT = () => useContext(LocaleContext).m
