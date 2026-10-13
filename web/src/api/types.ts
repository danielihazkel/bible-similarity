// Mirrors the pydantic response models in src/bsim/api/models.py (DESIGN.md §10).

export type Mode = 'lexical' | 'semantic' | 'fused' | 'structural' | 'domain' | 'syntax'
export type SearchMode = 'lexical' | 'semantic' | 'fused'
export type UnitType = 'verse' | 'chapter' | 'pericope' | 'parasha'
export type Exclude = 'neighbors' | 'chapter' | 'book' | 'known'

export interface Book {
  book_id: number
  name: string
  he_name: string
  osis: string
  section: string
  n_chapters: number
}

export interface UnitSummary {
  unit_id: string
  unit_type: UnitType
  label_en: string
  label_he: string
  book_id: number
  start_verse_id: number
  end_verse_id: number
  n_verses: number
  marker: string | null
}

export interface Verse {
  verse_id: number
  book_id: number
  chapter: number
  verse: number
  ref: string
  /** Hebrew reference, e.g. "בראשית א:א" */
  ref_he: string
  text_display: string
  display_tokens: string[]
  ketiv_note: string | null
}

export interface UnitDetail {
  unit: UnitSummary
  verses: Verse[]
  parents: UnitSummary[]
  prev_id: string | null
  next_id: string | null
}

export interface Breakdown {
  score: number
  lex_score: number | null
  lex_rank: number | null
  sem_score: number | null
  sem_rank: number | null
}

/** A Sefaria link: `verse` = direct verse-to-verse, `unit` = only a passage-level link covers it. */
export interface GoldLink {
  level: 'verse' | 'unit'
  types: string[]
}

export interface PhraseInfo {
  score: number
  n_tokens: number
}

export interface Hit extends Breakdown {
  rank: number
  unit: UnitSummary
  verse: Verse | null
  preview: string | null
  link: GoldLink | null
  phrase: PhraseInfo | null
}

export interface PhrasePair {
  score: number
  n_tokens: number
  spread: number
  a: UnitSummary
  b: UnitSummary
  a_verse: Verse
  b_verse: Verse
  a_display: number[]
  b_display: number[]
  link: GoldLink | null
}

export interface PhrasesResponse {
  book: number | null
  cross_book: boolean
  min_tokens: number
  max_spread: number | null
  /** only phrases with a side in this unit */
  unit: string | null
  total: number
  offset: number
  limit: number
  items: PhrasePair[]
}

export interface Discovery {
  score: number
  tie: number
  rank_ab: number | null
  rank_ba: number | null
  a: UnitSummary
  b: UnitSummary
  a_verse: Verse | null
  b_verse: Verse | null
  a_preview: string | null
  b_preview: string | null
}

export interface DiscoveriesResponse {
  unit_type: UnitType
  mode: Mode
  book: number | null
  cross_book: boolean
  /** only the pairs this unit is in */
  unit: string | null
  total: number
  offset: number
  limit: number
  items: Discovery[]
}

export interface SimilarResponse {
  unit: UnitSummary
  mode: Mode
  k: number
  exclude: Exclude[]
  hits: Hit[]
}

export interface WordRef {
  idx: number
  display_idx: number | null
  in_formula: boolean
}

export interface SharedLemma {
  lemma: string
  he_lemma: string
  formula: boolean
  a_words: WordRef[]
  b_words: WordRef[]
}

export interface ExplainResponse {
  a: number
  b: number
  shared: SharedLemma[]
}

export interface LemmaForm {
  lemma: string
  he_lemma: string
}

export interface Pair {
  src: number
  tgt: number
  cosine: number
  shared: LemmaForm[]
}

export interface CompareResponse {
  a: UnitSummary
  b: UnitSummary
  bma: number
  a_to_b: Pair[]
  b_to_a: Pair[]
  verses: Record<string, Verse>
}

export interface SearchHit extends Breakdown {
  rank: number
  verse: Verse
  label_en: string
  label_he: string
}

export interface SearchResponse {
  book: number | null
  query: string
  normalized: string
  tokens: string[]
  mode: Mode
  k: number
  hits: SearchHit[]
}

export interface ResolveResponse {
  query: string
  unit: UnitSummary | null
}

export interface LemmaStat {
  lemma: string
  he_lemma: string
  n_verses: number
}

export interface LemmaLookup {
  query: string
  /** exact matches first, then prefixes; the commonest first */
  items: LemmaStat[]
}

export interface WordDetail {
  idx: number
  display_idx: number | null
  surface: string
  lemma: string
  morph: string | null
  morph_he: string[]
  in_formula: boolean
  lemmas: LemmaStat[]
  /** SDBH domain codes of its content morphemes (named by `/domains`) */
  domains: string[]
  /** its content lemmas' root families (`bsim roots`; empty without it) */
  roots: RootRef[]
}

/** A content lemma's root family (DESIGN.md §16.38), when the family has other words */
export interface RootRef {
  lemma: string
  /** Strong's number of the root */
  root: string
  /** the root's Strong's headword */
  root_he: string
}

export interface BookCount {
  book_id: number
  n_verses: number
}

/** An SDBH semantic domain (DESIGN.md §16.22); counts include its subdomains. */
export interface DomainInfo {
  /** 3 digits per level, e.g. 002001001069 */
  code: string
  level: number
  parent: string | null
  label_en: string
  n_verses: number
  weight: number
}

export interface DomainHit {
  verse: Verse
  label_en: string
  label_he: string
  display_idxs: number[]
  weight: number
}

export interface DomainResponse {
  domain: DomainInfo
  /** its broader domains, from the top */
  path: DomainInfo[]
  children: DomainInfo[]
  by_book: BookCount[]
  book: number | null
  total: number
  offset: number
  limit: number
  items: DomainHit[]
}

export interface DomainShare {
  domain: DomainInfo
  weight: number
  expected: number
  lift: number
  /** Dunning's G², negative when under-represented */
  g2: number
}

export interface UnitDomains {
  unit: UnitSummary
  total: number
  themes: DomainShare[]
  broad: DomainShare[]
}

export interface ConcordanceHit {
  verse: Verse
  label_en: string
  label_he: string
  display_idxs: number[]
}

export interface ConcordanceResponse {
  lemma: string
  he_lemma: string
  n_words: number
  n_verses: number
  by_book: BookCount[]
  book: number | null
  total: number
  offset: number
  limit: number
  items: ConcordanceHit[]
}

export interface StructureScore {
  value: number
  pct: number
  z: number | null
  pair: [number, number] | null
}

export interface Echo {
  a: number
  b: number
  sim: number
}

export interface StructureBasis {
  matrix: number[][]
  inclusio: StructureScore | null
  chiasm: StructureScore | null
  echoes: Echo[]
}

export interface Leitwort {
  lemma: string
  he_lemma: string
  count: number
  expected: number
  g2: number
  multiple_of: number[]
  occurrences: Record<string, number[]>
}

export interface StructureResponse {
  unit: UnitSummary
  verse_ids: number[]
  semantic: StructureBasis
  lexical: StructureBasis
  leitworte: Leitwort[]
  /** Leitworte with each root's words counted together (empty without `bsim roots`) */
  root_leitworte: RootLeitwort[]
}

export interface RootLeitwort {
  root: string
  root_he: string
  count: number
  expected: number
  g2: number
  /** the family's words in the unit */
  lemmas: LemmaStat[]
  /** two or more words, none of them among the Leitworte by lemma */
  hidden: boolean
  /** verse_id -> display token indices */
  occurrences: Record<string, number[]>
}

export type StructureSort = 'semantic_chiasm' | 'lexical_chiasm' | 'semantic_inclusio' | 'lexical_inclusio'

export interface StructureRank {
  unit: UnitSummary
  semantic_inclusio: number | null
  semantic_inclusio_pct: number | null
  semantic_chiasm: number | null
  semantic_chiasm_pct: number | null
  semantic_chiasm_z: number | null
  lexical_inclusio: number | null
  lexical_inclusio_pct: number | null
  lexical_chiasm: number | null
  lexical_chiasm_pct: number | null
  lexical_chiasm_z: number | null
  semantic_inclusio_q: number | null
  semantic_chiasm_q: number | null
  lexical_inclusio_q: number | null
  lexical_chiasm_q: number | null
}

/** Multiples-of-m check of Leitwort counts: m -> observed vs count-matched expectation. */
export type LeitwortNumbers = {
  leitworte: number
  lemma_counts: number
  [m: string]: number | { multiples: number; expected: number; share: number | null; p: number }
}

