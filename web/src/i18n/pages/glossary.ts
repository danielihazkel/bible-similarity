// Interface strings of the glossary and the term popovers (DESIGN.md §11): the statistics and
// retrieval terms the pages use, explained once. English first, Hebrew typed against it.

export type TermKey =
  | 'p'
  | 'q'
  | 'shuffle'
  | 'g2'
  | 'rho'
  | 'auc'
  | 'kappa'
  | 'gold'
  | 'ndcg'
  | 'mrr'
  | 'recall'
  | 'csls'
  | 'rrf'
  | 'lemma'
  | 'hapax'
  | 'leitwort'
  | 'colon'
  | 'heaps'

/** The glossary's order: statistics, evaluation, retrieval, the text. */
export const TERMS: TermKey[] = ['p', 'q', 'shuffle', 'g2', 'rho', 'auc', 'kappa', 'gold', 'ndcg', 'mrr', 'recall', 'csls', 'rrf', 'lemma', 'hapax', 'leitwort', 'colon', 'heaps']

export interface TermText {
  term: string // as the pages write it
  name: string // spelled out
  def: string
}

export const glossEn = {
  title: 'Glossary',
  lede: 'The terms the pages use for their statistics and searches, each in a few words. On the Findings page and in table headings a dotted term opens its entry on hover, focus or a tap.',
  more: 'Glossary',
  open: (term: string) => `What is ${term}?`,
  terms: {
    p: { term: 'p', name: 'p-value', def: 'How often the shuffled versions of the data did at least as well as the real data. A small p (here, at most 0.05) means chance seldom gives the result; it does not say how large the effect is.' },
    q: { term: 'q', name: 'q-value (Benjamini–Hochberg)', def: 'A p-value adjusted for running many tests at once: of the results kept at q ≤ 0.05, about one in twenty is expected to be chance.' },
    shuffle: { term: 'shuffle', name: 'Shuffle (permutation test)', def: 'The data rearranged at random many times (verses, books, labels), keeping what the claim does not depend on. The real result is compared with the shuffled ones to give p.' },
    g2: { term: 'G²', name: 'G² (log-likelihood ratio)', def: 'How surprising a count is, given how common the word is overall and how much text there is. Higher is stronger; about 3.8 corresponds to p 0.05 for a single test.' },
    rho: { term: 'rho', name: 'Spearman’s rho', def: 'How well two orders agree, from −1 (reversed) through 0 (unrelated) to 1 (the same order).' },
    auc: { term: 'AUC', name: 'Area under the ROC curve', def: 'The chance that a score ranks a randomly chosen true case above a randomly chosen false one: 0.5 is guessing, 1 is perfect.' },
    kappa: { term: 'kappa', name: 'Cohen’s kappa', def: 'Agreement between two labellings beyond what chance gives: 0 is chance, 1 is full agreement.' },
    gold: { term: 'gold', name: 'Gold links', def: 'Parallels known in advance (Sefaria’s, OpenBible’s, ETCBC’s, your labels), used to measure the searches. Models are tuned on the dev books and measured once on the test books.' },
    ndcg: { term: 'nDCG@10', name: 'Normalized discounted cumulative gain', def: 'How high the known parallels stand in the first ten results, a hit at the top counting most: 1 is every known parallel at the top.' },
    mrr: { term: 'MRR', name: 'Mean reciprocal rank', def: 'One over the rank of the first known parallel, averaged over queries: 1 when it is always first, 0.5 when it is second.' },
    recall: { term: 'R@k', name: 'Recall at k', def: 'The share of known parallels found among the first k results.' },
    csls: { term: 'CSLS', name: 'Cross-domain similarity local scaling', def: 'A correction to similarity that keeps “hub” verses, close to everything, from crowding the top of every list.' },
    rrf: { term: 'fused', name: 'Fusion (reciprocal rank fusion)', def: 'The lexical and semantic lists merged by rank: a passage high in either list rises, one high in both rises most.' },
    lemma: { term: 'lemma', name: 'Lemma', def: 'A word’s dictionary form (its Strong’s number in OSHB), so that וַיֹּאמֶר and אָמַר count as one word.' },
    hapax: { term: 'hapax', name: 'Hapax legomenon', def: 'A word found once in the whole Bible.' },
    leitwort: { term: 'Leitwort', name: 'Leitwort (leading word)', def: 'A word repeated through a passage more than its frequency elsewhere predicts, binding the passage together (Buber, Rosenzweig).' },
    colon: { term: 'colon', name: 'Colon (verse half)', def: 'A line of verse, divided by the accents: most poetic verses have two or three, the second echoing the first.' },
    heaps: { term: 'Heaps’ law', name: 'Heaps’ law', def: 'Vocabulary grows more slowly than text: after N words a text has about K·N^b different words, b below 1.' },
  } satisfies Record<TermKey, TermText>,
  /** How the terms are written in running text (regular expressions), to mark them there. */
  patterns: [
    ['\\bp(?= [<\\d])', 'p'],
    ['\\bq(?= [≤<\\d])', 'q'],
    ['G²', 'g2'],
    ['Spearman’s rho', 'rho'],
    ['\\bAUC\\b', 'auc'],
    ['\\bkappa\\b', 'kappa'],
    ['nDCG@10', 'ndcg'],
    ['\\bMRR\\b', 'mrr'],
    ['Heaps’ law', 'heaps'],
    ['\\bLeitworte?\\b', 'leitwort'],
    ['shuffled', 'shuffle'],
  ] as [string, TermKey][],
}
