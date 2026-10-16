// The viewer's API types (DESIGN.md §10). A response model of src/bsim/api/models/ is an alias of
// its generated schema type (`npm run gen:api`); written here are the literal unions used as
// parameters, the JSON blobs the schema leaves open (eval results, meta checks), and the
// viewer's own types.
import type { components } from './schema.gen'

type S = components['schemas']

export type Mode = 'lexical' | 'semantic' | 'fused' | 'structural' | 'domain' | 'syntax'
export type SearchMode = 'lexical' | 'semantic' | 'fused'
export type UnitType = 'verse' | 'chapter' | 'pericope' | 'parasha'
export type Exclude = 'neighbors' | 'chapter' | 'book' | 'known'

export type Book = S['Book']

export type UnitSummary = S['UnitSummary']

export type Verse = S['Verse']

export type UnitDetail = S['UnitDetail']

export interface Breakdown {
  score: number
  lex_score: number | null
  lex_rank: number | null
  sem_score: number | null
  sem_rank: number | null
  /** the phrase list, on fused results of a unit type fused with it (§16.50) */
  phr_score: number | null
  phr_rank: number | null
}

/** A Sefaria link: `verse` = direct verse-to-verse, `unit` = only a passage-level link covers it. */
export type GoldLink = S['GoldLink']

export type PhraseInfo = S['PhraseInfo']

export type Hit = S['Hit']

export type PhrasePair = S['PhrasePair']

export type PhrasesResponse = S['PhrasesResponse']

export type Discovery = S['Discovery']

export type DiscoveriesResponse = S['DiscoveriesResponse']

export type SimilarResponse = S['SimilarResponse']

export type WordRef = S['WordRef']

export type SharedLemma = S['SharedLemma']

export type ExplainResponse = S['ExplainResponse']

export type LemmaForm = S['LemmaForm']

export type Pair = S['Pair']

export type CompareResponse = S['CompareResponse']

export type SearchHit = S['SearchHit']

export type SearchResponse = S['SearchResponse']

export type ResolveResponse = S['ResolveResponse']

export type LemmaStat = S['LemmaStat']

export type LemmaLookup = S['LemmaLookup']

export type WordDetail = S['WordDetail']

/** A content lemma's root family (DESIGN.md §16.38), when the family has other words */
export type RootRef = S['RootRef']

export type BookCount = S['BookCount']

/** An SDBH semantic domain (DESIGN.md §16.22); counts include its subdomains. */
export type DomainInfo = S['DomainInfo']

export type DomainHit = S['DomainHit']

export type DomainResponse = S['DomainResponse']

export type DomainShare = S['DomainShare']

export type UnitDomains = S['UnitDomains']

export type ConcordanceHit = S['ConcordanceHit']

export type ConcordanceResponse = S['ConcordanceResponse']

export type StructureScore = S['StructureScore']

export type Echo = S['Echo']

export type StructureBasis = S['StructureBasis']

export type Leitwort = S['Leitwort']

export type StructureResponse = S['StructureResponse']

export type RootLeitwort = S['RootLeitwort']

export type StructureSort = 'semantic_chiasm' | 'lexical_chiasm' | 'semantic_inclusio' | 'lexical_inclusio'

export type StructureRank = S['StructureRank']

/** Multiples-of-m check of Leitwort counts: m -> observed vs count-matched expectation. */
export type LeitwortNumbers = {
  leitworte: number
  lemma_counts: number
  [m: string]: number | { multiples: number; expected: number; share: number | null; p: number }
}

export type StructureRankingResponse = Omit<S['StructureRankingResponse'], 'leitwort_numbers'> & {
  leitwort_numbers: LeitwortNumbers | null
}

export type MapPoint = S['MapPoint']

export type MapCluster = S['MapCluster']

export type MapResponse = S['MapResponse']

export type AffinityCell = S['AffinityCell']

export type AffinityResponse = S['AffinityResponse']

export type AffinityPair = S['AffinityPair']

export type StyloPoint = S['StyloPoint']