export interface StructureRankingResponse {
  unit_type: UnitType
  by: StructureSort
  min_verses: number
  leitwort_numbers: LeitwortNumbers | null
  total: number
  offset: number
  limit: number
  items: StructureRank[]
}

export interface MapPoint {
  unit_id: string
  label_en: string
  label_he: string
  book_id: number
  n_verses: number
  x: number
  y: number
  cluster: number
  /** verses inside a list (`bsim forms`, §16.45) */
  list_verses: number
}

export interface MapCluster {
  cluster: number
  size: number
  lemmas: LemmaForm[]
}

export interface MapResponse {
  unit_type: UnitType
  points: MapPoint[]
  clusters: MapCluster[]
  /** lists computed (`bsim forms`): the map can be coloured by them */
  lists: boolean
}

export interface AffinityCell {
  a: number
  b: number
  n_pairs: number
  expected: number
  lift: number
}

export interface AffinityResponse {
  order: number[]
  cells: AffinityCell[]
}

export interface AffinityPair {
  score: number
  a: UnitSummary
  b: UnitSummary
  a_verse: Verse
  b_verse: Verse
  link: GoldLink | null
}

export interface StyloPoint {
  unit_id: string
  label_en: string
  label_he: string
  book_id: number
  n_words: number
  x: number
  y: number
}

export interface StyloAxis {
  pc: number
  variance: number
  positive: string[]
  negative: string[]
}

export interface StyloDelta {
  a: number
  b: number
  delta: number
}

export interface StylometryResponse {
  points: StyloPoint[]
  axes: StyloAxis[]
  order: number[]
  delta: StyloDelta[]
}

export interface StyloFeature {
  feature: string
  label: string
  rate: number
  z: number
}

export interface BookStyle {
  book_id: number
  n_words: number
  over: StyloFeature[]
  under: StyloFeature[]
  closest: StyloDelta[]
}

export interface Meta {
  build: Record<string, unknown>
  runtime: Record<string, unknown> & { encoder_ready?: boolean; encoder_error?: string | null; startup_s?: number }
}

export interface SequenceSummary {
  seq_id: number
  a_start: number
  a_end: number
  b_start: number
  b_end: number
  /** order of the b side: same, mirrored, or the same scene reordered */
  direction: SequenceDirection
  a_label: string
  b_label: string
  a_label_he: string
  b_label_he: string
  a_book: number
  b_book: number
  same_chapter: boolean
  n_pairs: number
  score: number
  q: number
  n_gold: number
}

export type SequenceDirection = 'forward' | 'reverse' | 'mixed'

export interface BookSpan {
  book_id: number
  /** first verse id */
  start: number
  /** last verse id */
  end: number
}

/** Every chain at once, for the arc diagram across the canon */
export interface SequenceArcsResponse {
  max_q: number | null
  direction: string | null
  /** chains matching; at most `serve.max_arcs` are returned, strongest first */
  total: number
  books: BookSpan[]
  items: SequenceSummary[]
}

export interface SequencesResponse {
  book: number | null
  cross_book: boolean
  hide_same_chapter: boolean
  max_q: number | null
  min_pairs: number
  unit: string | null
  direction: SequenceDirection | null
  total: number
  offset: number
  limit: number
  items: SequenceSummary[]
}

export type DiffOp = 'spelling' | 'form' | 'substitution' | 'omitted' | 'added' | 'moved'

export interface LadderRow {
  a: number | null
  b: number | null
  weight: number | null
  cosine: number | null
  gold: boolean
  a_marks: Record<string, DiffOp>
  b_marks: Record<string, DiffOp>
  loose: boolean
}

export interface ChangeExample {
  seq_id: number
  a: number
  b: number
  a_label: string
  b_label: string
  a_label_he: string
  b_label_he: string
}

export interface ChangeGroup {
  a_key: string | null
  b_key: string | null
  a_form: string | null
  b_form: string | null
  a_he: string | null
  b_he: string | null
  count: number
  n_sequences: number
  examples: ChangeExample[]
}

export interface ChangesResponse {
  op: DiffOp
  a_book: number | null
  b_book: number | null
  /** only verse pairs with a side in this unit */
  unit: string | null
  totals: Partial<Record<DiffOp, number>>
  total: number
  offset: number
  limit: number
  items: ChangeGroup[]
}

export interface SequenceDetail {
  sequence: SequenceSummary
  rows: LadderRow[]
  verses: Record<string, Verse>
}

export interface VerseHalves {
  verse_id: number
  n_cola: number
  cola: [number, number][]
  pauses: string[]
  cos: number | null
  shared: number | null
  shape: number | null
  balance: number | null
  prob: number | null
  /** spans between accent pauses of level 1-2 */
  clauses: [number, number][]
  /** bicolon with the next verse (two one-colon verses) */
  next_prob: number | null
  /** parallel verses, typed with the SDBH lexicon */
  relation: 'antithetic' | 'synonymous' | null
  relation_pairs: RelationPair[]
}

/** A word pair that types a parallel verse: antonyms, synonyms or two lemmas in one domain. */
export interface RelationPair {
  a: string
  b: string
  kind: 'antonym' | 'synonym' | 'domain'
  a_he: string
  b_he: string
}

export interface UnitParallelism {
  unit: UnitSummary
  parallel_at: number
  mean_prob: number | null
  share_parallel: number | null
  n_scored: number
  verses: VerseHalves[]
}

export interface ParallelUnit {
  unit: UnitSummary
  mean_prob: number
  share_parallel: number
  n_scored: number
  /** verses at `parallel_at` or above */
  n_parallel: number
  /** share of the parallel verses typed antithetic (null: none, or no lexicon) */
  share_antithetic: number | null
}

/** The antithetic / synonymous typing check of `bsim parallelism` (DESIGN.md §16.22). */
export type ParallelTyping = {
  lines: number
  antithetic: number
  synonymous: number
  antithetic_share: number
  pair_antithetic_share: number
  null_share: number | null
  null_p: number | null
  check_share: number | null
  check_lines: number
  rest_share: number | null
  check_p: number
  [k: string]: unknown
}

export interface ParallelBook {
  book_id: number
  poetic_accents: boolean
  mean_prob: number | null
  share_parallel: number | null
  n_scored: number
}

export interface ParallelismResponse {
  unit_type: UnitType
  book: number | null
  exclude_poetic: boolean
  parallel_at: number
  coefficients: Record<string, number>
  held_out_auc: Record<string, number>
  sort: 'prob' | 'antithetic'
  /** parallel verses a unit needs (0 unless sorted by antithetic share) */
  min_parallel: number
  typing: ParallelTyping | null
  books: ParallelBook[]
  total: number
  offset: number
  limit: number
  items: ParallelUnit[]
}

export interface WordplayPair {
  a_vid: number
  b_vid: number
  a_display: number | null
  b_display: number | null
  a_form: string
  b_form: string
  a_he: string
  b_he: string
  kind: 'substitution' | 'metathesis' | 'extension'
  gap: number
  score: number
  q: number
  a_label: string
  b_label: string
  a_label_he: string
  b_label_he: string
  verses: Verse[]
}

export interface WordplayResponse {
  book: number | null
  kind: string | null
  unit: string | null
  total: number
  expected_by_chance: number | null
  offset: number
  limit: number
  items: WordplayPair[]
}

export type EntityKind = 'person' | 'place' | 'mixed' | 'unclear'

export interface Entity {
  lemma: string
  he: string
  kind: EntityKind
  n_mentions: number
  n_verses: number
  n_here: number | null
  first_vid: number
  last_vid: number
  /** `lexicon`: Strong's part of speech; `cues`: guessed from context */
  kind_source: 'lexicon' | 'cues'
}

export interface EntitiesResponse {
  kind: string | null
  book: number | null
  q: string | null
  total: number
  offset: number
  limit: number
  items: Entity[]
}

export interface EntityPartner {
  lemma: string
  he: string
  kind: EntityKind
  n_verses: number
  expected: number
  g2: number
}

export interface EntityDetail {
  entity: Entity
  first_label: string
  last_label: string
  first_label_he: string
  last_label_he: string
  by_book: BookCount[]
  partners: EntityPartner[]
  links: { a: string; b: string; n_verses: number; g2: number }[]
}

export interface SeamFeature {
  feature: string
  label: string
  z: number
}

export interface Seam {
  book_id: number
  verse_id: number
  label: string
  label_he: string
  shift: number
  threshold: number
  rank: number
  features: SeamFeature[]
}

export interface CurvePoint {
  verse_id: number
  chapter: number
  verse: number
  shift: number
}

