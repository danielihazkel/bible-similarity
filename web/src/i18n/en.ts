// The interface's English messages: the source catalog (DESIGN.md §11.1). `he.ts` must match its
// shape (checked by tsc). Static text is a string; text with values is a function, which formats
// its own numbers and plurals. Scripture is never translated: these are interface strings only.

import type { ovEn } from './pages/overview'
import type { parEn } from './pages/parallels'
import type { patEn } from './pages/patterns'
import type { domEn } from './pages/domains'
import type { senEn } from './pages/senses'
import type { datEn } from './pages/dating'
import type { labEn } from './pages/labels'
import type { synEn } from './pages/syntax'
import type { borEn } from './pages/borrowing'
import type { dosEn } from './pages/dossier'
import type { divEn } from './pages/divisions'
import type { kqEn } from './pages/ketiv'
import type { citEn } from './pages/citations'
import type { mirEn } from './pages/mirrors'
import type { metEn } from './pages/meter'
import type { rootEn } from './pages/roots'
import type { readerEn } from './pages/reader'
import type { pentEn } from './pages/pentateuch'
import type { dlgEn } from './pages/dialogue'
import type { fmEn } from './pages/forms'
import type { gmEn } from './pages/gematria'
import type { elsEn } from './pages/els'
import type { glEn } from './pages/gematriaLinks'
import type { cphEn } from './pages/ciphers'
import type { msrEn } from './pages/masorah'
import type { paEn } from './pages/placeArc'
import type { plkEn } from './pages/placeLinks'
import type { plsEn } from './pages/placeLists'
import type { geoEn, plEn } from './pages/places'
import type { gtEn } from './pages/genealogy'
import type { qryEn } from './pages/query'
import type { dvEn } from './pages/divine'
import type { etyEn } from './pages/etiologies'
import type { brkEn } from './pages/brackets'
import type { rtEn } from './pages/retold'
import type { hfEn } from './pages/haftarot'
import type { rcEn } from './pages/reception'
import type { sfEn } from './pages/sourceFind'
import type { prcEn } from './pages/precision'
import type { nbhEn } from './pages/neighbourhood'
import type { theoEn } from './pages/theophoric'
import type { mlEn } from './pages/mainline'
import type { prophEn } from './pages/prophetic'
import type { lawsEn } from './pages/laws'
import type { wtEn } from './pages/witnesses'
import type { chEn } from './pages/chronology'
import type { smEn } from './pages/sums'
import type { vcEn } from './pages/vocabulary'
import type { glossEn } from './pages/glossary'
import type { trEn } from './pages/tours'
import type { wkEn } from './pages/week'
import type { fwEn } from './pages/frameworks'
import type { bnEn } from './pages/binomials'
import type { wbEn } from './pages/workbench'
import type { nbEn } from './pages/notebook'
import type { psaEn } from './pages/psalms'
import type { refEn } from './pages/refrains'
import type { echoEn } from './pages/echoes'
import type { findEn } from './pages/findings'
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

