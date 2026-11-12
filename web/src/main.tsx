import '@fontsource/noto-serif-hebrew/400.css'
import '@fontsource/noto-serif-hebrew/600.css'
import './styles/global.css'
import { onlineManager, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ApiError } from './api/client'
import { App } from './App'
import { LocaleProvider } from './context/Locale'
import { TextModeProvider } from './context/TextMode'
import { ThemeProvider } from './context/Theme'
import { startServiceWorker } from './lib/pwa'
import { applyTheme, loadTheme } from './lib/theme'
import { registerSW } from 'virtual:pwa-register'

// react-query assumes online until an `offline` event; a page opened offline (the offline app)
// starts from the browser's own state, so its failed queries are fetched again on `online`
onlineManager.setOnline(navigator.onLine)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // API errors (404 / 422 / 503) are answers, not glitches: only retry network failures, and
      // not offline (the answer is not saved: say so at once, ErrorBox)
      retry: (n, e) => !(e instanceof ApiError) && navigator.onLine && n < 2,
      refetchOnWindowFocus: false,
      // offline, a query still asks once: the service worker may have its answer (vite.config.ts)
      networkMode: 'offlineFirst',
    },
  },
})

// the offline app (DESIGN.md §11.1): production builds only, so the dev server is never cached
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  startServiceWorker(registerSW)
}

// the theme before the first render (index.html has set it before the first paint already)
applyTheme(loadTheme())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <TextModeProvider>
          <ThemeProvider>
            <App />
          </ThemeProvider>
        </TextModeProvider>
      </LocaleProvider>
    </QueryClientProvider>
  </StrictMode>,
)
