import { type ReactNode, useEffect, useLayoutEffect, useState } from 'react'
import { applyTheme, loadTheme, onSystemTheme, saveTheme, shadeOf, type Shade, type Theme } from '../lib/theme'
import { ThemeContext } from './themeContext'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, set] = useState<Theme>(loadTheme)
  const [shade, setShade] = useState<Shade>(() => shadeOf(theme))
  // main.tsx (and index.html before it) has written the attribute already; this keeps it there
  useLayoutEffect(() => {
    applyTheme(theme)
  }, [theme])
  // on auto the page follows the system as it changes
  useEffect(() => {
    if (theme !== 'auto') return
    return onSystemTheme(() => setShade(applyTheme('auto')))
  }, [theme])
  const setTheme = (t: Theme) => {
    saveTheme(t)
    set(t)
    setShade(applyTheme(t))
  }
  return <ThemeContext.Provider value={{ theme, shade, setTheme }}>{children}</ThemeContext.Provider>
}
