import { createContext, useContext } from 'react'
import type { TextMode } from '../lib/hebrew'

export const TextModeContext = createContext<{ mode: TextMode; setMode: (m: TextMode) => void }>({
  mode: 'teamim',
  setMode: () => {},
})

export const useTextMode = () => useContext(TextModeContext)
