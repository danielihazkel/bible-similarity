// The colour theme: a per-viewer preference (not view state), so it lives in localStorage. `auto`
// follows the system. The choice is resolved to light or dark and written as `data-theme` on
// <html>: the dark tokens key on `:root[data-theme='dark']` alone (styles/global.css). index.html
// does the same before the first paint (it reads the same key).

export type Theme = 'auto' | 'light' | 'dark'
export type Shade = 'light' | 'dark'

export const THEME_KEY = 'bsim.theme'
export const THEMES: Theme[] = ['auto', 'light', 'dark']

const systemDark = () => (typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : undefined)

export function loadTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (THEMES.includes(v as Theme)) return v as Theme
  } catch {
    // storage unavailable (private window, blocked site data)
  }
  return 'auto'
}

export function saveTheme(theme: Theme) {
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch {
    // ignore
  }
}

/** Light or dark: the choice itself, or the system's on `auto`. */
export const shadeOf = (theme: Theme): Shade => (theme === 'auto' ? (systemDark()?.matches ? 'dark' : 'light') : theme)

/** Writes the resolved theme on <html> and returns it. */
export function applyTheme(theme: Theme): Shade {
  const shade = shadeOf(theme)
  document.documentElement.setAttribute('data-theme', shade)
  return shade
}

/** Calls `f` when the system changes between light and dark; returns the way to stop. */
export function onSystemTheme(f: () => void): () => void {
  const q = systemDark()
  if (!q) return () => {}
  q.addEventListener('change', f)
  return () => q.removeEventListener('change', f)
}
