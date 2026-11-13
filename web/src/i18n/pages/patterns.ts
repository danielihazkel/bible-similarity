// Interface strings of the Patterns pages: English first, Hebrew typed against it (see ../en.ts).
// Structure, Acrostics, Poetry (parallel halves, word pairs) and Wordplay (pairs, alliteration, rhyme).

import type { StructureSort, WordplayPair } from '../../api/types'
import { countEn, numEn } from '../fmt'
import { register } from '../en'

type Basis = 'semantic' | 'lexical'
type StructureCol = 'semantic_chiasm_pct' | 'lexical_chiasm_pct' | 'semantic_inclusio_pct' | 'lexical_inclusio_pct'

export const patEn = {
  pageOf: (page: number, pages: number) => `page ${page} of ${pages}`,
  units: (n: number) => countEn(n, 'unit', 'units'),
  chapters: (n: number) => countEn(n, 'chapter', 'chapters'),
  pairs: (n: number) => countEn(n, 'pair', 'pairs'),
  cola: (n: number) => countEn(n, 'colon', 'cola'),
  runs: (n: number) => countEn(n, 'run', 'runs'),
  kind: 'Kind',
  any: 'Any',
  view: 'View',

  structure: {
    title: 'Structure',
    lede: [
      'Units whose verses frame them (',
      'inclusio',
      ': the opening returns at the close) or mirror each other (',
      'chiasm',
      ': A B C … C′ B′ A′), each scored against random pairs of the same unit. Open a unit for its heatmap and Leitworte.',
    ],
    sorts: {
      semantic_chiasm: 'Chiasm (semantic)',
      lexical_chiasm: 'Chiasm (lexical)',
      semantic_inclusio: 'Inclusio (semantic)',
      lexical_inclusio: 'Inclusio (lexical)',
    } satisfies Record<StructureSort, string>,
    cols: {
      semantic_chiasm_pct: 'Chiasm sem',
      lexical_chiasm_pct: 'Chiasm lex',
      semantic_inclusio_pct: 'Inclusio sem',
      lexical_inclusio_pct: 'Inclusio lex',
    } satisfies Record<StructureCol, string>,
    sortBy: 'Sort by',
    atLeast: 'At least',
    minVerses: (n: number) => `${n} verses`,
    note: 'Percentiles are per unit; with thousands of units about 5 % reach the 95th by chance. The q column corrects for that (Benjamini–Hochberg over all units of the type): only units with q ≤ 0.05 stand out from chance.',
    empty: 'No scored units.',
    unit: 'Unit',
    verses: 'Verses',
    sevens: (leitworte: number, multiples: number, expected: number, ratio: string, divisors: string, range: string | null, below: number) =>
      `Sevens: of ${numEn(leitworte)} chapter Leitworte, ${multiples} occur a multiple of 7 times against ${expected} expected from words with similar counts (${ratio}×). Other divisors (${divisors}) show ${range ?? 'no data'}${below === 0 ? ', so nothing singles out 7.' : `; ${below} of them less than 7.`}`,
  },

  panel: {
    computing: 'Computing structure…',
    basis: 'Similarity basis',
    hints: {
      semantic: 'cosine of the semantic verse embeddings',
      lexical: 'cosine of idf-weighted lemma bags (shared rare words)',
    } satisfies Record<Basis, string>,
    verseByVerse: (hint: string) => `Verse × verse similarity: ${hint}.`,
    inclusio: 'Inclusio',
    inclusioHint: 'opening and closing verses echo each other',
    chiasm: 'Chiasm',
    chiasmHint: 'mirror pairs (1st ↔ last, 2nd ↔ second-to-last …) are more alike than other pairs at the same distance',
    note: 'Percentiles compare the unit with itself (random pairs of the same unit). Across thousands of units some reach the 95th by chance: treat them as leads to read.',
    echoes: 'Strongest internal echoes',
    leitworte: 'Leitworte',
    leitworteLede: 'Lemmas this unit uses far more than the rest of the Tanakh (log-likelihood). Click to highlight.',
    leitwortTitle: (count: number, expected: string, g2: string) => `${count} times here, ${expected} expected · G² ${g2}`,
    tooFew: 'Too few verses.',
    percentile: (p: number) => `${Math.round(p * 100)}th percentile`,
    meanMirror: 'mean mirror similarity ',
    heatmap: 'Verse-by-verse similarity heatmap; arrow keys move between cells',
    heatmapKey: 'Darker = more similar · outlined cells = mirror pairs',
  },

  acrostics: {
    title: 'Acrostics',
    lede: "Poems whose lines start with the letters of the alphabet in order: verse by verse (Psalm 145, Proverbs 31, Lamentations 1), half-verse by half-verse (Psalms 111–112) or in blocks of verses (Psalm 119, Lamentations 3) — and broken ones with letters missing or out of place (Psalms 9–10). For every chapter the longest run through the alphabet is found, a skipped letter costing one, and compared with the same chapter's lines shuffled.",
    check: (recall: number) => `Check: ${Math.round(recall * 100)}% of the acrostics scholars list are found with q ≤ 0.05.`,
    qTitle: 'Benjamini–Hochberg q over all chapters: the share of chance chains expected among chains this strong',
    empty: 'No chapters match these filters.',
    letters: (n: number, missing: number) => `${n} letters${missing > 0 ? `, ${missing} skipped` : ''}`,
    peAyin: ' · פ before ע',
    chain: (n: number, first: string, last: string, missing: number) =>
      `${n} letters in order from ${first} to ${last}, ${missing} skipped`,
    skipped: 'skipped',
  },

  poetry: {
    title: 'Parallel halves',
    unitsView: 'Parallel verses',
    pairsView: 'Word pairs',
    lede: "The accents divide every verse at its main pause (etnahta; oleh-ve-yored in Psalms, Proverbs and Job). In poetry the two halves restate each other: similar meaning, other words, the same grammar, balanced length. A model trained only on how the halves relate — Psalms, Proverbs and Job against narrative and law — scores every verse; the share of parallel verses shows poetry wherever it is, including poems embedded in prose.",
    heldOut: (aucs: string) => `Held-out accuracy (AUC on a poetic book the model did not see): ${aucs}`,
    includePoetic: 'Include Psalms, Proverbs, Job',
    includePoeticTitle: 'Psalms, Proverbs and Job: the books the model learned from',
    empty: 'No units match these filters.',
    ranked: (n: number, plural: string) => `${numEn(n)} ${plural}, most parallel first`,
    rankedAnti: (n: number, plural: string, min: number) =>
      `${numEn(n)} ${plural} with at least ${min} parallel verses, most antithetic first`,
    parallelVerses: 'Parallel verses',
    parallelTitle: 'Verses whose halves score as parallel',
    mean: 'Mean',
    meanTitle: "Mean probability over the unit's verses",
    verses: 'Verses',
    byBook: 'By book',
    perBook: 'Parallel verses per book',
    perBookLede: "Share of each book's verses with parallel halves; green = the poetic-accent books.",
    sortBy: 'Sort by',
    sorts: { prob: 'Most parallel', antithetic: 'Most antithetic' } as Record<'prob' | 'antithetic', string>,
    antithetic: 'Antithetic',
    antitheticTitle: 'Share of the parallel verses whose halves set antonyms against each other (SDBH)',
    typing: (anti: number, syn: number, check: string, rest: string, shuffled: string, pairs: string) =>
      `Typing: ${numEn(anti)} parallel verses set antonyms against each other across their halves (antithetic), ${numEn(syn)} pair synonyms or words of one semantic domain (synonymous). Proverbs 10–15 are ${check} antithetic against ${rest} elsewhere; antonym pairs cross ${pairs} of the lines against ${shuffled} when the halves are shuffled between lines.`,
    relations: { antithetic: 'antithetic', synonymous: 'synonymous' } as Record<'antithetic' | 'synonymous', string>,
    pairKinds: { antonym: 'antonyms', synonym: 'synonyms', domain: 'same domain' } as Record<'antonym' | 'synonym' | 'domain', string>,
  },

  wordPairs: {
    lede: 'Hebrew poets answer a word in the first half of a line with a fixed partner in the second: ארץ // תבל, יעקב // ישראל, צדיק // רשע. Counted over every line whose halves score as parallel (and pairs of verses that form one line), these are the lemma pairs found together across the halves far more often than their frequencies predict, in at least three chapters.',
    empty: 'No word pairs.',
    first: 'First half',
    second: 'Second half',
    lines: 'Lines',
    linesTitle: 'Parallel lines with the pair / expected by chance',
    reversed: 'Reversed',
    reversedTitle: 'The pair in the other order',
    examples: 'Examples',
  },

  wordplay: {
    title: 'Wordplay',
    pattern: 'Sound pattern',
    pairsView: 'Sound-alike words',
    alliteration: 'Alliteration',
    rhyme: 'Rhyme',
    kinds: {
      substitution: 'One letter changed',
      metathesis: 'Letters swapped',
      extension: 'One letter added',
    } satisfies Record<WordplayPair['kind'], string>,
    lede: 'Different words that sound alike, a few words apart: one consonant changed, two swapped or one added, with the same vowels — as in Isaiah 5:7, מִשְׁפָּט / מִשְׂפָּח and צְדָקָה / צְעָקָה. Rare words first: that is what makes the echo audible.',
    chance: (total: number, expected: number, more: number) =>
      `${numEn(total)} pairs; shuffling the word order within each chapter yields about ${numEn(expected)}, so roughly ${numEn(more)} are more than chance — read the list as candidates, not proofs.`,
    empty: 'No wordplay matches these filters.',
  },

  sound: {
    alliterationLede: 'Within one colon, content words that begin with the same sound (after their prefixes; ב / כ / פ count as one sound with or without dagesh): פַּחַד וָפַחַת וָפָח (Isa 24:17), סִירִים סְבֻכִים (Nah 1:10). Chance is measured per word shape, since grammar fixes many first letters (every wayyiqtol starts with י).',
    alliterationNote: 'No single colon stands out once all 45,000 are tested together, so this is a ranking of candidates (p per colon), not a list of findings.',
    empty: 'Nothing here.',
    ofWords: (n: number, p: string) => `of ${n} content words · p = ${p}`,
    rhymeLede: 'Three or more lines in a row ending alike, with different words: Job 10:8–11 (‑נִי, “me”), Psalm 104:29–30 (‑וּן). Biblical rhyme is mostly the rhyme of suffixes; each run is compared with how common its ending is at line ends.',
    rhymeEmpty: 'No rhymes for these filters.',
  },
}

register('pat', patEn)