export interface SeamsResponse {
  book: number | null
  block_words: number
  threshold: number | null
  curve: CurvePoint[]
  seams: Seam[]
}

export interface VerseDiff {
  a: number
  b: number
  a_marks: Record<string, DiffOp>
  b_marks: Record<string, DiffOp>
  counts: Record<string, number>
  shared: number
  loose: boolean
}

/** recall@k, mrr@10, ndcg@10 (fractions) and `queries` (count). */
export type MetricSet = Record<string, number>

export interface EvalSplit {
  evaluated_at?: string
  config_hash?: string
  gold?: Record<string, { queries: number; pairs: number }>
  /** unit type -> system -> metrics */
  results: Record<string, Record<string, MetricSet>>
}

export type OpenBibleEval = {
  evaluated_at?: string
  split?: string
  gold?: Record<string, number>
  /** mode -> the system evaluated and its metrics on each gold set */
  results: Record<string, { system: string; openbible: MetricSet; sefaria: MetricSet }>
}

export type EtcbcEval = {
  evaluated_at?: string
  split?: string
  /** a pair is a parallel when both verses have at most this many partners */
  max_partners?: number
  stats?: { edges: number; pairs: number; parallels: number; formula_pairs: number }
  gold?: Record<string, number | null>
  /** mode -> the system evaluated and its metrics on each gold set */
  results: Record<string, { system: string; etcbc: MetricSet; sefaria: MetricSet }>
  /** similarity band (percent) -> fused recall@10 */
  bands?: Record<string, { pairs: number; 'recall@10': number | null }>
  coverage?: {
    pairs: number
    in_sequence?: number | null
    in_phrase?: number | null
    in_fused_top10?: number | null
    sequence_pairs?: number
    sequence_pairs_in_etcbc?: number | null
  }
}

/** A paired bootstrap of per-query gains (variant − baseline). */
export type Gain = { mean: number; lo: number; hi: number; better: number; worse: number; queries: number }

export type SupervisionEval = {
  evaluated_at?: string
  split?: string
  metric: string
  baseline: string
  /** list (semantic | fused) -> gold -> mean metric of the model in use */
  baseline_scores: Record<string, Record<string, number>>
  /** gold -> dev queries */
  queries: Record<string, number>
  /** the variant whose gain stands for a retrain's noise */
  noise: string | null
  results: Record<
    string,
    {
      overrides: Record<string, unknown>
      model: string
      /** training rows per pair source */
      rows_by_source: Record<string, number>
      /** list -> gold -> mean metric */
      scores: Record<string, Record<string, number>>
      /** gold -> list -> gain over the baseline */
      gains: Record<string, Record<string, Gain>>
      adopt: boolean
    }
  >
  chosen: string | null
}

export interface EvalResponse {
  splits: Record<string, EvalSplit>
  openbible: OpenBibleEval | null
  etcbc: EtcbcEval | null
  supervision: SupervisionEval | null
  /** unit type -> mode -> the system served for it */
  final: Record<string, Record<string, string>>
}

export interface AcrosticLine {
  verse_id: number
  display_idx: number
  letter: string
}

export interface Acrostic {
  unit: UnitSummary
  granularity: 'verse' | 'colon'
  order_name: 'standard' | 'pe-ayin'
  score: number
  n_letters: number
  missing: number
  first_letter: string
  last_letter: string
  n_lines: number
  p: number
  q: number
  chain: AcrosticLine[]
}

export interface AcrosticsResponse {
  max_q: number | null
  book: number | null
  known_recall: number | null
  total: number
  offset: number
  limit: number
  items: Acrostic[]
}

export type RewriteOp = 'substitution' | 'omitted' | 'added'

export interface Rewrite {
  a_book: number
  b_book: number
  op: RewriteOp
  a_key: string | null
  b_key: string | null
  a_he: string | null
  b_he: string | null
  n: number
  base: number
  rate: number | null
  g2: number
  p: number
  q: number
}

export interface RewriteProfile {
  a_book: number
  b_book: number
  verse_pairs: number
  a_words: number
  b_words: number
  spelling: number
  form: number
  substitution: number
  omitted: number
  added: number
  moved: number
  to_plene: number
  to_defective: number
}

export interface RewritesResponse {
  a_book: number | null
  b_book: number | null
  op: RewriteOp | null
  max_q: number | null
  total: number
  offset: number
  limit: number
  items: Rewrite[]
}

export interface NetworkNode {
  unit: UnitSummary
  pagerank: number
  strength: number
  partners: number
  cross_book: number
  community: number
  x: number
  y: number
}

export interface NetworkCommunity {
  community: number
  size: number
  lemmas: LemmaForm[]
  books: BookCount[]
}

export interface NetworkResponse {
  unit_type: UnitType
  communities: NetworkCommunity[]
  central: NetworkNode[]
}

export interface CommunityResponse {
  unit_type: UnitType
  community: NetworkCommunity
  nodes: NetworkNode[]
  edges: { a: string; b: string; weight: number }[]
}

export interface UnitNetwork {
  node: NetworkNode
  rank: number
  of: number
  community_size: number
}

export interface WordPair {
  a: LemmaForm
  b: LemmaForm
  n: number
  expected: number
  g2: number
  q: number
  reverse: number
  examples: { verse_id: number; label_en: string; label_he: string }[]
}

export interface WordPairsResponse {
  max_q: number | null
  lemma: string | null
  total: number
  offset: number
  limit: number
  items: WordPair[]
}

export interface Alliteration {
  verse: Verse
  label: string
  label_he: string
  colon: number
  sound: string
  count: number
  n_words: number
  words: number[]
  p: number
  q: number
}

export interface AlliterationResponse {
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: Alliteration[]
}

export interface Rhyme {
  start_vid: number
  end_vid: number
  label: string
  label_he: string
  n_cola: number
  ending: string
  members: [number, number][]
  verses: Verse[]
  p: number
  q: number
}

export interface RhymesResponse {
  book: number | null
  max_q: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: Rhyme[]
}

export interface TypeScene {
  a: UnitSummary
  b: UnitSummary
  score: number
  n_matches: number
  aligned: { a_vid: number; b_vid: number; lemma: string; he_lemma: string }[]
  parallel_text: boolean
  q: number
}

export interface TypeScenesResponse {
  book: number | null
  max_q: number | null
  hide_textual: boolean
  unit: string | null
  total: number
  offset: number
  limit: number
  items: TypeScene[]
}

/** How much a lemma's senses and uses depend on the corpus group (DESIGN.md §16.23). */
export interface LemmaShift {
  lemma: string
  he_lemma: string
  n: number
  groups: Record<string, number>
  k: number
  silhouette: number
  /** MI(group; use) in bits minus its shuffled mean */
  use_excess: number
  use_q: number
  n_senses: number
  /** null: fewer than two SDBH meanings to compare */
  sense_excess: number | null
  sense_q: number | null
  nmi: number | null
  nmi_null: number | null
}

export interface SenseExample {
  verse: Verse
  label_en: string
  label_he: string
  display_idx: number | null
}

export interface LemmaSense {
  /** `use`: a contextual-use cluster; `sdbh`: a dictionary meaning */
  kind: 'use' | 'sdbh'
  sense: string
  n: number
  groups: Record<string, number>
  collocates: LemmaForm[]
  examples: SenseExample[]
  domains: string[]
}

export interface LemmaSensesResponse {
  lemma: string
  he_lemma: string
  group_order: string[]
  shift: LemmaShift | null
  uses: LemmaSense[]
  senses: LemmaSense[]
}

export interface ShiftsResponse {
  by: 'sense' | 'use'
  max_q: number | null
  group_order: string[]
  nmi_mean: number | null
  nmi_null_mean: number | null
  total: number
  offset: number
  limit: number
  items: LemmaShift[]
}

/** A chapter's Late Biblical Hebrew profile (DESIGN.md §16.24). */
export interface DatingChapter {
  unit_id: string
  book_id: number
  chapter: number
  n_words: number
  /** training books (early / late) are scored by models that did not see them */
  role: 'early' | 'late' | 'scored'
  /** poetry: the model is calibrated on prose */
  out_of_domain: boolean
  /** 0 = like Genesis–Kings, 1 = like the late books; null: too short */
  score: number | null
  features: Record<string, number>
  drivers: string[]
}

export interface DatingBook {
  book_id: number
  role: 'early' | 'late' | 'scored'
  out_of_domain: boolean
  n_chapters: number
  score: number | null
  low: number | null
  high: number | null
  features: Record<string, number>
}

