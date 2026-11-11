// Interface strings of a unit's neighbourhood graph (DESIGN.md §11.1, D149). English first, Hebrew
// typed against it.

import { countEn } from '../fmt'
import { register } from '../en'

export const nbhEn = {
  title: (label: string) => `The neighbourhood of ${label}`,
  lede: 'The passages this one is most like, and the passages they are most like in turn, joined by what links each pair: shared wording, shared meaning, a shared phrase, a parallel already recorded, a parallel sequence, rare words in common, a citation, an echo between chapters. Click a passage to put it in the middle.',
  k: 'Hits per passage',
  hops: 'Steps out',
  hopNames: { 1: 'One', 2: 'Two' } as Record<number, string>,
  kindsLabel: 'Links shown',
  kinds: {
    lexical: 'Shared wording',
    semantic: 'Shared meaning',
    phrase: 'A shared phrase',
    known: 'A parallel already recorded',
    sequence: 'A parallel sequence',
    allusion: 'Rare words in common',
    citation: 'A citation',
    borrowing: 'A borrowing between chapters',
    echo: 'An echo between chapters',
    fused: 'Only on the combined list',
  } as Record<string, string>,
  colourNote: 'A link is drawn in the colour of the first of its kinds in this list.',
  graphLabel: 'The neighbourhood as a graph',
  nodeTitle: (label: string, hop: number) => (hop === 0 ? `${label}: the passage in the middle` : `${label}: ${countEn(hop, 'step', 'steps')} out`),
  truncated: (n: number) => `Only the first ${n} passages are drawn; fewer hits per passage or one step out shows the rest.`,
  none: 'Nothing is stored as like this passage.',
  zoomIn: 'Zoom in',
  zoomOut: 'Zoom out',
  reset: 'Back to the whole graph',
  svg: 'Download the graph (SVG)',
  open: 'Open the passage',
  tableTitle: (n: number) => `The ${countEn(n, 'passage', 'passages')} drawn`,
  cols: { passage: 'Passage', hop: 'Steps out', kinds: 'Linked to the middle by', centre: 'Put in the middle' },
  centreIt: 'In the middle',
  link: 'Its neighbourhood as a graph',
}

register('nbh', nbhEn)
