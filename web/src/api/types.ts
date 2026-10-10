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

export interface EvalResponse {
  splits: Record<string, EvalSplit>
  openbible: OpenBibleEval | null
  etcbc: EtcbcEval | null
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

export interface SpeakerInfo {
  lemma: string
  he: string
  n_words: number
  n_explicit: number
  divine: boolean
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
  /** lowest q (acrostic, structure), score (dating), divisions: score of the unit's opening gap */
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
  | 'echoes'
  | 'sevens'
  | 'chiasm'
  | 'allusions'

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