export interface SynopticExample {
  early_first: number
  late_first: number
  early_label: string
  late_label: string
  early_label_he: string
  late_label_he: string
  early_score: number
  late_score: number
}

export interface DatingResponse {
  features: string[]
  coefficients: Record<string, number>
  held_out_auc: number | null
  held_out_auc_grammar: number | null
  train_chapters: Record<string, number>
  /** pairs, later, p, later_grammar, p_grammar */
  synoptic: Record<string, number | null>
  synoptic_examples: SynopticExample[]
  books: DatingBook[]
}

// --- your labels (DESIGN.md §16.25) ---

export type LabelValue = 'real' | 'not' | 'unsure'

export interface LabelIn {
  a_id: string
  b_id: string
  label: LabelValue
  note: string
  mode?: string | null
  score?: number | null
}

export interface Label {
  unit_type: string
  /** starts earlier in the canon */
  a: UnitSummary
  b: UnitSummary
  label: LabelValue
  note: string
  mode: string | null
  score: number | null
  labeled_at: string
}

export interface LabelsResponse {
  writable: boolean
  counts: Record<string, number>
  items: Label[]
}

export interface LabelSeparation {
  unit_type: string
  mode: string
  n_real: number
  n_not: number
  found_real: number
  found_not: number
  recall: number | null
  precision: number | null
  auc: number | null
}

export interface LabelsEval {
  k: number
  min_pairs: number
  rows: LabelSeparation[]
}

// --- BHSA syntax: clauses, speakers, who speaks where (DESIGN.md §16.26) ---

export interface ClauseSegment {
  function: string
  typ: string
  text: string
}

export type SpeakerSource = 'explicit' | 'carried' | 'enclosing'
/** how the addressee was found (DESIGN.md §16.44) */
export type AddresseeSource = 'explicit' | 'vocative' | 'pronoun' | 'turn'

export interface ClauseInfo {
  typ: string
  kind: string
  /** text type with its embedding: N, NQ, ?NQQ … */
  txt: string
  rela: string
  speech: boolean
  speaker: string | null
  speaker_he: string | null
  speaker_source: SpeakerSource | null
  divine: boolean
  /** lemma of whom the quotation is addressed to */
  addressee: string | null
  addressee_he: string | null
  addressee_source: AddresseeSource | null
  segments: ClauseSegment[]
}

export interface VerseSyntax {
  verse_id: number
  ref: string
  ref_he: string
  clauses: ClauseInfo[]
}

export interface SyntaxNeighbor {
  unit: UnitSummary
  score: number
  preview: string
}

export interface UnitSyntax {
  verses: VerseSyntax[]
  neighbors: SyntaxNeighbor[]
}

export interface SpeakerTarget {
  /** addressee lemma, or `divine` (the divine names together) */
  key: string
  /** null for `divine` */
  he: string | null
  n_quotes: number
}

export interface SpeakerInfo {
  lemma: string
  he: string
  n_words: number
  n_explicit: number
  divine: boolean
  /** whom they speak to most (a book's speakers; empty in the book list) */
  to: SpeakerTarget[]
}

export interface SpeechShares {
  narration: number
  speech: number
  discourse: number
  divine: number
  attributed: number
  n_words: number
}

export interface SpeechBook extends SpeechShares {
  book_id: number
  speakers: SpeakerInfo[]
}

export interface SpeechChapter extends SpeechShares {
  unit_id: string
  chapter: number
}

export interface SpeechResponse {
  meta: Record<string, unknown>
  books: SpeechBook[]
}

export interface SpeechBookResponse {
  book_id: number
  chapters: SpeechChapter[]
  speakers: SpeakerInfo[]
}

// --- dossier: every analysis on one unit (DESIGN.md §10) ---

export type DossierKind =
  | 'phrases'
  | 'sequences'
  | 'changes'
  | 'borrowing'
  | 'wordplay'
  | 'alliteration'
  | 'rhymes'
  | 'typescenes'
  | 'discoveries'
  | 'seams'
  | 'names'
  | 'acrostic'
  | 'dating'
  | 'structure'
  | 'speech'
  | 'voices'
  | 'network'
  | 'divisions'
  | 'ketiv'
  | 'citations'
  | 'allusions'
  | 'mirrors'
  | 'echoes'
  | 'meter'
  | 'roots'
  | 'refrains'
  | 'psalms'
  | 'pentateuch'
  | 'dialogue'
  | 'forms'
  | 'labels'

export interface DossierEntry {
  kind: DossierKind
  /** read on the unit itself or on the chapter holding it (`target_unit`) */
  scope: 'unit' | 'chapter'
  /** false: the stage did not run (or does not cover this unit type) */
  computed: boolean
  /** rows found; 1 / 0 for a yes / no finding; network: rank; divisions: flagged gaps in the unit */
  count: number | null
  /** network: units ranked */
  total: number | null
  /** lowest q (acrostic, structure), score (dating), divisions: score of the unit's opening gap, meter: net fall */
  value: number | null
  /** speech: speaker lemma; voices: voice profile key; divisions: kind of the opening gap */
  key: string | null
  /** speech / voices: the speaker's Hebrew form */
  label: string | null
  target_unit: string | null
}

export interface Dossier {
  unit_id: string
  entries: DossierEntry[]
}

// --- speaker voices (DESIGN.md §16.28) ---

export interface VoiceSpeaker {
  /** speaker lemma, or `divine` (the divine names together) */
  key: string
  /** Hebrew form of the lemma; null for `divine` */
  he: string | null
  n_words: number
  n_explicit: number
  n_clauses: number
  main_book: number
  books: number[]
  /** Burrows' Delta to the other attributed speech of the same books */
  delta: number
  null_mean: number
  /** (delta - null mean) / null sd */
  effect: number
  p: number
  q: number
}

export interface VoicePair {
  /** speaker keys, `narrator`, `unattributed` */
  a: string
  b: string
  delta: number
}

export interface AuthorCheck {
  speaker: string
  a: string[]
  b: string[]
  cross: number
  p_cross: number
  d_ab: number
  p_ab: number
  words_a: number
  words_b: number
  verdict: 'author' | 'differs' | 'same' | 'underpowered'
}

export interface DistinctCheck {
  book: string
  speaker: string
  rank: number | null
  of: number
  ranking: { key: string; effect: number; q: number }[]
}

/** `meta.voices`, all keys absent without `bsim voices` */
export interface VoicesMeta {
  speakers?: number | null
  significant?: number | null
  calibration?: { significant: number; of: number } | null
  sensitivity?: { speakers: number; rho: number | null } | null
  words?: Record<string, number> | null
  order?: string[] | null
  checks?: { author: AuthorCheck[]; distinct: DistinctCheck[] } | null
}

export interface VoicesResponse {
  meta: VoicesMeta & Record<string, unknown>
  speakers: VoiceSpeaker[]
  pairs: VoicePair[]
}

export interface VoiceFeature {
  side: 'over' | 'under'
  rank: number
  feature: string
  label: string
  rate: number
  rate_ref: number
  z: number
}

export interface VoiceChapter {
  unit_id: string
  book_id: number
  chapter: number
  n_clauses: number
}

export interface VoiceDetail {
  speaker: VoiceSpeaker
  features: VoiceFeature[]
  /** a = this speaker, nearest first */
  nearest: VoicePair[]
  chapters: VoiceChapter[]
}

// --- who borrowed (DESIGN.md §16.27) ---

export type BorrowDirection = 'a_to_b' | 'b_to_a' | 'unclear'

export interface SignCheck {
  agree: number
  n: number
  p: number | null
  unclear: number | null
}

/** A cross-book parallel; A is the side earlier in the canon, a sign > 0 says B looks later. */
export interface BorrowingSequence {
  seq_id: number
  a_book: number
  b_book: number
  a_first: number
  b_first: number
  a_label: string
  b_label: string
  a_label_he: string
  b_label_he: string
  n_pairs: number
  language: number
  spelling: number | null
  smoothing: number | null
  expansion: number | null
  n_spelling: number
  n_substitution: number
  known: 'a_to_b' | 'b_to_a' | null
  votes: number
  n_votes: number
  direction: BorrowDirection
}

export interface BorrowingBookPair {
  a_book: number
  b_book: number
  sequences: number
  n_pairs: number
  votes: number
  a_to_b: number
  b_to_a: number
  known: 'a_to_b' | 'b_to_a' | null
  direction: BorrowDirection
  items: BorrowingSequence[]
}

