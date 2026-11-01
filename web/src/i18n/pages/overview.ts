// Interface strings of the Overview pages (map, network, style, evaluation) and Names: English
// first, Hebrew typed against it (see ../en.ts).

import type { EntityKind, NameKind, PlaceKind } from '../../api/types'
import { countEn, countHe, numEn } from '../fmt'

const typeEn: Record<string, string> = { verse: 'Verse', chapter: 'Chapter', pericope: 'Pericope', parasha: 'Parasha' }
export const pluralHe: Record<string, string> = { verse: 'פסוקים', chapter: 'פרקים', pericope: 'פיסקאות', parasha: 'פרשות' }
const pluralEn: Record<string, string> = { verse: 'verses', chapter: 'chapters', pericope: 'pericopes', parasha: 'parashot' }
/** Hebrew plural nouns of these unit types are feminine (פיסקאות, פרשות). */
export const feminine = (type: string) => type === 'pericope' || type === 'parasha'
export const versesHe = (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')

const goldEn: Record<string, string> = { sefaria: 'Sefaria', openbible: 'OpenBible', etcbc: 'ETCBC' }
export const goldHe: Record<string, string> = { sefaria: 'ספריא', openbible: 'OpenBible', etcbc: 'ETCBC' }

export const ovEn = {
  chart: {
    scatterKeys: (label: string) => `${label}. Use the arrow keys to step through points and Enter to open one.`,
    heatmapKeys: (label: string) => `${label}. Use the arrow keys to move between cells and Enter to select one.`,
  },

  map: {
    title: 'Map of the Tanakh',
    lede: (type: string) =>
      `Every ${(typeEn[type] ?? type).toLowerCase()} placed by meaning (t-SNE of the semantic embeddings): nearby points read alike. Colours are thematic clusters, labelled by the lemmas they use most.`,
    colourBy: 'Colour by',
    clusters: 'Clusters',
    sections: 'Torah / Prophets / Writings',
    lists: 'Lists',
    listsLegend: 'Share of the verses in a list (genealogies, itineraries, rolls of names): darker = more.',
    listShare: (n: number, of: number) => `· ${countEn(n, 'verse', 'verses')} of ${of} in a list`,
    scatter: 'Map of units by meaning',
    point: (n: number) => `· ${countEn(n, 'verse', 'verses')} · click to open`,
    idle: 'Hover a point; click to open the unit.',
    affinity: 'How the books talk to each other',
    affinityLede:
      "Cross-book verse pairs in each other's fused top 10, relative to what the books' sizes would predict (lift; darker = more). Click a cell for its strongest pairs.",
    bookOrder: 'Book order',
    related: 'Related books together',
    canon: 'Canon order',
    cell: (a: string, b: string, n: number, lift: string) => `${a} ↔ ${b}: ${n} pairs, lift ${lift}`,
    heatmap: 'Book by book affinity',
    examples: 'Book pair examples',
    strongest: (a: string, b: string) => `${a} ↔ ${b}: strongest pairs`,
    noPairs: 'No pairs.',
  },

  network: {
    title: 'Network of echoes',
    ledeLinked: (type: string) =>
      `Every ${(typeEn[type] ?? type).toLowerCase()} is linked to those in its top ten (lexical and semantic, fused), consecutive ones of the same book left out. `,
    communities: 'Communities',
    ledeCommunities: ' are groups that echo each other more than the rest — often across books; ',
    central: 'central',
    ledeCentral: ' passages (PageRank) are the ones the rest of the Bible echoes most.',
    nCommunities: (n: number) => `${n} communities`,
    graph: 'Community graph',
    mostEchoedLabel: 'Most echoed passages',
    mostEchoed: (type: string) => `Most echoed ${pluralEn[type] ?? `${type}s`}`,
    moreBooks: (n: number) => ` +${n} books`,
    communityOf: (n: number, type: string) => `Community of ${n} ${pluralEn[type] ?? `${type}s`}`,
    legend:
      'Circle size: centrality · colour: Torah / Prophets / Writings · lines: echoes (darker = stronger). Select a passage to open it.',
    graphLabel: 'Passages and their echoes',
    node: (label: string, partners: number) => `${label}, ${partners} echoes`,
    nodeTitle: (label: string, partners: number, cross: number) =>
      `${label} · ${partners} echoes · ${Math.round(cross * 100)}% to other books`,
    allPassages: (n: number) => `All ${n} passages, most central first`,
    passage: 'Passage',
    echoes: 'Echoes',
    otherBooks: 'Other books',
    otherBooksTitle: 'Share of the echo weight that reaches other books',
    community: 'Community',
  },

  style: {
    title: 'Style',
    lede: 'How the books write, not what they say: rates of the 100 most frequent lemmas and of grammatical forms (wayyiqtol, participles, the article, suffixes …), compared across books and chapters. These are descriptive statistics; groupings are not claims about authorship or date.',
    book: 'Book',
    highlight: '— highlight a book —',
    axis: (pc: number) => `${pc === 1 ? 'Horizontal' : 'Vertical'} axis`,
    variance: (v: number) => `(${Math.round(v * 100)} % of the variance)`,
    positive: (pc: number): string => (pc === 1 ? 'right' : 'up'),
    negative: (pc: number): string => (pc === 1 ? 'left' : 'down'),
    distance: 'Stylistic distance between books',
    distanceLede:
      "Burrows' Delta (mean difference of feature z-scores); darker = more alike. Books are ordered so similar styles sit together.",
    delta: (a: string, b: string, d: string) => `${a} ↔ ${b}: Delta ${d}`,
    profile: 'Book style profile',
    words: (n: number) => `(${numEn(n)} words)`,
    more: 'Uses more than other books',
    less: 'Uses less',
    closest: 'Closest in style:',
    feature: (f: string, rate: string, z: string) => `${f}: ${rate} per 100 words, z ${z}`,
    scatter: 'Chapters by style',
    point: (n: number) => ` · ${n} words`,
    idle: 'Each point is a chapter (≥ 150 words). Hover for its name; click to open it.',
  },

  seams: {
    label: 'Style shifts',
    title: 'Where the style changes',
    lede: (words: number) =>
      `At every verse boundary the ${words} words before and after are compared (Burrows' Delta of the same features). Peaks above the dashed line — the highest a book with shuffled verse order reaches 19 times in 20 — are seams: a new genre, language, speaker or source. Descriptive, not a claim about authorship.`,
    none: (inBook: boolean) => `No significant seams${inBook ? ' in this book' : ''}.`,
    shift: (shift: string, threshold: string) => `shift ${shift} (threshold ${threshold})`,
    chart: 'Style shift along the book',
  },

  eval: {
    title: 'Evaluation',
    lede: "How often each system ranks a known cross-reference near the top. The gold pairs are Sefaria's links between verses or passages of the Tanakh, split by book so that no tested book was seen in training. Known links are a biased sample (famous parallels are over-represented), so low scores also mean many hits are simply unlinked. Rows marked ",
    served: 'served',
    ledeEnd: ' are the systems this viewer shows.',
    none: 'No evaluation has been run yet (`bsim eval`).',
    splitLabel: (name: string) => `${name} split`,
    splits: {
      dev: 'Development books (used to choose models and weights)',
      test: 'Test books (evaluated once, after every choice was made)',
    } as Record<string, string>,
    evaluated: (date: string) => `Evaluated ${date}`,
    caption: (type: string, gold?: { queries: number; pairs: number }) =>
      `${typeEn[type] ?? type}s${gold ? ` · ${gold.queries} queries, ${gold.pairs} gold pairs` : ''}`,
    openbible: (split: string) => `A second opinion: OpenBible cross-references (${split} books)`,
    openbibleLede: 'Crowd-voted cross-references (at least 5 votes), compared with the Sefaria gold on the same queries.',
    openbibleShare: (pct: string) => ` Only ${pct}% of OpenBible pairs are also Sefaria links.`,
    againstOpenbible: 'Against OpenBible',
    againstSefaria: 'Against Sefaria (same books)',
    etcbc: (split: string) => `A third opinion: ETCBC's parallel passages (${split} books)`,
    etcbcLede: (parallels: number, formulas: number, max: number) =>
      `Verse pairs whose text is nearly the same (ETCBC parallels notebook, similarity ≥ 75 %): ${numEn(parallels)} parallels. The ${numEn(formulas)} pairs among verses with more than ${numEn(max)} partners are formulas and list items (וידבר יהוה אל משה לאמר has 157) and are left out.`,
    etcbcShare: (sef: string, ob: string) => ` ${sef}% of them are also Sefaria links and ${ob}% OpenBible references: the commentary rarely links a verse to its near-copy.`,
    againstEtcbc: 'Against ETCBC',
    etcbcBands: (bands: string) => `Fused recall@10 by similarity: ${bands}.`,
    etcbcCoverage: (fused: string, phrase: string, seq: string, prec: string, nSeq: number) =>
      `All parallels (every split): ${fused}% are in the fused top 10, ${phrase}% share a phrase, ${seq}% lie in a strong sequence; ${prec}% of the ${numEn(nSeq)} verse pairs of the strong sequences are ETCBC parallels (the rest are reworded).`,
    // the encoder retrained with more supervision (§16.41)
    supLabel: 'More supervision',
    sup: (split: string) => `More supervision: the semantic model retrained with other golds' pairs (${split} books)`,
    supLede: (metric: string, noise: string) =>
      `The semantic model learns from Sefaria's links between training books, which lean towards the famous ones. Each variant retrains it the same way with more pairs between training books (OpenBible's cross-references, ETCBC's parallels), or with only another seed (${noise}) to show what a retrain alone moves. The cells give the gain in ${metric} over the model the experiment started from (Sefaria's pairs only), with a 95% bootstrap interval over the development queries; the development and test books are never trained on. The rule was fixed before any training: a variant is adopted only if the fused list gains on OpenBible, with the interval above 0 and the gain larger than the retrain alone moves, and loses nothing significant on Sefaria or ETCBC. `,
    supChosen: (name: string) => `Passed: ${name}, now the semantic model in use.`,
    supNone: 'No variant passed, so the model in use stays.',
    supList: { fused: 'Fused list (lexical + semantic)', semantic: 'Semantic list alone' } as Record<string, string>,
    supCaption: (list: string, base: string, scores: string) => `${list} · gain over ${base} (${scores})`,
    supVariant: 'Variant',
    supRows: 'Training pairs (rows)',
    supAdopt: 'Passes the rule',
    supSource: (source: string, n: number) => `${goldEn[source] ?? source} ${numEn(n)}`,
    supCounts: (better: number, worse: number, queries: number) =>
      `${numEn(better)} queries better, ${numEn(worse)} worse, of ${numEn(queries)}`,
    supYes: 'yes',
    supNo: 'no',
    // newer encoders against the model in use (§16.48)
    encLabel: 'Newer encoders',
    enc: (split: string) => `Newer encoders against the model in use (${split} books)`,
    encLede: (metric: string, bar: string) =>
      `The semantic model is BEREL, a BERT trained on rabbinic Hebrew, fine-tuned on the cross-references. Two kinds of candidate: DictaBERT (modern Hebrew, base and large) fine-tuned the same way, with the same pairs and seed; and multilingual embedders used as they are, never trained here. The cells give the gain in ${metric} over the model in use, with a 95% bootstrap interval over the development queries. The rule was fixed before any candidate ran: a candidate is adopted only if the fused list gains on Sefaria with the interval above 0 and the gain larger than ${bar} (the most a retrain with another seed moved), and loses nothing significant on OpenBible or ETCBC. `,
    encChosen: (name: string) => `Passed: ${name}.`,
    encNone: 'No candidate passed, so BEREL stays.',
    encList: { fused: 'Newer encoders: fused list', semantic: 'Newer encoders: semantic list alone' } as Record<string, string>,
    encCandidate: 'Candidate',
    encModel: 'Model',
    encKind: { trained: 'fine-tuned here', zero_shot: 'used as it is' } as Record<string, string>,
    encZero: (ref: string, scores: string) => `Zero-shot: the multilingual embedders against ${ref}, the zero-shot system already built (semantic list; ${ref} ${scores})`,
    encZeroLabel: 'Zero-shot embedders against the one already built',
    // a third fusion list for chapters and pericopes (§16.50)
    unitLabel: 'A third list for chapters and pericopes',
    unit: (split: string) => `A third list for chapters and pericopes (${split} books)`,
    unitLede: (metric: string) =>
      `Chapters and pericopes are found by fusing a word list (TF-IDF) with the semantic list. Three candidates for a third list, each built from what the verses of two passages share: the parallel sequences that run through them, the phrases they share, and each verse's own top ten (fused). Each is added at three weights; the weight is chosen on one half of the development queries and scored on the other (cross-fitted), and the gain in ${metric} over the fused list is given with a 95% bootstrap interval. The rule was fixed before the first run: a list is adopted for a unit type only if its cross-fitted gain on Sefaria has the interval above 0 and it loses nothing significant on OpenBible or ETCBC.`,
    unitVerdict: (type: string, family: string | null) =>
      family ? `${pluralEn[type] ?? type}: the ${family} list passed the rule and is now fused.` : `${pluralEn[type] ?? type}: no list passed.`,
    unitCaption: (type: string, scores: string) => `${typeEn[type] ?? type}s · gain over the fused list (${scores})`,
    unitAloneCaption: (type: string) => `${typeEn[type] ?? type}s · each list alone, not fused`,
    unitFamily: 'Third list',
    unitSelected: 'Best on Sefaria',
    unitCrossFitted: 'Cross-fitted (Sefaria)',
    unitList: 'List',
    unitUnits: 'Passages with a list',
    unitFamilies: { sequences: 'parallel sequences', phrases: 'shared phrases', hits: 'verse hits' } as Record<string, string>,
    gold: goldEn,
    system: 'System',
    servedAs: (modes: string) => `served: ${modes}`,
  },

  names: {
    title: 'People and places',
    lede: 'Every name in the text. Whether a name is a person or a place comes from Strong\'s lexicon where it says, and is otherwise guessed from its contexts (directional ־ה, "city of", "son of", "and X said"); tribes and peoples count as people. Two names are linked when they share verses more often than their frequencies predict.',
    kindSource: { lexicon: "from Strong's lexicon", cues: 'guessed from context' } as Record<'lexicon' | 'cues', string>,
    kind: 'Kind',
    all: 'All',
    kinds: { person: 'Person', place: 'Place', mixed: 'Person / place', unclear: 'Unclear' } satisfies Record<EntityKind, string>,
    book: 'Book',
    allBooks: 'All books',
    find: 'Find a name',
    list: 'Names',
    noMatch: 'No names match.',
    count: (total: number, inBook: boolean, page: number, pages: number) =>
      `${numEn(total)} names${inBook ? ' in this book' : ''} · page ${page} of ${pages}`,
    details: 'Name details',
    mentions: (n: number, verses: number) => `${n} mentions in ${verses} verses · first `,
    last: ', last ',
    allVerses: 'all verses',
    where: 'Where',
    perBook: 'Verses per book',
    bookCount: (book: string, n: number) => `${book}: ${n} verses`,
    appearsWith: 'Appears with',
    together: (n: number, chance: string) => `${n} verses together (${chance} by chance)`,
    ego: (name: string) => `Names appearing with ${name}`,
    show: (name: string) => `${name}: show this name`,
    nameKinds: { person: 'a person', people: 'a people', location: 'a place', landform: 'a landform', water: 'water' } satisfies Record<NameKind, string>,
    sdbhKind: (kind: string) => `In SDBH’s domains, mostly ${kind}.`,
    sites: 'On the ground',
    sitesLede: 'Where the places this name stands for lie: each mention matched to a place by STEPBible’s TIPNR, located by OpenBible.info’s best-voted identification. One name may be several places.',
    placeKinds: { town: 'Town', region: 'Region', landform: 'Landform', water: 'Water' } satisfies Record<PlaceKind, string>,
    siteVerses: (n: number) => countEn(n, 'verse', 'verses'),
    coords: (lat: number, lon: number) => `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? 'E' : 'W'}`,
    votes: (score: number) => `identification voted ${numEn(score)} / 1,000`,
    contested: (share: number) => `a second site has ${Math.round(share * 100)}% of its votes`,
    tipnrPoint: 'TIPNR’s point, not voted on',
    unlocated: 'not located',
  },
}
