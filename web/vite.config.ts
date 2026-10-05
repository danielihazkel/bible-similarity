/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: the viewer runs on :5173 and proxies /api to `bsim serve` (serve.host / serve.port in
// configs/default.yaml). Production: `npm run build` writes dist/, which `bsim serve` serves at /.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: { outDir: 'dist' },
  // component tests opt in with `// @vitest-environment jsdom`; e2e/ is Playwright's (`npm run e2e`)
  test: { environment: 'node', exclude: ['e2e/**', 'node_modules/**'] },
})