export type StyloAxis = S['StyloAxis']

export type StyloDelta = S['StyloDelta']

export type StylometryResponse = S['StylometryResponse']

export type StyloFeature = S['StyloFeature']

export type BookStyle = S['BookStyle']

export type Meta = Omit<S['Meta'], 'runtime'> & {
  runtime: Record<string, unknown> & { encoder_ready?: boolean; encoder_error?: string | null; startup_s?: number }
}

export type SequenceSummary = S['SequenceSummary']

export type SequenceDirection = 'forward' | 'reverse' | 'mixed'

export type BookSpan = S['BookSpan']

/** Every chain at once, for the arc diagram across the canon */
export type SequenceArcsResponse = S['SequenceArcsResponse']

export type SequencesResponse = S['SequencesResponse']

export type DiffOp = 'spelling' | 'form' | 'substitution' | 'omitted' | 'added' | 'moved'

export type LadderRow = S['LadderRow']

export type ChangeExample = S['ChangeExample']

export type ChangeGroup = S['ChangeGroup']

export type ChangesResponse = S['ChangesResponse']

export type SequenceDetail = S['SequenceDetail']

export type VerseHalves = S['VerseHalves']

/** A word pair that types a parallel verse: antonyms, synonyms or two lemmas in one domain. */
export type RelationPair = S['RelationPair']

export type UnitParallelism = S['UnitParallelism']

export type ParallelUnit = S['ParallelUnit']

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

export type ParallelBook = S['ParallelBook']

export type ParallelismResponse = Omit<S['ParallelismResponse'], 'typing'> & {
  typing: ParallelTyping | null
}

export type WordplayPair = S['WordplayPair']

export type WordplayResponse = S['WordplayResponse']

export type EntityKind = 'person' | 'place' | 'mixed' | 'unclear'

export type Entity = S['Entity']

export type EntitiesResponse = S['EntitiesResponse']

export type EntityPartner = S['EntityPartner']

export type EntityDetail = S['EntityDetail']

// The gazetteer (`/places`, `sites` of `/entities/{lemma}`, DESIGN.md §16.56).
export type PlaceKind = 'town' | 'region' | 'landform' | 'water'
export type NameKind = 'person' | 'people' | 'location' | 'landform' | 'water'
export type PlaceSite = S['PlaceSite']
export type PlacesResponse = Omit<S['PlacesResponse'], 'meta'> & { meta: PlacesMeta & Record<string, unknown> }
export interface PlacesMeta {
  places?: number
  located?: number
  hand_check?: { site?: [number, number]; low_score?: number }
}
export type MapShape = S['MapShape']
export type BasemapResponse = S['BasemapResponse']
export type PlaceDetail = S['PlaceDetail']
export type PlacePartner = S['PlacePartner']
export type PlaceVerse = S['PlaceVerse']
export type PlaceVersesResponse = S['PlaceVersesResponse']
export type ReaderPlace = S['ReaderPlace']

// The place lists against shuffles (`/place-lists`, `/place-districts/{key}`, DESIGN.md §16.58).
export type PlaceListKind = 'itinerary' | 'boundary' | 'towns' | 'nations'
export type NullHistogram = S['NullHistogram']
export type PlaceListTest = S['PlaceListTest']
export type PlaceList = S['PlaceList']
export type DistrictTest = S['DistrictTest']
export type DistrictRow = S['DistrictRow']
export type District = S['District']
export type DistrictGrouping = S['DistrictGrouping']
export interface PlaceListsMeta {
  shuffles?: number
  alpha?: number
  sure_score?: number
  min_places?: number
  order?: { all?: { n: number; held: number }; sure?: { n: number; held: number } }
}
export type PlaceListsResponse = Omit<S['PlaceListsResponse'], 'meta'> & { meta: PlaceListsMeta & Record<string, unknown> }
export type PlaceListStep = S['PlaceListStep']
export type PlaceListDetail = S['PlaceListDetail']
export type DistrictTown = S['DistrictTown']
export type DistrictDetail = S['DistrictDetail']

