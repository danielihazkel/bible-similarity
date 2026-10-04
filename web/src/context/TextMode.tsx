import { useState, type ReactNode } from 'react'
import { TEXT_MODES, type TextMode } from '../lib/hebrew'
import { TextModeContext } from './textModeContext'

// A per-viewer display preference (not view state), so it lives in localStorage, not the URL.
const KEY = 'bsim.textMode'

function load(): TextMode {
  try {
    const v = localStorage.getItem(KEY)
    if (TEXT_MODES.some((m) => m.value === v)) return v as TextMode
  } catch {
    // storage unavailable (private window, blocked site data)
  }
  return 'teamim'
}

export function TextModeProvider({ children }: { children: ReactNode }) {
  const [mode, set] = useState<TextMode>(load)
  const setMode = (m: TextMode) => {
    set(m)
    try {
      localStorage.setItem(KEY, m)
    } catch {
      // ignore
    }
  }
  return <TextModeContext.Provider value={{ mode, setMode }}>{children}</TextModeContext.Provider>
}