export interface BorrowingResponse {
  /** only the parallels touching this unit */
  unit: string | null
  checks: Record<string, SignCheck>
  used_signs: string[]
  held_out: SignCheck | null
  books: BorrowingBookPair[]
}

// --- where the text turns and where it is divided (DESIGN.md §16.29) ---

export type SegmentKind = 'turn' | 'cut' | 'quiet'
export type Paragraph = 'pe' | 'samekh'

/** A book's top-K gaps as a segmentation against its MAM breaks or its chapters */
export interface SegmentBook {
  book_id: number
  ref: 'mam' | 'chapter'
  /** Pk window, in verses */
  k: number
  pk: number
  /** mean over K random gaps */
  pk_null: number
  pk_p: number
  wd: number
  wd_null: number
  wd_p: number
}

/** One kind of division: its gaps' mean score against the labels shuffled in each book */
export interface SegmentGroup {
  n: number
  score: number | null
  null: number | null
  p: number | null
  lex: number | null
  sem: number | null
}

export interface SegmentContrast {
  a: number | null
  b: number | null
  diff: number | null
  p: number | null
}

/** `meta.segments`, all keys absent without `bsim segments` */
export interface SegmentsMeta {
  window?: number
  window_grid?: Record<string, number>
  gaps?: number
  groups?: Record<string, SegmentGroup>
  contrasts?: Record<string, SegmentContrast>
  calibration?: SegmentGroup
  seams?: { n: number; share: number | null; null: number | null; p: number | null; near?: number }
  agreement?: Record<string, { books: number; pk: number; pk_null: number; wd: number; wd_null: number; better: number }>
  kinds?: Record<SegmentKind, number>
}

export interface SegmentsResponse {
  meta: SegmentsMeta & Record<string, unknown>
  books: SegmentBook[]
}

/** A gap between two verses (`verse_id` = the verse after it) */
export interface SegmentGap {
  verse_id: number
  book_id: number
  label: string
  label_he: string
  /** within-book percentile of the cohesion drop (1 = the book's sharpest turn) */
  score: number
  lex: number
  sem: number
  mam: Paragraph | null
  oshb: Paragraph | null
  chapter: boolean
  seam: boolean
  kind: SegmentKind | null
  /** the verse before the gap and the verse after it */
  verses: Verse[]
}

export interface SegmentGapsResponse {
  kind: SegmentKind | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: SegmentGap[]
}

export interface SegmentPoint {
  verse_id: number
  chapter: number
  verse: number
  score: number
  mam: Paragraph | null
  oshb: Paragraph | null
  chapter_start: boolean
  seam: boolean
  kind: SegmentKind | null
}

export interface SegmentCurve {
  book_id: number
  points: SegmentPoint[]
  agreement: SegmentBook[]
}

// --- what is written against what is read (DESIGN.md §16.30) ---

export type KqClass =
  | 'vowel_letter'
  | 'swap'
  | 'vowel_position'
  | 'metathesis'
  | 'division'
  | 'qere_only'
  | 'ketiv_only'
  | 'same_letters'
  | 'other'
export type KqGrammar = 'spelling' | 'form' | 'word'
export type KqParallel = 'qere' | 'ketiv' | 'neither'

export interface KqBook {
  book_id: number
  n: number
  words: number
  /** per 1,000 words */
  rate: number
  vowel_letter: number
  /** share of the vowel-letter pairs written fuller than read */
  ketiv_fuller: number | null
  swap: number
  division: number
  other_cls: number
  form: number
  word: number
}

export interface KqLetter {
  /** two letters, sorted */
  pair: string
  n: number
  expected: number
  ratio: number | null
  p: number
  q: number
  lookalike: boolean
}

interface KqShare {
  n: number
  lookalike: number
  share: number | null
  expected: number
  p: number
}

/** `meta.ketiv`, all keys absent without `bsim ketiv` */
export interface KetivMeta {
  pairs?: number
  classes?: Partial<Record<KqClass, number>>
  grammar?: Partial<Record<KqGrammar, number>>
  euphemisms?: number
  /** [feature difference, count], most frequent first */
  features?: [string, number][]
  checks?: {
    lookalike: { all: KqShare; without_wy: KqShare }
    late_fuller: { late: number | null; late_n?: number; other: number | null; other_n?: number; diff: number | null; p: number | null; books?: number }
    parallel: { qere: number; ketiv: number; neither: number; p: number | null }
    plural_suffix: { plural: number; waw_yw: number }
    books: { chi2: number | null; p: number | null }
  }
}

export interface KetivResponse {
  meta: KetivMeta & Record<string, unknown>
  books: KqBook[]
  letters: KqLetter[]
}

export interface KqPair {
  kq_id: number
  verse_id: number
  book_id: number
  label: string
  label_he: string
  /** as written, unpointed */
  ketiv: string
  /** as read, pointed */
  qere: string
  cls: KqClass
  fuller: 'ketiv' | 'qere' | null
  /** swap: ketiv letter > qere letter */
  letters: string | null
  grammar: KqGrammar | null
  /** inflection features that differ, e.g. `number s>p` */
  features: string[]
  euphemism: boolean
  /** what an aligned parallel passage writes */
  parallel: KqParallel | null
  partner_vid: number | null
  partner_label: string | null
  partner_label_he: string | null
  partner_form: string | null
  verse: Verse
  /** display tokens of the read words */
  display: number[]
}

export interface KqPairsResponse {
  cls: KqClass | null
  grammar: string | null
  parallel: string | null
  euphemism: boolean | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: KqPair[]
}

// --- verses that say they quote or fulfil another (DESIGN.md §16.31) ---

export type CitationFamily = 'written' | 'word' | 'command'

export interface CitationBook {
  /** the citing book */
  book_id: number
  /** the cited book */
  target_book: number
  n: number
}

export interface CitationFamilyStats {
  verses: number
  resolved: number
  share: number | null
  /** share of random verses of the same books whose two signals agree */
  null_share: number | null
  p: number | null
  pct_median: number | null
}

/** `meta.citations`, all keys absent without `bsim citations` */
export interface CitationsMeta {
  citations?: number
  resolved?: number
  families?: Partial<Record<CitationFamily, CitationFamilyStats>>
  gold?: { named: number; found: number; missing: string[]; top1: number; top_k: number; k: number; resolved: number; resolved_right: number }
  word_lag_median?: number | null
  book_pairs?: number
}

export interface CitationsResponse {
  meta: CitationsMeta & Record<string, unknown>
  books: CitationBook[]
}

export interface CitationCandidate {
  verse_id: number
  label: string
  label_he: string
  score: number
}

export interface Citation {
  cite_id: number
  family: CitationFamily
  verse_id: number
  book_id: number
  label: string
  label_he: string
  /** the matched words, consonantal */
  formula: string
  verse: Verse
  target: Verse | null
  target_label: string | null
  target_label_he: string | null
  score: number | null
  pct: number | null
  /** BM25 alone and cosine alone agree on the source */
  resolved: boolean
  candidates: CitationCandidate[]
  gold_rank: number | null
  /** scholarship names a source for this citation */
  named: boolean
}

export interface CitationListResponse {
  family: CitationFamily | null
  resolved: boolean | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: Citation[]
}

// --- rare words two passages share over a few verses (DESIGN.md §16.32) ---

export interface AllusionLemma {
  /** Strong's number */
  lemma: string
  form: string
}

export interface Allusion {
  allusion_id: number
  a_start: number
  a_end: number
  b_start: number
  b_end: number
  a_label: string
  a_label_he: string
  b_label: string
  b_label_he: string
  n_shared: number
  score: number
  q: number
  /** already a fused neighbour or a parallel sequence */
  known: boolean
  /** rarest first */
  lemmas: AllusionLemma[]
  a_verses: Verse[]
  b_verses: Verse[]
  /** verse_id -> display tokens of the shared words */
  a_marks: Record<string, number[]>
  b_marks: Record<string, number[]>
}

/** `meta.allusions`, all keys absent without `bsim allusions` */
export interface AllusionsMeta {
  rare_lemmas?: number
  window?: number
  pairs?: number
  known?: number
  max_q?: number
  strong?: number
  strong_known?: number
  best_new_q?: number | null
}

export interface AllusionsResponse {
  meta: AllusionsMeta & Record<string, unknown>
  known: boolean | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: Allusion[]
}

// --- the tested claim of each analysis (`/findings`, DESIGN.md §10) ---