export type SeamFeature = S['SeamFeature']

export type Seam = S['Seam']

export type CurvePoint = S['CurvePoint']

export type SeamsResponse = S['SeamsResponse']

export type VerseDiff = S['VerseDiff']

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

/** Newer encoders against the model in use (§16.48). */
export type EncoderEval = {
  evaluated_at?: string
  split?: string
  metric: string
  baseline: string
  /** list (semantic | fused) -> gold -> mean metric of the model in use */
  baseline_scores: Record<string, Record<string, number>>
  /** the zero-shot system already built, compared with the zero-shot candidates */
  reference: string
  reference_scores: Record<string, Record<string, number>>
  /** gold -> dev queries */
  queries: Record<string, number>
  /** supervision-exp's reseeded retrain, and the gain it sets as the bar */
  noise: string
  noise_bar: number
  results: Record<
    string,
    {
      kind: 'trained' | 'zero_shot'
      /** the base model trained, or the embedder used as it is */
      model: string
      prompt?: string | null
      dim: number
      best_epoch?: number | null
      peak_vram_gb?: number | null
      /** list -> gold -> mean metric */
      scores: Record<string, Record<string, number>>
      /** gold -> list -> gain over the baseline */
      gains: Record<string, Record<string, Gain>>
      /** zero-shot only: gold -> semantic gain over the reference */
      vs_reference?: Record<string, Gain>
      adopt: boolean
    }
  >
  chosen: string | null
}

/** One third-list family for a unit type (`bsim unit-exp`, §16.50). */
export type UnitFamilyEval = {
  /** list variant -> its scores alone (gold -> mean) and how many units have one */
  alone: Record<string, { scores: Record<string, number>; units_with_list: number }>
  /** member (variant, weight) -> gold -> mean */
  members: Record<string, Record<string, number>>
  selected: string
  /** gold -> the selected member's gain over the fused list */
  gains: Record<string, Gain>
  cross_fitted_choices: string[]
  cross_fitted_gain: Gain
  adopt: boolean
}

export type UnitListEval = {
  evaluated_at?: string
  split?: string
  metric: string
  baseline: string
  /** unit type -> its baseline, queries, families and the family chosen (or null) */
  unit_types: Record<
    string,
    {
      baseline_scores: Record<string, number>
      queries: Record<string, number>
      families: Record<string, UnitFamilyEval>
      chosen: string | null
    }
  >
}

export type EvalResponse = Omit<S['EvalResponse'], 'splits' | 'openbible' | 'etcbc' | 'supervision' | 'encoders' | 'units'> & {
  splits: Record<string, EvalSplit>
  openbible: OpenBibleEval | null
  etcbc: EtcbcEval | null
  supervision: SupervisionEval | null
  encoders: EncoderEval | null
  units: UnitListEval | null
}

export type AcrosticLine = S['AcrosticLine']

export type Acrostic = S['Acrostic']

export type AcrosticsResponse = S['AcrosticsResponse']

export type RewriteOp = 'substitution' | 'omitted' | 'added'

export type Rewrite = S['Rewrite']

export type RewriteProfile = S['RewriteProfile']

export type RewritesResponse = S['RewritesResponse']

export type NetworkNode = S['NetworkNode']

export type NetworkCommunity = S['NetworkCommunity']

export type NetworkResponse = S['NetworkResponse']

export type CommunityResponse = S['CommunityResponse']

export type UnitNetwork = S['UnitNetwork']

export type WordPair = S['WordPair']

export type WordPairsResponse = S['WordPairsResponse']

export type Alliteration = S['Alliteration']

export type AlliterationResponse = S['AlliterationResponse']

export type Rhyme = S['Rhyme']

export type RhymesResponse = S['RhymesResponse']

export type TypeScene = S['TypeScene']

export type TypeScenesResponse = S['TypeScenesResponse']

/** How much a lemma's senses and uses depend on the corpus group (DESIGN.md §16.23). */
export type LemmaShift = S['LemmaShift']

