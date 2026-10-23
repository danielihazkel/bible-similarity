// The divine names page (DESIGN.md §16.65): a chapter's mix of יהוה and אלהים as a colour step.

/** The mix's colour step: two arms of two steps each around a neutral middle; `none` without
 * either name. */
export function shareStep(share: number | null): 'y2' | 'y1' | 'mid' | 'e1' | 'e2' | 'none' {
  if (share === null) return 'none'
  if (share >= 0.9) return 'y2'
  if (share >= 0.6) return 'y1'
  if (share > 0.4) return 'mid'
  if (share > 0.1) return 'e1'
  return 'e2'
}
