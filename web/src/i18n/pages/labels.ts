// Interface strings of your labels (DESIGN.md §16.25): the buttons on proposed pairs and the
// Labels page. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

type LabelValue = 'real' | 'not' | 'unsure'

export const labEn = {
  group: 'Your judgement of this pair',
  values: { real: 'Real', not: 'Not', unsure: 'Unsure' } as Record<LabelValue, string>,
  titles: {
    real: 'A connection worth recording (click again to clear)',
    not: 'A coincidence of words or meaning (click again to clear)',
    unsure: 'Not sure yet (click again to clear)',
  } as Record<LabelValue, string>,
  removed: 'Label removed',
  noteSaved: 'Note saved',
  title: 'Your labels',
  lede: 'Pairs you judged on Discoveries and in the lists of similar passages: real connections, coincidences, and the ones you are unsure of. Together they are a third gold set, beside the Sefaria links and the OpenBible cross-references, and the only one that says which proposed pairs are not connections.',
  caveat: 'They describe what you were shown — mostly the top of one mode’s lists — not the whole canon. `bsim eval-labels` scores the final systems on the dev-split verse pairs, and nothing is tuned on those. Pairs between two training books can train a variant of the meaning model (see the queue). Labels are stored on this machine (data/labels.sqlite), apart from the results.',
  readOnly: 'This server shows labels read-only.',
  counts: (real: number, not: number, unsure: number) =>
    `${numEn(real)} real · ${numEn(not)} not · ${numEn(unsure)} unsure`,
  none: 'No labels yet: mark pairs as real or not on Discoveries or in a passage’s list of similar passages.',
  evalTitle: 'How each mode separates your pairs',
  evalLede: (k: number, min: number) =>
    `A mode finds a pair when either passage ranks the other within its top ${numEn(k)}. Precision: the share of what it finds that you marked real. AUC: how often a real pair ranks above a not pair (0.5 = chance; shown with at least ${numEn(min)} of each).`,
  unitType: 'Unit',
  mode: 'Mode',
  realFound: 'Real found',
  notFound: 'Not found',
  precision: 'Precision',
  auc: 'AUC',
  show: 'Show',
  all: 'All',
  pairs: 'Labelled pairs',
  judgedIn: (mode: string, score: string) => `judged in ${mode} (score ${score})`,
  note: 'Note',
  notePlaceholder: 'Why (optional)',
  view: 'View',
  views: { labels: 'Your labels', queue: 'What to judge next' },
  queueMode: 'the queue',
  queueLede:
    'Pairs where the two ways of reading disagree most: one mode ranks the pair near the top, the other low or not at all. Your judgement says which of them was right, so these are the pairs that teach the most. Only verse pairs between two training books are offered, so that your labels can train the meaning model while the dev and test books stay unseen.',
  queueTraining: (real: number, need: number) =>
    `You have ${numEn(real)} real pairs between training books. Training on them (bsim supervision-exp --only labels) needs ${numEn(need)}; your not pairs become the negatives the model is trained to rank low. The variant is kept only if it passes the adoption rule on the dev golds.`,
  queueSide: 'Ranked higher by',
  either: 'Either',
  queueCounts: (total: number, pool: number, labelled: number) =>
    `${numEn(total)} ${total === 1 ? 'pair' : 'pairs'} to judge · ${numEn(labelled)} of ${numEn(pool)} judged`,
  ranks: (lex: string, sem: string) => `lexical rank ${lex} · semantic rank ${sem}`,
  beyond: (k: number) => `beyond ${numEn(k)}`,
  queueNone: 'Nothing left to judge here.',
  queueMore: 'Next pairs',
  queueMoreTitle: 'Show the next pairs; the ones you judged leave the queue',
  queueMissing: 'The queue needs the book split: run bsim build-links.',
  llmLine: (model: string, auc: string, min: string, n: number, hebrew: boolean) =>
    `Suggestions by ${model} for the first ${numEn(n)} pairs of the queue (bsim llm-triage). Checked first on Sefaria’s dev links against random dev pairs: AUC ${auc} (shown from ${min}). They are suggestions only: nothing is labelled until you click, and its reasons are its own, in ${hebrew ? 'Hebrew' : 'English'}.`,
  llmHidden: (auc: string, min: string) =>
    `Claude’s suggestions are hidden: on Sefaria’s dev links against random dev pairs its AUC was ${auc}, below the ${min} fixed beforehand.`,
  onlySuggested: 'Only pairs with a suggestion',
  suggests: (verdict: string, p: string, kind: string) => `Claude suggests: ${verdict} (p ${p}, ${kind}).`,
  kinds: {
    quotation: 'quotation',
    allusion: 'allusion',
    parallel_account: 'parallel account',
    shared_formula: 'shared formula',
    shared_phrase: 'shared phrase',
    thematic: 'thematic',
    none: 'no connection',
  } as Record<string, string>,
}

register('lab', labEn)
