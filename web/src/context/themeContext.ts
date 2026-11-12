import { createContext, useContext } from 'react'
import type { Shade, Theme } from '../lib/theme'

/** `theme` is the viewer's choice (auto / light / dark), `shade` what is on screen (light / dark). */
export const ThemeContext = createContext<{ theme: Theme; shade: Shade; setTheme: (t: Theme) => void }>({
  theme: 'auto',
  shade: 'light',
  setTheme: () => {},
})

export const useTheme = () => useContext(ThemeContext)
