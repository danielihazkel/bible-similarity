// Interface strings of the Parallels pages: English first, Hebrew typed against it (see ../en.ts).

import type { RewriteOp, SequenceDirection } from '../../api/types'
import { numEn } from '../fmt'
import { register } from '../en'

type Labelled = { label: string; hint: string }

export const parEn = {
  book: 'Book',
  allBooks: 'All books',
  differentBooks: 'Different books only',
  includeQ: 'Include q > 0.05',
  /** "from → to" between two passages or words */
  arrow: '→',
  pairsPage: (n: number, page: number, pages: number) => `${numEn(n)} pairs · page ${page} of ${pages}`,

  discoveries: {
    title: 'Discoveries',
    ledeBefore: 'The strongest pairs that Sefaria does ',
    ledeNot: 'not',
    ledeAfter:
      ' cross-reference: one unit ranks the other in its top 10, no Sefaria link joins them, and neighbouring verses are left out.',
    none: 'No unlinked pairs match these filters.',
    rankFor: (b: string, rank: number, a: string) => `${b} is #${rank} for ${a}`,
    mutualTitle: "Each is in the other's top 10",
    mutual: 'mutual',
  },

  phrases: {
    title: 'Shared phrases',
    lede: 'Verse pairs whose lemmas line up as a phrase (same words in the same order, small gaps allowed). Rare words weigh more and formulaic phrases barely count, so quotations, allusions and parallel accounts come first.',
    atLeast: 'At least',
    recurringTitle: (n: number) => `Show phrases shared by more than ${n} verses (idioms)`,
    recurring: 'Include recurring phrases',
    none: 'No shared phrases match these filters.',
    views: { phrases: 'Phrases', spread: 'Spread over verses' },
    viewLabel: 'What to list',
  },

  spread: {
    lede: (w: number) =>
      `Passages of ${w} verses sharing at least three rare words (found in 15 verses or fewer, names left out), wherever they stand in the passages: an allusion can borrow a few words without quoting a phrase. Verse order shuffled within every chapter gives the chance level (q): it keeps each chapter's vocabulary and only scatters the words.`,
    finding: (pairs: number, known: number, strong: number, strongKnown: number, best: string) =>
      `${numEn(pairs)} passage pairs, ${numEn(known)} of them already found as parallels. ${numEn(strong)} beat the shuffles (q ≤ 0.05), all known parallels (${numEn(strongKnown)}); the best new pair has q ${best}. The new pairs are leads, not findings.`,
    onlyNew: 'Only pairs not found as parallels',
    none: 'No passage pairs match these filters.',
    shared: (n: number) => `${numEn(n)} rare words`,
    known: 'known parallel',
    page: (n: number, page: number, pages: number) => `${numEn(n)} passage pairs · page ${page} of ${pages}`,
    noData: 'Not computed in this build: run `bsim allusions`, then `bsim build-db`.',
  },

  sequences: {
    title: 'Parallel sequences',
    lede: 'Passages that run alongside each other verse by verse, in the same order: synoptic accounts (Samuel–Kings and Chronicles), retold stories, a command and its execution, repeated lists. Each chain links similar verse pairs whose positions advance together on both sides; q estimates how often such a chain appears when verse order is shuffled within chapters.',
    order: 'Order',
    orders: {
      forward: { label: 'Same order', hint: 'Both passages advance together' },
      reverse: { label: 'Mirrored', hint: 'One passage runs backwards: A B C … C′ B′ A′' },
      mixed: { label: 'Reordered', hint: 'The same scene told in another order' },
      any: { label: 'Any order', hint: 'Same, mirrored and reordered chains' },
    } satisfies Record<SequenceDirection | 'any', Labelled>,
    significance: 'Significance',
    qOptions: { '0.05': 'q ≤ 0.05 (strong)', '0.2': 'q ≤ 0.2', all: 'All chains' } as Record<string, string>,
    hideRepeatsTitle: 'Hide repeats inside one chapter (lists such as Numbers 7)',
    hideRepeats: 'Hide repeats within a chapter',
    none: 'No sequences match these filters.',
    mirroredHint: ' Mirrored and reordered chains never beat the shuffled-order baseline: choose “All chains”.',
    viewLabel: 'View',
    views: { list: 'List', arcs: 'Across the canon' },
    arcs: {
      label: 'Parallel sequences across the canon',
      legend: 'Each arc joins the two passages of a chain; the books run in canon order along the line, and thicker arcs have more verse pairs. Select an arc to read its chain; choosing a book brings out its arcs.',
      crossBook: 'between books',
      withinBook: 'within a book',
      count: (n: number, cross: number) => `${numEn(n)} chains, ${numEn(cross)} of them between books`,
      capped: (n: number, total: number) => ` (the ${numEn(n)} strongest of ${numEn(total)})`,
      arc: (a: string, b: string, n: number) => `${a} ↔ ${b}, ${numEn(n)} verse pairs`,
    },
    page: (n: number, page: number, pages: number) => `${numEn(n)} sequences · page ${page} of ${pages}`,
    synopses: 'Where three or more passages run parallel, read them side by side as a synopsis.',
  },

  sequence: {
    notId: 'Not a sequence id.',
    versePairs: (n: number) => `${n} verse pairs`,
    directions: {
      reverse: 'in mirrored order (the right side runs backwards)',
      mixed: 'in another order (the right side jumps back and forth)',
      forward: 'in the same order',
    } as Record<string, string>,
    score: (s: string) => `score ${s}`,
    noneLinked: 'none linked in Sefaria',
    linked: (n: number) => `${n} linked in Sefaria (★)`,
    onlySides: (a: number, b: number) => ` · ${a} verse(s) only on the left, ${b} only on the right`,
    markChanges: 'Mark word changes',
    loose: '≈ loosely parallel, not marked',
    aligned: 'Aligned verses',
    cosineTitle: (cos: string, gold: boolean, loose: boolean) =>
      `Cosine ${cos}${gold ? ' · linked in Sefaria' : ''}${loose ? ' · loosely parallel: too different to mark word by word' : ''}`,
  },

  changes: {
    title: 'How parallels differ',
    lede: 'Every verse pair of a strong parallel sequence aligned word by word, the earlier passage (in canon order) on the left. Counted across the corpus, the changes show habits of the later text: Chronicles writes דויד for דוד, על for אל, אני for אנכי, and often אלהים where Samuel–Kings has יהוה.',
    view: 'View',
    byWord: 'All changes by word',
    rewrites: 'Systematic rewrites',
    kind: 'Kind of change',
    opCount: (label: string, n: number) => `${label} ${numEn(n)}`,
    anyBook: 'Any book',
    earlierIn: 'Earlier passage in',
    laterIn: 'Later passage in',
    none: 'No changes of this kind for these books.',
    page: (n: number, page: number, pages: number) => `${numEn(n)} distinct changes · page ${page} of ${pages}`,
    earlier: 'Earlier',
    later: 'Later',
    times: 'Times',
    sequences: 'Sequences',
    examples: 'Examples',
    openSequence: 'Open the parallel sequence',
  },

  rewrites: {
    intro:
      "A change counts as a habit when it recurs between two books more often than their overall rate of change explains: the later book's word, given the earlier one, compared by log-likelihood (G²), with q corrected for testing every change of every book pair.",
    books: 'Books',
    allPairs: 'All book pairs',
    within: (name: string) => `${name} (repeats within)`,
    pair: (a: string, b: string) => `${a} → ${b}`,
    optionPairs: (n: number) => `${n} verse pairs`,
    change: 'Change',
    any: 'Any',
    ops: {
      substitution: { label: 'Substituted', hint: 'one word regularly replaced by another' },
      omitted: { label: 'Dropped', hint: 'a word the later text regularly leaves out' },
      added: { label: 'Added', hint: 'a word the later text regularly adds' },
    } satisfies Record<RewriteOp, Labelled>,
    none: 'No systematic changes for these filters.',
    page: (n: number, page: number, pages: number) => `${numEn(n)} changes · page ${page} of ${pages}`,
    timesTitle: 'Times this change occurs / words it could apply to',
    qTitle: 'Benjamini–Hochberg q over all book pairs and changes',
    rateTitle: (rate: number) => `${Math.round(rate * 100)}% of the time`,
    profile: 'How these books differ',
    parallelVerses: 'Parallel verses',
    profilePairs: (n: number, aWords: number, bWords: number) => `${n} pairs, ${numEn(aWords)} → ${numEn(bWords)} words`,
    per100Of: (from: string) => `Per 100 words of ${from}`,
    per100: (sub: string, om: string, add: string, form: string, spell: string) =>
      `${sub} substituted · ${om} dropped · ${add} added · ${form} other form · ${spell} spelling`,
    spelling: 'Spelling',
    spellingText: (to: string, from: string, plene: number, defective: number, fuller: number) =>
      `${to} writes a vowel letter (ו / י) ${from} lacks ${plene}× and drops one ${defective}× (${fuller}% fuller)`,
  },

  typeScenes: {
    title: 'Action sequences',
    lede: "Two passages that tell the same actions in the same order, whatever the names and wording: the verbs of every pericope are aligned with those of others (rare verbs count more), and each alignment is compared with the same passages' verbs shuffled. The strongest are court tales (Daniel 3 and 6: accused, thrown in, rescued), ritual procedures and visions retold.",
    note: 'The classic literary type-scenes (meetings at a well, annunciations to barren women) vary their verbs too much to stand out this way: they score little above random pairs of chapters.',
    textualTitle: 'Pairs joined by a parallel sequence: the same text told twice',
    textual: 'Include textual parallels',
    none: 'No aligned passages for these filters.',
    actions: (n: number) => `${n} actions in order`,
    qTitle: 'Expected share of chance alignments among those at least this strong (verb order shuffled inside each passage)',
    textualTag: 'textual parallel',
  },

  synopses: {
    title: 'Synopses',
    lede: 'Where a passage runs parallel to two or more others, their parallel sequences are joined into one synopsis: verses aligned by any of the chains share a row, so Jeremiah 52, Jeremiah 39 and II Kings 24–25 on the fall of Jerusalem, or I Chronicles 16 with the two psalms it quotes, are read side by side. Only strong same-order chains (q ≤ 0.05) are joined; two passages with a single chain between them are read as its ladder under Parallel sequences.',
    passages: 'Passages',
    rows: 'Rows',
    aligned: 'Aligned rows',
    chains: 'Chains',
    count: (n: number) => (n === 1 ? 'One synopsis' : `${numEn(n)} synopses`),
    none: 'No parallel sequences join into a synopsis in this build.',
  },

  synopsis: {
    notId: 'Not a synopsis id.',
    summary: (rows: number, aligned: number, cols: number) =>
      `${numEn(rows)} rows, ${numEn(aligned)} with verses in two or more of the ${cols} columns.`,
    order: 'The rows follow the first column; a verse marked ↶ goes back in its own book’s order.',
    joined: 'Joined from the parallel sequences',
    breaks: (n: number) => `${n} row(s) placed against a chain’s order, where the chains disagree.`,
    dropped: (n: number) => `${n} aligned pair(s) left out: they would put one passage twice in a row.`,
    base: 'Mark against',
    baseHint: 'Every column is marked against this one; its own words are marked where any column differs.',
    loose: '≈ too different from the marked-against verse to diff word by word',
    looseTitle: 'Too different from the verse it is marked against to diff word by word',
    reordered: '↶ goes back in its book’s order',
    rows: 'Verses side by side',
    partOf: (n: number) => `Part of a synopsis of ${n} passages`,
  },
}

register('par', parEn)
