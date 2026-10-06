// The interface's English messages: the source catalog (DESIGN.md §11.1). `he.ts` must match its
// shape (checked by tsc). Static text is a string; text with values is a function, which formats
// its own numbers and plurals. Scripture is never translated: these are interface strings only.

import { ovEn } from './pages/overview'
import { parEn } from './pages/parallels'
import { patEn } from './pages/patterns'
import { domEn } from './pages/domains'
import { senEn } from './pages/senses'
import { datEn } from './pages/dating'
import { labEn } from './pages/labels'
import { synEn } from './pages/syntax'
import { borEn } from './pages/borrowing'
import type { DiffOp, Exclude, Mode, WordplayPair } from '../api/types'

const num = (n: number) => n.toLocaleString('en-US')
const s = (n: number, one: string, other: string) => (n === 1 ? one : other)
const ordinal = (n: number) => {
  const suffix =
    n % 100 >= 11 && n % 100 <= 13 ? 'th' : (({ 1: 'st', 2: 'nd', 3: 'rd' }) as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${suffix}`
}

const unitTypes: Record<string, string> = { verse: 'Verse', chapter: 'Chapter', pericope: 'Pericope', parasha: 'Parasha' }
const unitTypesPlural: Record<string, string> = { verse: 'verses', chapter: 'chapters', pericope: 'pericopes', parasha: 'parashot' }

export const en = {
  locale: 'en',
  /** A number with grouping, as this language writes it. */
  num,
  /** A share 0..1 as a whole percentage. */
  pct: (x: number) => `${Math.round(x * 100)}%`,

  /** chapter:verse without the book */
  cv: (c: number, v: number) => `${c}:${v}`,

  site: {
    name: 'Tanakh Similarity',
    skip: 'Skip to content',
    menu: 'Menu',
    mainNav: 'Main',
    copyLink: 'Copy link',
    copied: 'Copied',
    copyLinkTitle: 'Copy a link to this view',
    textDisplay: 'Text display',
    language: 'Interface language',
    footer: {
      display: 'Display text: Sefaria,',
      mam: 'Miqra according to the Masorah',
      lemmas: 'Lemmas and morphology:',
      wlc: '(WLC public domain, morphology CC BY 4.0). Cross-references: Sefaria; OpenBible.info (CC-BY) for evaluation. For personal and research use.',
      lexicon: 'Word senses and semantic domains: UBS Dictionary of Biblical Hebrew, SDBH (CC BY-SA 4.0); name types: OpenScriptures HebrewLexicon (CC BY 4.0).',
      syntax: 'Clauses, phrases and speech: ETCBC, BHSA (CC BY-NC 4.0).',
    },
    notFound: 'Page not found.',
    backToBooks: 'Back to the books',
  },

  nav: {
    browse: 'Browse',
    search: 'Search',
    compare: 'Compare',
    about: 'About',
    parallels: 'Parallels',
    patterns: 'Patterns',
    overview: 'Overview',
    discoveries: { label: 'Discoveries', hint: 'Strong pairs Sefaria does not link' },
    labels: { label: 'Your labels', hint: 'Pairs you judged: a third gold set' },
    borrowing: { label: 'Who borrowed', hint: 'Which side of a parallel looks later' },
    phrases: { label: 'Phrases', hint: 'Shared runs of words' },
    sequences: { label: 'Sequences', hint: 'Passages parallel verse by verse' },
    changes: { label: 'Changes', hint: 'How parallel passages differ' },
    typescenes: { label: 'Action sequences', hint: 'The same actions in the same order' },
    structure: { label: 'Structure', hint: 'Inclusio, chiasm, Leitworte' },
    acrostics: { label: 'Acrostics', hint: 'Lines through the alphabet' },
    poetry: { label: 'Poetry', hint: 'Parallel verse halves' },
    wordplay: { label: 'Wordplay', hint: 'Sound-alike words' },
    names: { label: 'Names', hint: 'People and places' },
    domains: { label: 'Domains', hint: 'Words by meaning: semantic fields' },
    map: { label: 'Map', hint: 'Units by meaning, book affinity' },
    network: { label: 'Network', hint: 'Echo communities, most echoed passages' },
    style: { label: 'Style', hint: 'Stylometry and style shifts' },
    shifts: { label: 'Shifts', hint: 'Words used differently across the canon' },
    language: { label: 'Language', hint: 'Late Biblical Hebrew profile of each chapter' },
    speech: { label: 'Who speaks', hint: 'Narration and direct speech, and the speakers' },
    eval: { label: 'Evaluation', hint: 'How well known cross-references are found' },
  } satisfies Record<string, string | { label: string; hint: string }>,

  status: {
    loading: 'Loading…',
    notFound: 'Not found:',
    unreachable: (msg: string) => `Could not reach the API (${msg}). Is \`bsim serve\` running?`,
    apiUnreachable: 'the API could not be reached',
    couldNotLoad: (what: string) => `Could not load ${what}`,
    staleChunk: 'This page could not be loaded: the viewer has been updated since this tab was opened.',
    crashed: (msg: string | undefined) => `Something went wrong while showing this page${msg ? `: ${msg}` : ''}.`,
    reload: 'Reload',
  },

  pager: {
    label: 'Pages',
    previous: '← Previous',
    next: 'Next →',
    page: 'Page',
    of: (n: number) => `of ${n}`,
    pageOf: (n: number) => `Page (of ${n})`,
    go: 'Go',
    pastEnd: (page: number, last: number) =>
      `Page ${page} is past the end of this list (${last} ${s(last, 'page', 'pages')}).`,
    lastPage: 'Go to the last page',
  },

  units: {
    type: (t: string) => unitTypes[t] ?? t,
    /** lower-case plural: "chapters", "parashot" */
    plural: (t: string) => unitTypesPlural[t] ?? `${t}s`,
    /** "Verse" / "Chapter" … as a lower-case noun inside a sentence */
    noun: (t: string) => (unitTypes[t] ?? t).toLowerCase(),
    verses: (n: number) => `${num(n)} ${s(n, 'verse', 'verses')}`,
    chapterN: (n: number) => `Chapter ${n}`,
    chaptersShort: (n: number) => `${n} ch.`,
    sections: { Torah: 'Torah', Prophets: 'Prophets', Writings: 'Writings' } as Record<string, string>,
    tabs: { chapters: 'Chapters', verses: 'Verses', parashot: 'Parashot', pericopes: 'Pericopes' },
    markers: { pe: 'פ open', samekh: 'ס closed' },
    unknownBook: 'Unknown book.',
    unitType: 'Unit type',
    similarVerses: (ref: string) => `${ref}: similar verses`,
    book: 'Book',
    books: 'Books',
    context: 'Context',
  },

  modes: {
    label: 'Similarity mode',
    names: { lexical: 'Lexical', semantic: 'Semantic', fused: 'Fused', structural: 'Structural', domain: 'Domains', syntax: 'Clauses' } satisfies Record<Mode, string>,
    hints: {
      lexical: 'Shared wording: BM25 / TF-IDF over OSHB lemmas, formulas down-weighted',
      semantic: 'Shared meaning: fine-tuned BEREL embeddings (CSLS)',
      fused: 'Both, combined by weighted reciprocal rank fusion',
      structural:
        'Same grammatical shape, any words: BM25 / TF-IDF over n-grams of word forms (part of speech, verb form, state)',
      domain:
        'Same semantic fields, any words: BM25 / TF-IDF over the SDBH domain of each word in context (Move, Weak, Waterbodies…)',
      syntax:
        'Built the same way, any words: BM25 / TF-IDF over the BHSA clauses — their types, the functions of their phrases in order, narration or speech',
    } satisfies Record<Mode, string>,
    score: (mode: string) => `${mode} score`,
    top: 'Top',
    exclude: {
      neighbors: 'Hide neighbours ±2',
      chapter: 'Hide same chapter',
      book: 'Hide same book',
      known: 'Hide Sefaria-linked',
    } satisfies Record<Exclude, string>,
    textModes: { teamim: 'Vowels and cantillation marks', niqqud: 'Vowels only', consonants: 'Consonants only' },
  },

  rank: {
    lex: 'Lex',
    sem: 'Sem',
    notInTop: (label: string, k: number) => `${label}: not in the top ${k}`,
    rank: (label: string, rank: number, score: string) => `${label}: rank ${rank}, score ${score}`,
  },

  q: (q: number) => (q < 0.001 ? 'q < 0.001' : `q = ${q < 0.01 ? q.toFixed(3) : q.toFixed(2)}`),
  granularity: { verse: 'verse by verse', colon: 'half-verse by half-verse' },

  diff: {
    marks: 'Change marks',
    ops: {
      substitution: { label: 'Substituted', hint: 'Another word (lemma) in the same place' },
      added: { label: 'Added', hint: 'Only in the later passage' },
      omitted: { label: 'Omitted', hint: 'Only in the earlier passage' },
      moved: { label: 'Moved', hint: 'Dropped in one place and added in another' },
      form: { label: 'Other form', hint: 'Same lemma, different prefix, suffix or inflection' },
      spelling: { label: 'Spelling', hint: 'Same word, written with or without ו / י (plene / defective)' },
    } satisfies Record<DiffOp, { label: string; hint: string }>,
    tooDifferent: 'Too different to mark word by word.',
    tooDifferentShare: (share: number) =>
      `Too different to mark word by word (${Math.round(share * 100)}% of the words keep their lemma).`,
    keepShare: (share: number) => `${Math.round(share * 100)}% of the words keep their lemma; A is read as the earlier passage.`,
    loadFailed: 'Could not load the changes.',
    aligning: 'Aligning words…',
  },

  hit: {
    phraseTitle: (n: number, score: string) => `Aligned shared phrase: ${n} lemmas, score ${score}`,
    phrase: (n: number) => `phrase · ${n}`,
    unpin: 'Unpin',
    changes: 'Changes',
    sharedWords: 'Shared words',
    keepChanges: 'Keep the word changes marked',
    keepShared: 'Keep the shared words highlighted',
    compare: 'Compare',
    compareTitle: 'Side-by-side comparison',
    moreVerses: (n: number) => ` … (${n} verses)`,
    markBy: 'Mark words by',
  },

  lemmas: {
    finding: 'Finding shared words…',
    none: 'No shared content lemmas.',
    shared: 'Shared lemmas',
    strongs: (lemma: string, formula: boolean) => `Strong's ${lemma}${formula ? ' (only inside a repeated formula)' : ''}`,
    allVerses: (lemma: string) => `Strong's ${lemma}: all verses`,
    strongsTag: (lemma: string) => `Strong's ${lemma}`,
  },

  word: {
    panel: 'Word analysis',
    close: 'Close',
    unaligned: 'No OSHB word is aligned to this token.',
    verses: (n: number) => `${n} verses`,
    clickHint: 'Click a word for its morphology and concordance.',
    pause: 'pause',
    ketiv: 'Ketiv (written form)',
  },

  link: {
    untyped: 'untyped',
    verseTitle: (types: string) => `Sefaria links these verses (${types})`,
    passageTitle: (types: string) => `A Sefaria passage-level link covers this pair (${types})`,
    verse: 'Sefaria link',
    passage: 'Sefaria passage',
  },

  picker: {
    lookingUp: 'Looking up…',
    notRef: (q: string) => `Not a reference: ${q}`,
    unreachable: 'Could not reach the API',
    booksFailed: 'Could not load books',
    unitsFailed: 'Could not load units',
    unitType: (label: string) => `${label} unit type`,
    book: (label: string) => `${label} book`,
    chapter: (label: string) => `${label} chapter`,
    unit: (label: string) => `${label} unit`,
    reference: (label: string) => `${label} reference`,
    bookPlaceholder: 'Book…',
    refPlaceholder: 'Gen 1:1 · בראשית א',
    go: 'Go',
  },

  filter: {
    onlyTouching: 'Only those touching',
    showAll: 'Show all',
  },

  csv: { page: 'Export page (CSV)', all: 'Export all (CSV)' },

  keypad: { label: 'Hebrew keyboard', space: 'Space', backspace: 'Backspace' },

  cards: {
    phraseScore: 'Alignment score: idf-weighted matched lemmas minus gap and mismatch penalties',
    lemmas: (n: number) => `${n} lemmas`,
    recursTitle: 'Verses sharing exactly this lemma sequence',
    recurs: (n: number) => `recurs in ${n} verses`,
    qTitle: 'Expected share of chance chains among chains at least this strong (verse order shuffled within chapters)',
    chainScore: 'Chain score: pair weights minus gap costs',
    seqVerses: (n: number, direction?: string) =>
      `${n} verses ${direction === 'reverse' ? 'in mirrored order' : direction === 'mixed' ? 'reordered' : 'in order'}`,
    goldTitle: 'Aligned verse pairs that Sefaria already links',
    notLinked: 'not linked in Sefaria',
    linksOf: (gold: number, n: number) => `Sefaria links ${gold}/${n}`,
    sideBySide: 'Side by side',
    wordplayKinds: {
      substitution: 'one letter changed',
      metathesis: 'letters swapped',
      extension: 'one letter added',
    } satisfies Record<WordplayPair['kind'], string>,
    adjacent: 'adjacent',
    apart: (gap: number) => `${gap} words apart`,
    wordplayScore: 'Mean rarity (idf) of the two words, minus distance',
  },

  books: {
    title: 'Browse',
    lede: 'Pick a book, then a chapter, parasha or pericope. Every unit lists its most similar units by shared wording, meaning, or both.',
  },

  unit: {
    halvesTitle: 'Split each verse at its main accent pauses (etnahta; oleh-ve-yored in Psalms, Proverbs, Job)',
    halves: "Verse halves (te'amim)",
    clausesTitle: 'Also split at the weaker pauses (zaqef, segolta, tipeha; revia and tsinnor in poetry)',
    clauses: 'Finer clauses',
    loadingHalves: 'Loading verse halves…',
    theHalves: 'the verse halves',
    parallelHalves: '∥ marks verses whose halves are parallel like poetry',
    shareOf: (share: number, type: string) => ` · ${Math.round(share * 100)}% of this ${(unitTypes[type] ?? type).toLowerCase()}`,
    source: 'Source text',
    names: 'Names: ',
    namesLabel: 'People and places',
    theNames: 'the names in this unit',
    nameTitle: (here: number | null, all: number) => `${here} here, ${all} in all`,
    network: (rank: number, of: number, type: string, partners: number, cross: number) =>
      `Echo network: ${ordinal(rank)} most echoed of ${of} ${unitTypesPlural[type] ?? `${type}s`} · ${partners} echoes, ${Math.round(cross * 100)}% to other books · `,
    community: (n: number) => `its community of ${n}`,
    structure: 'Structure: inclusio, chiasm, Leitworte',
    similar: 'Similar units',
    similarOf: (type: string) => `Similar ${unitTypesPlural[type] ?? `${type}s`}`,
    keys: 'Keys:',
    keysNext: 'next / previous hit',
    keysMarked: ' (its words marked)',
    noResults: 'No results left after the filters.',
    sharedPhrases: 'Shared phrases',
    theSharedPhrases: 'shared phrases',
    phrasesLede: 'Verses that share an aligned run of lemmas with this one (rare words weigh more)',
    strongestShown: (n: number) => `; the strongest ${n} are shown`,
    wordplay: 'Wordplay',
    theWordplay: 'wordplay',
    wordplayLede: 'Sound-alike words close together, rarest first.',
    allHere: (n: number) => `All ${n} here`,
    inWordplay: 'In the wordplay list',
    runs: 'Runs parallel to',
    runsLabel: 'Parallel sequences',
    theSequences: 'parallel sequences',
    runsLede: (q: number) => `Passages that follow this one verse by verse in the same order (q ≤ ${q}).`,
    inSequences: 'In the sequences list',
    acrostic: 'Acrostic',
    acrosticLetters: (n: number, first: string, last: string) => `: ${n} letters in alphabetical order, ${first}–${last}`,
    skipped: (n: number) => ` (${n} skipped)`,
    peAyin: ', פ before ע',
    markLetters: 'Mark the letters',
    allAcrostics: 'All acrostics',
    nextVerseTitle: (p: string) => `Parallel with the next verse (one bicolon over two verses): p = ${p}`,
    halvesTip: (p: string, cos: string, shared: number | null, shape: string, balance: string) =>
      `Parallel halves: p = ${p} · meaning ${cos} · shared lemmas ${shared} · grammar ${shape} · balance ${balance}`,
    previous: '← Previous',
    next: 'Next →',
  },

  search: {
    title: 'Search',
    book: 'Book',
    allBooks: 'All books',
    hint: 'Pointed or unpointed input; lexical matching strips prefixes (ו ה ב כ ל מ ש).',
    encoderFailed: (err: string) =>
      `The semantic encoder failed to load on the server (${err}); only lexical search is available.`,
    searchLexically: 'Search lexically',
    encoderLoading: (mode: string) =>
      `The semantic encoder is still loading on the server; ${mode} search will answer as soon as it is ready (lexical search works now).`,
    reference: 'Reference:',
    notRef: 'Not a reference; free-text search needs Hebrew letters.',
    waiting: 'Waiting for the semantic encoder…',
    searching: 'Searching…',
    normalized: 'Normalized:',
    terms: 'lexical terms:',
    noMatches: 'No matches.',
    placeholder: 'חיפוש בתנ״ך… או הפניה: בראשית א א / Gen 1:1',
    inputLabel: 'Hebrew search text or reference',
    submit: 'Search',
    hideKeyboard: 'Hide keyboard',
    showKeyboard: 'Hebrew keyboard',
  },

  compare: {
    title: 'Compare',
    lede: 'Every verse is paired with its most similar verse in the other unit (cosine of the semantic embeddings). Hover a verse to see its partner and their shared words.',
    swap: 'Swap A and B',
    choose: 'Choose two units, or use “Compare” on any result.',
    bmaHint: '½ (mean best cosine A→B + mean best cosine B→A)',
    lowHigh: 'low → high',
    cosine: 'cosine',
    changes: 'Changes A → B',
    unitSide: (side: string) => `Unit ${side}`,
    bestIn: (label: string) => `Best match in ${label}`,
  },

  concordance: {
    occurrences: (words: number, verses: number, books: number) =>
      `${num(words)} occurrences in ${num(verses)} verses, ${books} books.`,
    byBook: 'By book',
    allBooks: 'Show all books',
    onlyBook: 'Only this book',
    verses: 'Verses',
    versesIn: (book: string) => `Verses in ${book}`,
  },
  par: parEn,
  pat: patEn,
  dom: domEn,
  sen: senEn,
  dat: datEn,
  lab: labEn,
  syn: synEn,
  bor: borEn,
  ov: ovEn,
}

export type Messages = typeof en
