// Mirrors the pydantic response models in src/bsim/api/models.py (DESIGN.md §10).

export type Mode = 'lexical' | 'semantic' | 'fused' | 'structural'
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

export interface WordDetail {
  idx: number
  display_idx: number | null
  surface: string
  lemma: string
  morph: string | null
  morph_he: string[]
  in_formula: boolean
  lemmas: LemmaStat[]
}

export interface BookCount {
  book_id: number
  n_verses: number
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
}

export interface StructureRankingResponse {
  unit_type: UnitType
  by: StructureSort
  min_verses: number
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
  runtime: Record<string, unknown>
}

export interface SequenceSummary {
  seq_id: number
  a_start: number
  a_end: number
  b_start: number
  b_end: number
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

export interface SequencesResponse {
  book: number | null
  cross_book: boolean
  hide_same_chapter: boolean
  max_q: number | null
  min_pairs: number
  unit: string | null
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