export type SenseExample = S['SenseExample']

export type LemmaSense = S['LemmaSense']

export type LemmaSensesResponse = S['LemmaSensesResponse']

export type ShiftsResponse = S['ShiftsResponse']

/** A chapter's Late Biblical Hebrew profile (DESIGN.md §16.24). */
export type DatingChapter = S['DatingChapter']

export type DatingBook = S['DatingBook']

export type SynopticExample = S['SynopticExample']

export type DatingResponse = Omit<S['DatingResponse'], 'synoptic'> & {
  synoptic: Record<string, number | null>
}

// --- your labels (DESIGN.md §16.25) ---

export type LabelValue = 'real' | 'not' | 'unsure'

export type LabelIn = S['LabelIn']

export type Label = S['Label']

export type LabelsResponse = S['LabelsResponse']

export type LabelSeparation = S['LabelSeparation']

export type LabelsEval = S['LabelsEval']

// --- BHSA syntax: clauses, speakers, who speaks where (DESIGN.md §16.26) ---

export type ClauseSegment = S['ClauseSegment']

export type SpeakerSource = 'explicit' | 'carried' | 'enclosing'
/** how the addressee was found (DESIGN.md §16.44) */
export type AddresseeSource = 'explicit' | 'vocative' | 'pronoun' | 'turn'

export type ClauseInfo = S['ClauseInfo']

export type VerseSyntax = S['VerseSyntax']

export type SyntaxNeighbor = S['SyntaxNeighbor']

export type UnitSyntax = S['UnitSyntax']

export type SpeakerTarget = S['SpeakerTarget']

export type SpeakerInfo = S['SpeakerInfo']

export interface SpeechShares {
  narration: number
  speech: number
  discourse: number
  divine: number
  attributed: number
  n_words: number
}

export type SpeechBook = S['SpeechBook']

export type SpeechChapter = S['SpeechChapter']

export type SpeechResponse = S['SpeechResponse']

export type SpeechBookResponse = S['SpeechBookResponse']

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

export type DossierEntry = S['DossierEntry']

export type Dossier = S['Dossier']

// --- speaker voices (DESIGN.md §16.28) ---

export type VoiceSpeaker = S['VoiceSpeaker']

export type VoicePair = S['VoicePair']

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

export type VoicesResponse = Omit<S['VoicesResponse'], 'meta'> & {
  meta: VoicesMeta & Record<string, unknown>
}

export type VoiceFeature = S['VoiceFeature']

export type VoiceChapter = S['VoiceChapter']

export type VoiceDetail = S['VoiceDetail']

// --- who borrowed (DESIGN.md §16.27) ---

export type BorrowDirection = 'a_to_b' | 'b_to_a' | 'unclear'

export type SignCheck = S['SignCheck']

/** A cross-book parallel; A is the side earlier in the canon, a sign > 0 says B looks later. */
export type BorrowingSequence = S['BorrowingSequence']

export type BorrowingBookPair = S['BorrowingBookPair']

export type BorrowingResponse = S['BorrowingResponse']

// --- where the text turns and where it is divided (DESIGN.md §16.29) ---

export type SegmentKind = 'turn' | 'cut' | 'quiet'
export type Paragraph = 'pe' | 'samekh'

/** A book's top-K gaps as a segmentation against its MAM breaks or its chapters */
export type SegmentBook = S['SegmentBook']

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

export type SegmentsResponse = Omit<S['SegmentsResponse'], 'meta'> & {
  meta: SegmentsMeta & Record<string, unknown>
}

/** A gap between two verses (`verse_id` = the verse after it) */
export type SegmentGap = S['SegmentGap']

export type SegmentGapsResponse = S['SegmentGapsResponse']

export type SegmentPoint = S['SegmentPoint']

export type SegmentCurve = S['SegmentCurve']

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

export type KqBook = S['KqBook']

export type KqLetter = S['KqLetter']

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

export type KetivResponse = Omit<S['KetivResponse'], 'meta'> & {
  meta: KetivMeta & Record<string, unknown>
}

