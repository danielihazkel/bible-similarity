/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// Dev: the viewer runs on :5173 and proxies /api to `bsim serve` (serve.host / serve.port in
// configs/default.yaml). Production: `npm run build` writes dist/, which `bsim serve` serves at /.

// GET /api routes the service worker never caches: your labels and notebook and the server's
// state (`NO_STORE_PATHS` in src/bsim/api/app.py; tests/test_api.py keeps them in step), and the
// CSV downloads. The one no-store route cached is /dossier/{unit}: network first never shows it
// stale online, and offline a unit page keeps its dossier (its label count as last seen).
// Matched against the whole URL, from the origin on.
export const NETWORK_ONLY = String.raw`^https?://[^/]+/api/(?:labels|notebook|meta|export/)`

// The offline app (DESIGN.md §11.1, D136): a service worker precaches the viewer's shell (every
// built file but the source maps), so every page opens without the server; the answers of /api
// GETs are cached as they are fetched, network first: online, every answer comes from the server
// (a 304 against the build's ETag when unchanged, M109), as fresh as without the worker;
// offline, the last answer for that URL is served. A new build waits until you reload (the
// banner of components/AppBanner.tsx), so a page is never swapped under you.
const API_ENTRIES = 1000 // /api answers kept (least recently used dropped first)

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      injectRegister: false, // main.tsx registers it (production builds only)
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Tanakh Similarity',
        short_name: 'Tanakh Similarity',
        description: 'Parallels, echoes and patterns across the Hebrew Bible, in Hebrew.',
        lang: 'en',
        dir: 'ltr',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#faf6ee', // --bg (styles/global.css)
        theme_color: '#6b4f2a', // the icon's
        icons: [
          { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
        // the Hebrew name, for the browsers that read localized manifest members (others show
        // the English one); not in the plugin's types, hence the spread
        ...{
          name_localized: { he: { value: 'מקבילות בתנ״ך', lang: 'he', dir: 'rtl' } },
          short_name_localized: { he: { value: 'מקבילות', lang: 'he', dir: 'rtl' } },
        },
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        navigateFallback: '/index.html',
        // the API and FastAPI's own pages are the server's, never the viewer's index.html
        navigateFallbackDenylist: [/^\/api(?:\/|$)/, /^\/docs/, /^\/redoc/, /^\/openapi\.json/],
        clientsClaim: true, // the first visit is offline-ready without a reload
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          { urlPattern: new RegExp(NETWORK_ONLY), handler: 'NetworkOnly' },
          {
            urlPattern: /^https?:\/\/[^/]+\/api\//,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'bsim-api',
              cacheableResponse: { statuses: [200] }, // never an error or a 503 while loading
              expiration: { maxEntries: API_ENTRIES, purgeOnQuotaError: true },
            },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        // the libraries in a chunk of their own: they change far less often than the viewer, so the
        // browser keeps them across rebuilds; d3-hierarchy stays with the one page that uses it
        manualChunks: (id) =>
          /node_modules\/(react|react-dom|scheduler|react-router|@tanstack)\//.test(id) ? 'vendor' : undefined,
      },
    },
  },
  // component tests opt in with `// @vitest-environment jsdom`; e2e/ is Playwright's (`npm run e2e`)
  test: { environment: 'node', exclude: ['e2e/**', 'node_modules/**'], setupFiles: ['src/test/setup.ts'] },
})
