import type { DiffOp } from '../api/types'

// labels and hints: the catalogs' `diff.ops` (src/i18n)
export const DIFF_OPS: DiffOp[] = ['substitution', 'added', 'omitted', 'moved', 'form', 'spelling']