export type FindingKey =
  | 'acrostics'
  | 'divisions'
  | 'dating'
  | 'borrowing'
  | 'citations'
  | 'voices'
  | 'clauses'
  | 'meter'
  | 'cognate'
  | 'echoes'
  | 'sevens'
  | 'chiasm'
  | 'laments'
  | 'root_leitworte'
  | 'allusions'
  | 'refrains'
  | 'refrain_regular'
  | 'refrain_turns'
  | 'psalm_genres'
  | 'psalm_forms'
  | 'lament_turn'
  | 'lament_turns'
  | 'pentateuch_split'
  | 'pentateuch_genesis'
  | 'pentateuch_names'
  | 'dialogue_deference'
  | 'dialogue_particle'
  | 'dialogue_last_word'
  | 'forms_known'
  | 'forms_chance'
  | 'forms_parallel'
  | 'forms_lists'

export interface Finding {
  key: FindingKey
  verdict: 'holds' | 'fails' | 'lead'
  /** the deciding numbers; which keys depends on `key` */
  values: Record<string, number | null>
}

export interface FindingsResponse {
  alpha: number
  /** in page order; analyses not computed are left out */
  items: Finding[]
}

// --- a direction on the cross-book echoes (DESIGN.md §16.36) ---

export type EchoBasis = 'cited' | 'borrowed' | 'language' | 'conflict' | 'none'

export interface EchoBook {
  /** the book drawn on */
  src_book: number
  /** the book echoing it */
  dst_book: number
  /** directed chapter pairs by the layer that decided them */
  cited: number
  borrowed: number
  language: number
}

export interface EchoChapter {
  unit: UnitSummary
  /** directed pairs it is the source of */
  lends: number
  /** directed pairs it is the echo of */
  borrows: number
  /** cited or borrowed only */
  lends_explicit: number
  borrows_explicit: number
}

export interface EchoCheck {
  n: number
  agree: number
  p: number
  underpowered: boolean
}

/** `meta.echoes`, all keys absent without `bsim echoes` */
export interface EchoesMeta {
  language_gap?: number
  pairs?: number
  network_pairs?: number
  in_domain?: number
  bases?: Record<EchoBasis, number>
  checks?: { cited: EchoCheck; spelling: EchoCheck; borrowed: EchoCheck }
  language_forward?: number
  language_backward?: number
  /** book ids, each a cycle of the cited / borrowed book graph */
  cycles?: number[][]
}

export interface EchoesResponse {
  meta: EchoesMeta & Record<string, unknown>
  books: EchoBook[]
  sources: EchoChapter[]
}

/** A cross-book chapter pair; a is the earlier in the canon */
export interface EchoEdge {
  edge_id: number
  a: UnitSummary
  b: UnitSummary
  /** network edge weight */
  weight: number
  /** resolved citations from b into a */
  n_cited: number
  /** +1 b borrowed from a, -1 a from b, 0 none / unclear */
  borrowed: number
  /** late-profile score of b minus a (null: a side out of domain) */
  gap: number | null
  language: number | null
  /** +1 b echoes a, -1 a echoes b, 0 undecided */
  direction: number
  basis: EchoBasis
}

export interface EchoListResponse {
  basis: EchoBasis | null
  directed: boolean | null
  backward: boolean | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: EchoEdge[]
}

// --- chiasm at the small scale (DESIGN.md §16.33) ---

export interface WordOrderTest {
  verses_chiastic: number
  verses_parallel: number
  pairs_chiastic: number
  pairs_parallel: number
  /** chiastic pairs / (chiastic + parallel) */
  share: number
  p: number | null
  verses: number
  bigrams: number
  /** 95 % interval of the share, chapters resampled */
  interval?: [number, number]
}

export interface ClausePairStats {
  pair: string
  n: number
  poetry: number | null
  poetry_n: number
  prose: number | null
  prose_n: number
}

/** `meta.mirrors`, all keys absent without `bsim mirrors` */
export interface MirrorsMeta {
  words?: { all: WordOrderTest; poetry: WordOrderTest; prose: WordOrderTest }
  clauses?: { poetry: number | null; poetry_n: number; prose: number | null; prose_n: number; diff: number; p: number; pairs: number; by_pair: ClausePairStats[] }
  full_mirrors?: number
  full_mirrors_q?: number
  min_words?: number
}

export interface MirrorsResponse {
  meta: MirrorsMeta & Record<string, unknown>
}

export interface MirrorVerse {
  verse_id: number
  label: string
  label_he: string
  poetic: boolean
  n_pairs: number
  n_words: number
  p: number
  q: number
  verse: Verse
  /** display token -> nesting depth of its lemma (0 = the outermost pair) */
  marks: Record<string, number>
}

export interface MirrorVersesResponse {
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: MirrorVerse[]
}

export interface MirrorClause {
  pair_id: number
  verse_id: number
  label: string
  label_he: string
  poetic: boolean
  /** the two constituents, sorted */
  pair: string
  first: string
  second: string
  mirrored: boolean
  verse: Verse
  /** display token -> 0 (the first clause's first constituent) or 1 */
  marks: Record<string, number>
}

export interface MirrorClausesResponse {
  pair: string | null
  mirrored: boolean | null
  poetic: boolean | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: MirrorClause[]
}

// --- stresses per line and the falling lament line (DESIGN.md §16.37) ---

export type MeterGroup = 'test' | 'control' | 'pool' | 'poetic' | 'prose'

export interface MeterChapter {
  unit: UnitSummary
  /** the test / control chapters, the poetry pool (prose accents), the poetic accent books, the rest */
  group: MeterGroup
  /** measured lines: `min_stresses`…`max_stresses`, both members stressed */
  n_lines: number
  /** share with the first member longer (3:2) */
  fall: number
  /** share with it shorter (2:3) */
  rise: number
  /** fall − rise */
  net: number
  share32: number
  /** mean probability of parallel verse halves */
  prob: number | null
  /** share of the pool chapters with a lower net fall */
  pct: number | null
}

export interface MeterGroupTest {
  n: number
  pool_n: number
  mean: number | null
  pool_mean: number | null
  null_mean?: number
  p: number | null
}

export interface MeterGroupStats {
  chapters: number
  lines: number
  fall: number | null
  rise: number | null
  /** commonest `a:b` patterns with their counts */
  patterns: [string, number][]
}

/** `meta.meter`, all keys absent without `bsim meter` */
export interface MeterMeta {
  min_stresses?: number
  max_stresses?: number
  min_lines?: number
  pool_quantile?: number
  pool_prob?: number
  lines?: number
  split?: number
  /** the test chapters against the poetry pool / the poetic accent books */
  test?: MeterGroupTest
  test_poetic?: MeterGroupTest
  /** chapters naming a lament (קינה) against the pool */
  named?: MeterGroupTest
  grid?: { min: number; max: number; mean: number | null; pool_mean: number | null; pool_p: number | null; poetic_p: number | null }[]
  groups?: Partial<Record<MeterGroup, MeterGroupStats>>
}

export interface MeterResponse {
  meta: MeterMeta & Record<string, unknown>
  test_chapters: MeterChapter[]
  control_chapters: MeterChapter[]
  named_chapters: MeterChapter[]
  group: MeterGroup | null
  book: number | null
  total: number
  offset: number
  limit: number
  /** highest net fall first */
  items: MeterChapter[]
}

export interface MeterLine {
  /** inclusive display-token span */
  first: number
  last: number
  stresses: number
  /** stresses of the two members; null when the line does not split */
  a: number | null
  b: number | null
}

export interface MeterVerse {
  verse_id: number
  lines: MeterLine[]
}

export interface UnitMeter {
  unit_id: string
  min_stresses: number
  max_stresses: number
  /** the chapter the unit starts in */
  chapter: MeterChapter | null
  verses: MeterVerse[]
}

// --- root families (DESIGN.md §16.38) ---

export type RootPairKind = 'cognate' | 'other' | 'inf_abs'

export interface RootBook {
  book_id: number
  /** Hebrew words */
  words: number
  /** a verb and a noun of one root side by side */
  cognate: number
  /** ... with the content words permuted within chapters */
  expected: number
  /** infinitive absolute + finite verb (מות יומת) */
  inf_abs: number
}

export interface RootKnown {
  unit: UnitSummary
  root: string
  root_he: string
  /** best rank of any word of the family, counted by lemma */
  lemma_rank: number | null
  /** rank of the family counted by root */
  root_rank: number | null
}

export interface RootTest {
  observed: number
  expected: number
  ratio: number
  p: number
}

