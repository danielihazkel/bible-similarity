import '@fontsource/noto-serif-hebrew/400.css'
import '@fontsource/noto-serif-hebrew/600.css'
import './styles/global.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ApiError } from './api/client'
import { App } from './App'
import { TextModeProvider } from './context/TextMode'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // API errors (404 / 422 / 503) are answers, not glitches: only retry network failures.
      retry: (n, e) => !(e instanceof ApiError) && n < 2,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TextModeProvider>
        <App />
      </TextModeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