const core = {
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
    display: 'Display',
    displayTitle: 'Text display, language, theme and a link to this view',
    theme: 'Theme',
    themes: { auto: 'Auto', light: 'Light', dark: 'Dark' },
    themeAuto: 'Light or dark as your system is set',
    pinned: 'Pinned',
    pin: (page: string) => `Pin ${page}`,
    pinTitle: 'Pin this page: it stays one click away in the Pinned menu',
    unpinTitle: 'Pinned. Click to take it out of the Pinned menu',
    allPages: 'All pages',
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

  // headings of a big menu's pages (Patterns), in the menu and the index of every page
  navSections: {
    poetryForm: 'Poetry and form',
    wordsNames: 'Words and names',
    lettersNumbers: 'Letters and numbers',
    narrative: 'Narrative',
  },

  nav: {
    browse: 'Browse',
    findings: 'Findings',
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
    synopses: { label: 'Synopses', hint: 'Three or more parallel passages side by side, verse by verse' },
    changes: { label: 'Changes', hint: 'How parallel passages differ' },
    typescenes: { label: 'Action sequences', hint: 'The same actions in the same order' },
    citations: { label: 'Citations', hint: '"As it is written", "according to the word of the LORD": resolved' },
    sourceFind: { label: 'Source finder', hint: 'Paste a Hebrew text: the phrases it takes from the Bible, each with its verse' },
    structure: { label: 'Structure', hint: 'Inclusio, chiasm, Leitworte' },
    acrostics: { label: 'Acrostics', hint: 'Lines through the alphabet' },
    divisions: { label: 'Divisions', hint: 'Do paragraphs and chapters fall where the text turns?' },
    ketiv: { label: 'Written and read', hint: 'Ketiv and qere: what is written against what is read' },
    roots: { label: 'Roots', hint: 'Words of one root side by side; key roots of a chapter' },
    refrains: { label: 'Refrains', hint: 'Phrases that come back inside a passage' },
    notebook: 'Notebook',
    query: { label: 'Pattern search', hint: 'Find a construction: lemma, root, form and syntax, word by word' },
    workbench: { label: 'Workbench', hint: 'Contrast two sets of verses; check a pattern of your own' },
    forms: { label: 'Numbers and lists', hint: 'Three, and four: graded numerical sayings; genealogies and other lists' },
    gematria: { label: 'Gematria', hint: 'Letter values: what adds up to what' },
    gematriaLinks: { label: 'Equal values, related words?', hint: 'Do words of equal gematria mean alike? Genesis 1:1’s numbers' },
    divine: { label: 'Names of God', hint: 'יהוה and אלהים chapter by chapter: where the mix changes, the Elohistic Psalter' },
    etiologies: { label: 'Naming etiologies', hint: 'Names given in the text, and the word of the verse that sounds like the name' },
    brackets: { label: 'Resumptive repetition', hint: 'A clause said again after a block: does the block interrupt its story?' },
    retold: { label: 'Retold speech', hint: 'What changes when something said is told again, by another speaker or as done' },
    mainline: { label: 'Main line', hint: 'The wayyiqtol chain of a story, and where it pauses for background' },
    haftarot: { label: 'Haftarot', hint: 'Each parasha’s reading from the Prophets: where the systems rank it among all the chapters' },
    reception: { label: 'Rabbinic reception', hint: 'Where the Mishnah and the Talmuds cite the Bible: the books, chapters and verses read most' },
    witnesses: { label: 'Other witnesses', hint: 'The Samaritan Pentateuch and the Dead Sea Scrolls against the Masoretic text, word by word' },
    binomials: { label: 'Word pairs', hint: 'Pairs joined by \u2068ו\u2069 in a set order (\u2068שמים וארץ\u2069): the shorter first, the late books’ turns' },
    frameworks: { label: 'Narrative frameworks', hint: 'The judges’ cycle slot by slot, and every king’s verdict and regnal formula' },
    chronology: { label: 'Chronology', hint: 'The years from Adam as the verses count them, and the two kingdoms’ reigns against their synchronisms' },
    week: { label: 'This week’s parasha', hint: 'The coming Shabbat’s Torah portion, its haftarah and what the analyses found in it' },
    tours: { label: 'Guided tours', hint: 'Four short walks through the strongest findings, a sentence on each page' },
    glossary: { label: 'Glossary', hint: 'The statistics and search terms the pages use (p, q, G², nDCG …), each in a few words' },
    vocabulary: { label: 'Vocabulary', hint: 'New words book by book against Heaps’ law, words found once, each word’s first use' },
    sums: { label: 'Do the sums add up?', hint: 'Lists against the totals the text states (Num 1, Ezra 2), and the numbers of parallel passages' },
    els: { label: 'Letters at equal skips', hint: 'Names at equal skips in the Torah, counted against shuffles: no codes' },
    ciphers: { label: 'Atbash and albam', hint: 'Names hidden by a letter swap: Babel written ששך' },
    masorah: { label: 'The Masorah’s counts', hint: 'The middle letter, word and verse of the Torah, and each book’s verses, counted on this text' },
    psalms: { label: 'Psalms', hint: 'Gunkel\'s genres from the counted form; where the laments turn' },
    laws: { label: 'Law codes', hint: 'The Covenant, Holiness and Deuteronomic codes: each law’s form, the laws given again, side by side' },
    prophetic: { label: 'Prophetic forms', hint: 'The messenger formula, woe sayings, oracles against the nations, the lawsuit, the call' },
    poetry: { label: 'Poetry', hint: 'Parallel verse halves' },
    wordplay: { label: 'Wordplay', hint: 'Sound-alike words' },
    names: { label: 'Names', hint: 'People and places' },
    domains: { label: 'Domains', hint: 'Words by meaning: semantic fields' },
    map: { label: 'Map', hint: 'Units by meaning, book affinity' },
    places: { label: 'Places on the map', hint: 'Where the places the text names lie' },
    placeLists: { label: 'Place lists on the ground', hint: 'Are itineraries, borders and town lists ordered on the map?' },
    placeArc: { label: 'The geographic arc', hint: 'Where each chapter takes place, and how the story moves' },
    placeLinks: { label: 'Named together, near together?', hint: 'Do places the text names together lie together?' },
    genealogy: { label: 'Family tree', hint: 'Everyone the text names, parent by parent, with the verses that say so' },
    network: { label: 'Network', hint: 'Echo communities, most echoed passages, who echoes whom' },
    style: { label: 'Style', hint: 'Stylometry and style shifts' },
    shifts: { label: 'Shifts', hint: 'Words used differently across the canon' },
    language: { label: 'Language', hint: 'Late Biblical Hebrew profile of each chapter' },
    pentateuch: { label: "The Pentateuch's sources", hint: 'An unsupervised P / non-P split of Genesis–Numbers, against the critics\' P' },
    speech: { label: 'Who speaks', hint: 'Narration and direct speech, and the speakers' },
    eval: { label: 'Evaluation', hint: 'How well known cross-references are found' },
  } satisfies Record<string, string | { label: string; hint: string }>,

  status: {
    loading: 'Loading…',
    notFound: 'Not found:',
    unreachable: (msg: string) => `Could not reach the API (${msg}). Is \`bsim serve\` running?`,
    apiUnreachable: 'the API could not be reached',
    couldNotLoad: (what: string) => `Could not load ${what}`,
    notComputed: (stage?: string) =>
      stage
        ? `Not computed in this build: run \`bsim ${stage}\`, then \`bsim build-db\`.`
        : 'Not computed in this build.',
    staleChunk: 'This page could not be loaded: the viewer has been updated since this tab was opened.',
    crashed: (msg: string | undefined) => `Something went wrong while showing this page${msg ? `: ${msg}` : ''}.`,
    reload: 'Reload',
  },

  /** What a public read-only server leaves out (useServer, DESIGN.md §10.3). */
  server: {
    personalOff: 'This site keeps no labels or notebook: it is a read-only copy of the results.',
    encoderOff: 'Semantic and fused search are not offered on this site; lexical search is.',
  },

  /** The offline app (components/AppBanner.tsx). */
  offline: {
    notice: "You're offline: the pages and answers already opened still work; the rest waits for the connection.",
    update: 'A new version of the viewer is ready.',
    notSaved: 'This page was not opened before the connection went, so its answers are not saved here; it loads when the connection is back.',
    notSavedShort: 'not saved for offline use',
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
    // shown beside the English names on the home page (the Hebrew catalog loads only on demand)
    sectionsHe: { Torah: 'תורה', Prophets: 'נביאים', Writings: 'כתובים' } as Record<string, string>,
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
    hide: 'Hide',
    hideTitle: 'Leave units out of the list: the verse’s neighbours, its chapter or book, pairs Sefaria links',
    textModes: { teamim: 'Vowels and cantillation marks', niqqud: 'Vowels only', consonants: 'Consonants only' },
  },

  rank: {
    lex: 'Lex',
    sem: 'Sem',
    phr: 'Phr',
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
    read: 'Read',
    readTitle: 'Read it in its chapter, in the reader',
    moreVerses: (n: number) => ` … (${n} verses)`,
    markBy: 'Mark words by',
  },

  copy: {
    ref: 'Copy reference',
    refTitle: 'Copy the reference of this passage',
    text: 'Copy text',
    textTitle: 'Copy the Hebrew text as the text display shows it',
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

  jump: {
    open: 'Jump to…',
    openTitle: 'Jump to a passage, a word, a place, a person or a page (Ctrl+K)',
    label: 'Jump to a passage, a word, a place, a person or a page',
    placeholder: 'Gen 1:1 · בראשית א · שלום · 7965 · = 318 · חברון · יפתח · network',
    passage: 'Passage',
    places: 'Places on the map',
    people: 'People in the family tree',
    place: (kind: string | null, verses: string, first: string) => `${kind ? `${kind} · ` : ''}${verses} · first in ${first}`,
    words: 'Words',
    pages: 'Pages',
    search: 'Search the text',
    searchFor: (q: string) => `Search the text for “${q}”`,
    gematria: 'Gematria',
    gematriaOf: (q: string) => `Letter value: ${q}`,
    verses: (n: number) => `${n.toLocaleString('en-US')} ${n === 1 ? 'verse' : 'verses'}`,
    keys: '↑ ↓ to move · Enter to open · Esc to close',
    keysInline: '↑ ↓ to move · Enter to open · Esc to clear',
    pinned: 'Pinned pages',
    recentPassages: 'Recent passages',
    recentPages: 'Recent pages',
    books: 'Books',
    inReader: 'in the reader',
  },
  // /pages: every page by menu, with a star to pin it
  pageIndex: {
    title: 'All pages',
    lede: 'Every page of the site by menu, with what it shows. Star a page to pin it: the pinned pages are in the Pinned menu of the top bar and at the top of the jump box (Ctrl+K).',
    filter: 'Filter',
    filterPlaceholder: 'A name, or a word of the description',
    count: (n: number) => `${n} pages`,
    matching: (n: number, of: number) => `${n} of ${of} pages`,
    none: (q: string) => `No page matches “${q}”.`,
    clear: 'Show all',
    top: 'In the top bar',
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
    suggestions: (label: string) => `${label}: passages and books that match`,
    bookTag: 'book',
  },

  filter: {
    onlyTouching: 'Only those touching',
    showAll: 'Show all',
  },

  csv: { page: 'Export page (CSV)', all: 'Export all (CSV)', table: 'Export table (CSV)', region: 'Table' },
  // print and save (§11.1): a page to paper or PDF, a drawing as an SVG file
  out: {
    print: 'Print',
    printTitle: 'Print this page, or save it as a PDF from the print dialog',
    svg: 'Save as SVG',
    mapTitle: 'Save the map as drawn, as an SVG file to print or edit',
  },

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
    findings: 'What the analyses found: the claims each one tested, and which of them hold',
    allPages: 'All pages: every view of the text, by menu',
    resume: 'Continue',
    booksTitle: 'The books',
    notebookAll: 'The whole notebook',
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
    onThisPage: 'On this page',
    sectionText: 'Text',
    showInText: 'Show in the text:',
    reset: 'Reset',
    resetTitle: 'Back to the list as it opens: fused, the top 10, the usual filters',
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
    meaning: 'Linked in meaning',
    alignLinks: 'Words linked',
    aligning: 'Linking the words…',
    alignNone: (min: number) => `No two words are each other’s best match at cosine ${min} or more.`,
    alignLoading: 'The encoder is still loading; try again in a moment.',
    alignFailed: 'The words could not be linked.',
    alignTitle: (cos: number, same: boolean) => `cosine ${cos.toFixed(3)}${same ? ', the same word' : ', a link of meaning'}`,
    alignNote: 'Each word the other’s best match in the encoder’s reading of the two verses; blue: a link of meaning between different words, yellow: the same word.',
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
}

/** The page groups (`pages/*.ts`): each registers itself in `en` when its module is first
 * imported (`register`), so its strings load with the pages that read them (DESIGN.md §11.1,
 * M145). `catalog.test.ts` checks that a module reading `m.<group>` imports the group's file. */
export interface Groups {
  par: typeof parEn
  pat: typeof patEn
  dom: typeof domEn
  sen: typeof senEn
  dat: typeof datEn
  lab: typeof labEn
  syn: typeof synEn
  bor: typeof borEn
  dos: typeof dosEn
  div: typeof divEn
  kq: typeof kqEn
  cit: typeof citEn
  mir: typeof mirEn
  met: typeof metEn
  root: typeof rootEn
  reader: typeof readerEn
  ref: typeof refEn
  psa: typeof psaEn
  pent: typeof pentEn
  dlg: typeof dlgEn
  fm: typeof fmEn
  gm: typeof gmEn
  gl: typeof glEn
  els: typeof elsEn
  cph: typeof cphEn
  msr: typeof msrEn
  pl: typeof plEn
  geo: typeof geoEn
  pls: typeof plsEn
  pa: typeof paEn
  plk: typeof plkEn
  gt: typeof gtEn
  qry: typeof qryEn
  dv: typeof dvEn
  ety: typeof etyEn
  brk: typeof brkEn
  rt: typeof rtEn
  hf: typeof hfEn
  ch: typeof chEn
  fw: typeof fwEn
  bn: typeof bnEn
  sm: typeof smEn
  vc: typeof vcEn
  rc: typeof rcEn
  sf: typeof sfEn
  prc: typeof prcEn
  nbh: typeof nbhEn
  theo: typeof theoEn
  ml: typeof mlEn
  proph: typeof prophEn
  laws: typeof lawsEn
  wt: typeof wtEn
  gloss: typeof glossEn
  tr: typeof trEn
  wk: typeof wkEn
  wb: typeof wbEn
  nb: typeof nbEn
  echo: typeof echoEn
  find: typeof findEn
  ov: typeof ovEn
}

export type Messages = typeof core & Groups

/** The English messages: the core at once, each group once a module that reads it is loaded. */
export const en = core as Messages

/** Called by each group's module with its English strings. */
export function register<K extends keyof Groups>(key: K, value: Groups[K]): void {
  ;(en as Groups)[key] = value
}