/** `meta.roots`, all keys absent without `bsim roots` */
export interface RootsMeta {
  entries?: number
  derived?: number
  joined?: number
  lemmas?: number
  families?: number
  family_lemmas?: number
  window?: number
  shuffles?: number
  pairs?: Record<RootPairKind, number>
  tests?: { cognate: RootTest; other: RootTest }
  known_top_lemma?: number
  known_top_root?: number
  known_better?: number
  top?: number
  hidden?: number
}

export interface RootsResponse {
  meta: RootsMeta & Record<string, unknown>
  known: RootKnown[]
  /** canon order */
  books: RootBook[]
}

export interface RootPair {
  pair_id: number
  verse_id: number
  label: string
  label_he: string
  kind: RootPairKind
  root: string
  root_he: string
  a: LemmaStat
  b: LemmaStat
  verse: Verse
  /** display token -> 0 (the first word) or 1 */
  marks: Record<string, number>
}

export interface RootPairsResponse {
  kind: RootPairKind | null
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: RootPair[]
}

export interface HiddenRoot {
  unit: UnitSummary
  rank: number
  root: string
  root_he: string
  count: number
  g2: number
  /** Strong's numbers of the family in the chapter */
  n_words: number
  /** best rank of one of them counted by lemma */
  lemma_rank: number | null
  lemmas: LemmaStat[]
}

export interface HiddenRootsResponse {
  book: number | null
  unit: string | null
  total: number
  offset: number
  limit: number
  items: HiddenRoot[]
}

export interface RootFamily {
  root: string
  root_he: string
  /** commonest first */
  members: LemmaStat[]
  /** member lemma -> how Strong's derives it (from, feminine of, ...) */
  links: Record<string, string>
  n_verses: number
  by_book: BookCount[]
  book: number | null
  total: number
  offset: number
  limit: number
  items: ConcordanceHit[]
}

// The layered reader (`/reader/{unit}`, DESIGN.md §16.39): word-level layers keyed by display token.
export interface ReaderSpeaker {
  /** null: speech whose speaker is not known */
  lemma: string | null
  he: string | null
  divine: boolean
  n_words: number
  /** Hebrew forms of whom they speak to here, the most words first */
  to: string[]
}
export interface ReaderWordplay {
  display: number
  partner_vid: number
  partner_display: number | null
  partner_label: string
  partner_label_he: string
  form: string
  partner_form: string
  kind: 'substitution' | 'metathesis' | 'extension'
  q: number
}
export interface ReaderKetiv {
  /** display tokens of the read words */
  display: number[]
  ketiv: string
  qere: string
  cls: KqClass
}
export interface ReaderGap {
  /** within-book percentile of the cohesion drop (1 = the book's sharpest turn) */
  score: number
  kind: SegmentKind | null
  mam: Paragraph | null
  chapter: boolean
}
export interface ReaderRefrain {
  refrain_id: number
  text: string
  /** verses holding it */
  k: number
  known: string | null
}
export interface ReaderVerse {
  verse_id: number
  /** display token -> index into `refrains` */
  refrains: Record<string, number>
  /** display token -> distress | praise (its SDBH domains) */
  mood: Record<string, 'distress' | 'praise'>
  /** the P / non-P split (Genesis-Numbers only) */
  source: ReaderSource | null
  /** display token -> index into `speakers` */
  speech: Record<string, number>
  /** display token -> other verses sharing a phrase through it */
  phrases: Record<string, number>
  /** display token -> verses holding its rarest content word */
  rare: Record<string, number>
  wordplay: ReaderWordplay[]
  ketiv: ReaderKetiv[]
  /** the gap before the verse: flagged or a MAM break */
  gap: ReaderGap | null
}
export interface ReaderResponse {
  unit: UnitSummary
  rare_verses: number
  computed: Record<string, boolean>
  speakers: ReaderSpeaker[]
  /** strongest first */
  refrains: ReaderRefrain[]
  verses: ReaderVerse[]
}

// The Pentateuch's sources (`/pentateuch`, DESIGN.md §16.43): an unsupervised P / non-P split.
export interface ReaderSource {
  side: 'P' | 'nonP'
  /** of the P-like side, smoothed over neighbouring verses */
  prob: number
  /** null: unassigned */
  reference: 'P' | 'nonP' | null
}
export interface SourceWord {
  /** Strong's number (`@h` / `@q`: the stem), or `p:x` for a prefix */
  token: string
  he: string | null
  weight: number
}
export interface SourceSynonym {
  name: string
  members: string[]
  he: (string | null)[]
  p_like: number[]
  non_p: number[]
}
export interface PentateuchTest {
  observed: number
  null: number
  p: number
}
export interface PentateuchBook {
  verses: number
  agree: number | null
  p_like: number
  p_ref: number | null
}
export interface PentateuchSide {
  yhwh: number
  elohim: number
  share: number | null
}
export interface PentateuchMeta {
  verses?: number
  assigned?: number
  reference_p?: number
  p_like?: number
  chunks?: number
  core_verses?: number
  synonym_sets?: number
  alpha?: number
  draws?: number
  agreement?: number
  tests?: { kappa: PentateuchTest; kappa_genesis: PentateuchTest; names: PentateuchTest }
  confusion?: { p_like_p: number; p_like_non: number; non_p: number; non_non: number }
  books?: Record<string, PentateuchBook>
  names?: { p_like: PentateuchSide; non_p: PentateuchSide; reference_p: number | null; reference_non: number | null }
  grid?: {
    chunk_verses: number
    smooth: number
    kappa: number
    kappa_genesis: number
    names: number
    kappa_p: number
    kappa_genesis_p: number
    names_p: number
  }[]
}
export interface PentateuchResponse {
  meta: PentateuchMeta & Record<string, unknown>
  /** the words that pull a verse to the P-like side most */
  p_like: SourceWord[]
  non_p: SourceWord[]
  synonyms: SourceSynonym[]
}
export interface SourceChapter {
  unit_id: string
  label: string
  label_he: string
  book_id: number
  chapter: number
  verses: number
  /** share of its verses on the P-like side */
  p_like: number
  assigned: number
  /** share of its assigned verses the reference calls P */
  p_ref: number | null
}
export interface PentateuchChaptersResponse {
  book: number | null
  total: number
  offset: number
  limit: number
  items: SourceChapter[]
}

// Who speaks to whom (`/dialogue`, DESIGN.md §16.44).
export interface VerseLabel {
  verse_id: number
  label_en: string
  label_he: string
}
export interface DialogueParty {
  /** lemma, or `divine` (the divine names together) */
  key: string
  /** null for `divine` */
  he: string | null
  /** 2 God, 1 a king, 0 anyone else */
  rank: number
}
export interface DialogueBook {
  book_id: number
  n_quotes: number
  n_pairs: number
  n_exchanges: number
}
export interface DialogueRate {
  rate: number
  count: number
  of: number
  quotations: number
}
export interface DialogueUpTest {
  observed: number
  null: number | null
  p: number | null
  up: DialogueRate
  rest: DialogueRate
  holds?: boolean | null
}
export interface DialogueTurnTest {
  observed: number
  expected: number
  exchanges: number
  p: number
  holds?: boolean | null
}
export interface DialogueMeta {
  quotations?: number
  with_addressee?: number
  addressee?: Record<AddresseeSource, number>
  reliable?: AddresseeSource[]
  /** source -> [right, judged] */
  hand_check?: Record<AddresseeSource, [number, number]>
  pairs?: number
  exchanges?: number
  unequal?: number
  shuffles?: number
  alpha?: number
  tests?: { deference: DialogueUpTest; particle: DialogueUpTest; last_word: DialogueTurnTest }
  sensitivity?: { deference: DialogueUpTest; particle: DialogueUpTest }
  opener?: DialogueTurnTest
  lengths?: { longer: number; shorter: number; median_higher: number | null; median_lower: number | null; p: number | null }
}
export interface DialogueResponse {
  meta: DialogueMeta & Record<string, unknown>
  books: DialogueBook[]
}
export interface DialoguePair {
  speaker: DialogueParty
  addressee: DialogueParty
  n_quotes: number
  n_words: number
  /** quotations whose addressee is explicit or a vocative */
  n_reliable: number
}
export interface DialogueBookResponse {
  book_id: number
  /** the most quotations first */
  pairs: DialoguePair[]
}
export interface DialogueExchange {
  exchange: number
  book_id: number
  /** the chapter it starts in */
  unit_id: string
  first: VerseLabel
  last_verse: VerseLabel
  /** who opens */
  a: DialogueParty
  b: DialogueParty
  turns: number
  a_turns: number
  a_words: number
  b_words: number
  /** key of who speaks last */
  last: string
}
export interface DialogueExchangesResponse {
  book: number | null
  party: string | null
  unequal: boolean
  total: number
  offset: number
  limit: number
  items: DialogueExchange[]
}

