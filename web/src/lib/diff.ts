import type { DiffOp } from '../api/types'

export const DIFF_LABELS: Record<DiffOp, { label: string; hint: string }> = {
  substitution: { label: 'Substituted', hint: 'Another word (lemma) in the same place' },
  added: { label: 'Added', hint: 'Only in the later passage' },
  omitted: { label: 'Omitted', hint: 'Only in the earlier passage' },
  moved: { label: 'Moved', hint: 'Dropped in one place and added in another' },
  form: { label: 'Other form', hint: 'Same lemma, different prefix, suffix or inflection' },
  spelling: { label: 'Spelling', hint: 'Same word, written with or without ו / י (plene / defective)' },
}

export const DIFF_OPS = Object.keys(DIFF_LABELS) as DiffOp[]
