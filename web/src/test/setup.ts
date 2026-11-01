// Component tests render in either language at once: load the Hebrew catalog (a chunk of its own in
// the viewer, fetched when chosen) before any test runs.
import { loadCatalog } from '../i18n'

await loadCatalog('he')