// Graded numerical sayings and lists (`/forms`, DESIGN.md §16.45).
export interface FormsKnownSaying {
  name: string
  /** its first named verse */
  first: VerseLabel
  /** verses named */
  n_verses: number
  /** of them holding a graded pair */
  hits: number
  /** at least half */
  found: boolean
}
export interface FormsKnownList {
  name: string
  first: VerseLabel
  last_verse: VerseLabel
  n_verses: number
  /** its verses inside a list found */
  covered: number
  /** at least half */
  found: boolean
}
export interface FormsBook {
  book_id: number
  /** number words */
  numbers: number
  /** ... not part of a compound number */
  free: number
  sayings: number
  lists: number
  list_verses: number
}
export interface FormsChance {
  pairs: number
  observed: number
  expected: number
  p: number | null
  /** described, added after the first run: the test without these steps */
  without?: string[]
  without_observed?: number
  without_expected?: number
  without_p?: number | null
}
export interface FormsParallel {
  sayings: number
  others: number
  saying_prob: number
  other_prob: number
  saying_parallel: number
  other_parallel: number
  p: number | null
}
export type FormsKind = 'genealogy' | 'itinerary' | 'census' | 'offering' | 'kings' | 'names' | 'other'
export interface FormsListsMeta {
  threshold?: number
  like_verses?: number
  observed?: number
  expected?: number
  verses?: number
  kinds?: Partial<Record<FormsKind, number>>
  known_found?: number
  known_share?: number
  shuffles?: number
  min_verses?: number
  quantile?: number
}
export interface FormsMeta {
  window?: number
  alpha?: number
  shuffles?: number
  numbers?: number
  free?: number
  sayings?: number
  graded_pairs?: number
  /** "3 / 4" -> graded pairs */
  steps?: Record<string, number>
  chance?: FormsChance | null
  parallel?: FormsParallel | null
  known_found?: number
  known_share?: number
  lists: FormsListsMeta
}
export interface FormsResponse {
  meta: FormsMeta & Record<string, unknown>
  known: FormsKnownSaying[]
  known_lists: FormsKnownList[]
  /** canon order, books with a number or a list */
  books: FormsBook[]
}
export interface FormsPair {
  /** display tokens of the two numbers */
  a_tok: number | null
  b_tok: number | null
  a_value: number
  b_value: number
}
export interface FormsSaying {
  /** its chapter */
  unit_id: string
  n_pairs: number
  /** e.g. "3 / 4" */
  steps: string
  /** probability of parallel halves (§16.9) */
  prob: number | null
  /** the saying named in advance it is */
  known: string | null
  pairs: FormsPair[]
  verse: Verse
}
export interface FormsSayingsResponse {
  book: number | null
  unit: string | null
  known: boolean
  total: number
  offset: number
  limit: number
  items: FormsSaying[]
}
export interface FormsList {
  list_id: number
  book_id: number
  /** the chapter it starts in */
  unit_id: string
  first: VerseLabel
  last_verse: VerseLabel
  /** first to last */
  n_verses: number
  /** list-like verses */
  n_like: number
  /** mean best cosine of word shapes with a neighbour */
  likeness: number
  kind: FormsKind
  /** the list named in advance it is part of */
  known: string | null
  /** its first few verses */
  verses: Verse[]
}
export interface FormsListsResponse {
  book: number | null
  unit: string | null
  kind: string | null
  total: number
  offset: number
  limit: number
  items: FormsList[]
}

// Psalms (`/psalms`, DESIGN.md §16.42): the form of each psalm, Gunkel's genres, the lament's turn.
export type PsalmGenre = 'hymn' | 'lament_individual' | 'lament_communal' | 'royal' | 'thanksgiving' | 'trust' | 'wisdom'
export type PsalmFeature =
  | 'first_singular'
  | 'first_plural'
  | 'second'
  | 'imperative'
  | 'imperative_plural'
  | 'question'
  | 'distress'
  | 'praise'
export interface PsalmVerse {
  verse: number
  /** without the superscription */
  words: number
  distress: number
  praise: number
}
export interface PsalmTurn {
  /** the first verse after the split */
  verse_id: number
  verse: number
  label: string
  label_he: string
  /** mood rate (praise - distress words per word) after - before */
  stat: number
  /** against verse orders shuffled within the psalm */
  p: number
  before: number
  after: number
}
export interface Psalm {
  unit_id: string
  label: string
  label_he: string
  chapter: number
  /** Gunkel's (core cases); null: mixed or disputed */
  genre: string | null
  cluster: number
  words: number
  /** per word */
  features: Record<string, number>
  turn: PsalmTurn | null
  mood: PsalmVerse[]
}
export interface PsalmKnownTurn {
  verse_id: number
  label: string
  label_he: string
  turn_vid: number | null
  turn_label: string | null
  turn_label_he: string | null
  p: number | null
  /** null: the psalm is too short */
  found: boolean | null
  chance: number | null
}
export interface PsalmTest {
  nmi: number
  null: number
  p: number
}
export interface PsalmCheck {
  genre: string
  feature: string
  direction: 'higher' | 'lower'
  mean: number
  rest: number
  p: number
  q: number
}
export interface PsalmsMeta {
  psalms?: number
  labelled?: number
  genres?: Record<string, number>
  features?: string[]
  k?: number
  alpha?: number
  draws?: number
  title_words?: number
  genre_test?: PsalmTest
  crosstab?: { genre: string; cluster: number; n: number }[]
  checks?: PsalmCheck[]
  checks_held?: number
  profiles?: Record<string, Record<string, number>>
  cluster_profiles?: Record<string, Record<string, number>>
  known_turns?: { found: number; n: number; expected: number; p: number }
  laments_vs_hymns?: { laments: number; n_laments: number; hymns: number; n_hymns: number; p: number }
  tolerance?: number
  min_side?: number
  robustness?: {
    titles_kept: { nmi: number; known: number; laments_vs_hymns_p: number }
    form_only: PsalmTest
    domains_only: PsalmTest
    tolerance: Record<string, { found: number; expected: number; p: number }>
  }
}
export interface PsalmsResponse {
  meta: PsalmsMeta & Record<string, unknown>
  known: PsalmKnownTurn[]
}
export interface PsalmsListResponse {
  genre: string | null
  cluster: number | null
  turned: boolean
  unit: string | null
  sort: string
  total: number
  offset: number
  limit: number
  items: Psalm[]
}

// Refrains (`/refrains`, DESIGN.md §16.40): phrases that come back inside a passage.
export interface RefrainVerse {
  verse_id: number
  label: string
  label_he: string
  /** display tokens of the phrase, inclusive */
  first: number
  last: number
}
export interface Refrain {
  /** 1 = the strongest burst */
  refrain_id: number
  book_id: number
  /** verses holding it */
  k: number
  n_tokens: number
  p: number
  /** false discovery rate against verse orders shuffled within books */
  q: number
  /** coefficient of variation of the gaps between its verses */
  cv: number
  /** random placements as even (null: too few to test) */
  regular_p: number | null
  /** mean of each verse's sharper neighbouring gap score */
  turn: number | null
  /** the strongest refrain of its group sharing a verse */
  strongest: boolean
  known: string | null
  text: string
  lemmas: string
  occurrences: RefrainVerse[]
  /** the first few occurrences' verses */
  verses: Verse[]
}
export interface RefrainKnown {
  name: string
  first_vid: number
  label: string
  label_he: string
  n_verses: number
  refrain_id: number | null
  text: string | null
  k: number | null
  q: number | null
}
export interface RefrainBook {
  book_id: number
  refrains: number
  strongest: number
}
export interface RefrainTest {
  n?: number
  observed: number | null
  expected: number | null
  p?: number | null
}
export interface RefrainsMeta {
  min_tokens?: number
  min_count?: number
  max_gap?: number
  alpha?: number
  shuffles?: number
  candidates?: number
  detect?: RefrainTest
  refrains?: number
  distinct?: number
  known_found?: number
  known_share?: number
  regular?: { testable: number; regular: number; share: number | null; p: number | null }
  turns?: RefrainTest | null
}
export interface RefrainsResponse {
  meta: RefrainsMeta & Record<string, unknown>
  known: RefrainKnown[]
  books: RefrainBook[]
}
export interface RefrainsListResponse {
  book: number | null
  unit: string | null
  strongest: boolean
  known: boolean
  total: number
  offset: number
  limit: number
  items: Refrain[]
}
