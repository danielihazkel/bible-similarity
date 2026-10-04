// Mirrors the pydantic response models in src/bsim/api/models.py (DESIGN.md §10).

export type Mode = 'lexical' | 'semantic' | 'fused'
export type UnitType = 'verse' | 'chapter' | 'pericope' | 'parasha'
export type Exclude = 'neighbors' | 'chapter' | 'book'

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

export interface Hit extends Breakdown {
  rank: number
  unit: UnitSummary
  verse: Verse | null
  preview: string | null
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

export interface Meta {
  build: Record<string, unknown>
  runtime: Record<string, unknown>
}