export type KqPair = S['KqPair']

export type KqPairsResponse = S['KqPairsResponse']

// --- verses that say they quote or fulfil another (DESIGN.md §16.31) ---

export type CitationFamily = 'written' | 'word' | 'command'

export type CitationBook = S['CitationBook']

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

export type CitationsResponse = Omit<S['CitationsResponse'], 'meta'> & {
  meta: CitationsMeta & Record<string, unknown>
}

export type CitationCandidate = S['CitationCandidate']

export type Citation = S['Citation']

export type CitationListResponse = S['CitationListResponse']

// --- rare words two passages share over a few verses (DESIGN.md §16.32) ---

export type AllusionLemma = S['AllusionLemma']

export type Allusion = S['Allusion']

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

export type AllusionsResponse = Omit<S['AllusionsResponse'], 'meta'> & {
  meta: AllusionsMeta & Record<string, unknown>
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
  | 'ciphers_known'
  | 'ciphers_jeremiah'
  | 'ciphers_elsewhere'
  | 'ciphers_albam'
  | 'masorah_letter'
  | 'masorah_words'
  | 'masorah_verse'
  | 'masorah_books'
  | 'gematria_links'
  | 'gematria_measures'
  | 'gematria_genesis'
  | 'place_lists_order'
  | 'place_lists_districts'

export type Finding = S['Finding']

export type FindingsResponse = S['FindingsResponse']

// --- a direction on the cross-book echoes (DESIGN.md §16.36) ---

export type EchoBasis = 'cited' | 'borrowed' | 'language' | 'conflict' | 'none'

export type EchoBook = S['EchoBook']

export type EchoChapter = S['EchoChapter']

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

export type EchoesResponse = Omit<S['EchoesResponse'], 'meta'> & {
  meta: EchoesMeta & Record<string, unknown>
}

/** A cross-book chapter pair; a is the earlier in the canon */
export type EchoEdge = S['EchoEdge']

export type EchoListResponse = S['EchoListResponse']

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

export type MirrorsResponse = Omit<S['MirrorsResponse'], 'meta'> & {
  meta: MirrorsMeta & Record<string, unknown>
}

export type MirrorVerse = S['MirrorVerse']

export type MirrorVersesResponse = S['MirrorVersesResponse']

export type MirrorClause = S['MirrorClause']

export type MirrorClausesResponse = S['MirrorClausesResponse']

// --- stresses per line and the falling lament line (DESIGN.md §16.37) ---

export type MeterGroup = 'test' | 'control' | 'pool' | 'poetic' | 'prose'

export type MeterChapter = S['MeterChapter']

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

export type MeterResponse = Omit<S['MeterResponse'], 'meta'> & {
  meta: MeterMeta & Record<string, unknown>
}

export type MeterLine = S['MeterLine']

export type MeterVerse = S['MeterVerse']

export type UnitMeter = S['UnitMeter']

// --- root families (DESIGN.md §16.38) ---

export type RootPairKind = 'cognate' | 'other' | 'inf_abs'

export type RootBook = S['RootBook']

export type RootKnown = S['RootKnown']

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

export type RootsResponse = Omit<S['RootsResponse'], 'meta'> & {
  meta: RootsMeta & Record<string, unknown>
}

export type RootPair = S['RootPair']

export type RootPairsResponse = S['RootPairsResponse']

export type HiddenRoot = S['HiddenRoot']

export type HiddenRootsResponse = S['HiddenRootsResponse']

export type RootFamily = S['RootFamily']

// The layered reader (`/reader/{unit}`, DESIGN.md §16.39): word-level layers keyed by display token.
export type ReaderSpeaker = S['ReaderSpeaker']
export type ReaderWordplay = S['ReaderWordplay']
export type ReaderKetiv = S['ReaderKetiv']
export type ReaderGap = S['ReaderGap']
export type ReaderRefrain = S['ReaderRefrain']
export type ReaderVerse = S['ReaderVerse']
export type ReaderResponse = S['ReaderResponse']

// The Pentateuch's sources (`/pentateuch`, DESIGN.md §16.43): an unsupervised P / non-P split.
export type ReaderSource = S['ReaderSource']
export type SourceWord = S['SourceWord']
export type SourceSynonym = S['SourceSynonym']
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
export type PentateuchResponse = Omit<S['PentateuchResponse'], 'meta'> & {
  meta: PentateuchMeta & Record<string, unknown>
}
export type SourceChapter = S['SourceChapter']
export type PentateuchChaptersResponse = S['PentateuchChaptersResponse']

// Who speaks to whom (`/dialogue`, DESIGN.md §16.44).
export type VerseLabel = S['VerseLabel']
export type DialogueParty = S['DialogueParty']
export type DialogueBook = S['DialogueBook']
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
export type DialogueResponse = Omit<S['DialogueResponse'], 'meta'> & {
  meta: DialogueMeta & Record<string, unknown>
}
export type DialoguePair = S['DialoguePair']
export type DialogueBookResponse = S['DialogueBookResponse']
export type DialogueExchange = S['DialogueExchange']
export type DialogueExchangesResponse = S['DialogueExchangesResponse']

// Your notebook (`/notebook`, DESIGN.md §16.47): units kept with notes, and collections of them.
export type NotebookEntry = S['NotebookEntry']
export type NotebookCollection = S['NotebookCollection']
export type NotebookResponse = S['NotebookResponse']
export type NoteIn = S['NoteIn']
export type CollectionIn = S['CollectionIn']

// Pattern search (`/patterns`, DESIGN.md §16.46).
export type PatternErrorCode =
  | 'empty'
  | 'expected_pattern'
  | 'unclosed'
  | 'bad_condition'
  | 'unknown_key'
  | 'bad_value'
  | 'unknown_value'
  | 'bad_gap'
  | 'too_many'
  | 'variable'
  | 'too_broad'
export type PatternProblem = S['PatternProblem']
export type PatternMatch = S['PatternMatch']
export type PatternVerse = S['PatternVerse']
export type PatternBook = S['PatternBook']
export type PatternResponse = S['PatternResponse']

// Letter values (`/gematria`, DESIGN.md §16.53).
export type GematriaSystem = 'standard' | 'gadol' | 'ordinal' | 'katan'
export type GematriaView = 'forms' | 'lemmas' | 'verses'
export type GematriaValues = S['GematriaValues']
export type GematriaValueResponse = S['GematriaValueResponse']
export type GematriaKnown = S['GematriaKnown']
export type GematriaResponse = S['GematriaResponse']
export type GematriaForm = S['GematriaForm']
export type GematriaFormsResponse = S['GematriaFormsResponse']
export type GematriaLemma = S['GematriaLemma']
export type GematriaLemmasResponse = S['GematriaLemmasResponse']
// Do equal values link related words? (`/gematria-links`, DESIGN.md §16.59)
export type LinkMeasure = 'domains' | 'root' | 'vector'
export type LinkTest = S['LinkTest']
export type LinkLemma = S['LinkLemma']
export type LinkEquivalence = S['LinkEquivalence']
export type LinkProperty = S['LinkProperty']
export type LinkVerse = S['LinkVerse']
export interface GematriaLinksMeta {
  system?: GematriaSystem
  draws?: number
  alpha?: number
  min_count?: number
  lemmas?: number
  pairs?: number
  same_letters?: number
  tested?: number
  root_pairs?: number
}
export type GematriaLinksResponse = Omit<S['GematriaLinksResponse'], 'meta'> & { meta: GematriaLinksMeta & Record<string, unknown> }
export type GematriaPair = S['GematriaPair']
export type GematriaPairsResponse = S['GematriaPairsResponse']
export type GematriaPairSort = 'vector' | 'domains' | 'value'
export type GematriaVerse = S['GematriaVerse']
export type GematriaVersesResponse = S['GematriaVersesResponse']

// Atbash and albam (`/ciphers`, DESIGN.md §16.54).
export type CipherName = 'atbash' | 'albam'
export type CipherForm = S['CipherForm']
export type CipherValueResponse = S['CipherValueResponse']
export type CipherKnown = S['CipherKnown']
export type CipherChapter = S['CipherChapter']
export interface CipherTest {
  observed: number
  expected: number
  p: number
}
export interface CiphersMeta {
  min_letters?: number
  rare_form?: number
  shuffles?: number
  alpha?: number
  names?: number
  spans?: number
  single_spans?: number
  distinct_spans?: number
  chapters?: string[]
  n_chapters?: number
  hits?: Partial<Record<CipherName, number>>
  random_hits?: number
  known_found?: number
  tests?: { jeremiah?: CipherTest; elsewhere?: CipherTest; albam?: CipherTest; albam_elsewhere?: CipherTest }
  chapters_q?: Partial<Record<CipherName, number>>
}
export type CiphersResponse = Omit<S['CiphersResponse'], 'meta'> & {
  meta: CiphersMeta & Record<string, unknown>
}
export type CipherHit = S['CipherHit']
export type CipherHitsResponse = S['CipherHitsResponse']

// The Masorah's counts on our text (`/masorah`, DESIGN.md §16.55).
export type MasorahText = 'ketiv' | 'qere'
export type MasorahReason = 'split' | 'decalogue' | 'absent' | 'untraced' | 'witnesses'
export type MasorahMiddle = S['MasorahMiddle']
export type MasorahTotal = S['MasorahTotal']
export type MasorahBook = S['MasorahBook']
export interface MasorahCheck {
  ref: string
  n: number
  distance: number
  verses_apart: number
  holds: boolean
}
export interface MasorahCounts {
  verses: number
  words_ketiv: number
  words_qere: number
  letters_ketiv: number
  letters_qere: number
}
export interface MasorahMeta {
  tolerance?: number
  text?: MasorahText
  kq?: { pairs: number; changed: Record<MasorahText, number>; unaligned: number }
  torah?: MasorahCounts
  bible?: MasorahCounts
  checks?: {
    letter?: MasorahCheck
    word?: MasorahCheck
    verse?: MasorahCheck
    books?: { n: number; agree: number; max_diff: number; reasoned: number }
  }
}
export type MasorahResponse = Omit<S['MasorahResponse'], 'meta'> & {
  meta: MasorahMeta & Record<string, unknown>
}

// Graded numerical sayings and lists (`/forms`, DESIGN.md §16.45).
export type FormsKnownSaying = S['FormsKnownSaying']
export type FormsKnownList = S['FormsKnownList']
export type FormsBook = S['FormsBook']
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
export type FormsResponse = Omit<S['FormsResponse'], 'meta'> & {
  meta: FormsMeta & Record<string, unknown>
}
export type FormsPair = S['FormsPair']
export type FormsSaying = S['FormsSaying']
export type FormsSayingsResponse = S['FormsSayingsResponse']
export type FormsList = S['FormsList']
export type FormsListsResponse = S['FormsListsResponse']

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
export type PsalmVerse = S['PsalmVerse']
export type PsalmTurn = S['PsalmTurn']
export type Psalm = S['Psalm']
export type PsalmKnownTurn = S['PsalmKnownTurn']
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
export type PsalmsResponse = Omit<S['PsalmsResponse'], 'meta'> & {
  meta: PsalmsMeta & Record<string, unknown>
}
export type PsalmsListResponse = S['PsalmsListResponse']

// Refrains (`/refrains`, DESIGN.md §16.40): phrases that come back inside a passage.
export type RefrainVerse = S['RefrainVerse']
export type Refrain = S['Refrain']
export type RefrainKnown = S['RefrainKnown']
export type RefrainBook = S['RefrainBook']
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
export type RefrainsResponse = Omit<S['RefrainsResponse'], 'meta'> & {
  meta: RefrainsMeta & Record<string, unknown>
}
export type RefrainsListResponse = S['RefrainsListResponse']
