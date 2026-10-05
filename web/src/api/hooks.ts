import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { hasHebrew } from '../lib/hebrew'
import { getJson } from './client'
import type {
  AffinityPair,
  AffinityResponse,
  Book,
  BookStyle,
  ChangesResponse,
  CompareResponse,
  DiffOp,
  ConcordanceResponse,
  DiscoveriesResponse,
  Exclude,
  ExplainResponse,
  Meta,
  MapResponse,
  Mode,
  ParallelismResponse,
  PhrasePair,
  PhrasesResponse,
  ResolveResponse,
  SearchResponse,
  SequenceDetail,
  SequencesResponse,
  SimilarResponse,
  StructureRankingResponse,
  StructureResponse,
  StructureSort,
  StylometryResponse,
  UnitDetail,
  UnitParallelism,
  UnitSummary,
  UnitType,
  WordDetail,
} from './types'

// The DB is read-only while the server runs: everything except search is immutable.
const forever = { staleTime: Infinity, gcTime: 30 * 60_000 }

export const useBooks = () =>
  useQuery({ queryKey: ['books'], queryFn: ({ signal }) => getJson<Book[]>('/books', {}, signal), ...forever })

export const useUnits = (type: UnitType, book: number | undefined) =>
  useQuery({
    queryKey: ['units', type, book],
    queryFn: ({ signal }) => getJson<UnitSummary[]>(`/units/${type}`, { book }, signal),
    enabled: book !== undefined,
    ...forever,
  })

export const useUnit = (id: string | undefined) =>
  useQuery({
    queryKey: ['unit', id],
    queryFn: ({ signal }) => getJson<UnitDetail>(`/unit/${encodeURIComponent(id!)}`, {}, signal),
    enabled: !!id,
    ...forever,
  })

export const useSimilar = (id: string, mode: Mode, k: number, exclude: Exclude[]) =>
  useQuery({
    queryKey: ['similar', id, mode, k, exclude.join(',')],
    queryFn: ({ signal }) =>
      getJson<SimilarResponse>(`/similar/${encodeURIComponent(id)}`, { mode, k, exclude: exclude.join(',') }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useExplain = (a: number | undefined, b: number | undefined) =>
  useQuery({
    queryKey: ['explain', a, b],
    queryFn: ({ signal }) => getJson<ExplainResponse>('/explain', { a, b }, signal),
    enabled: a !== undefined && b !== undefined,
    ...forever,
  })

export const useCompare = (a: string | undefined, b: string | undefined) =>
  useQuery({
    queryKey: ['compare', a, b],
    queryFn: ({ signal }) => getJson<CompareResponse>('/compare', { a, b }, signal),
    enabled: !!a && !!b,
    ...forever,
  })

export const useSearch = (q: string, mode: Mode, k: number) =>
  useQuery({
    queryKey: ['search', q, mode, k],
    queryFn: ({ signal }) => getJson<SearchResponse>('/search', { q, mode, k }, signal),
    // the API rejects queries without Hebrew letters (e.g. an English reference)
    enabled: hasHebrew(q),
    ...forever,
  })

export interface DiscoveriesQuery {
  unitType: UnitType
  mode: Mode
  book: number | undefined
  crossBook: boolean
  limit: number
  offset: number
}

export const useDiscoveries = (q: DiscoveriesQuery) =>
  useQuery({
    queryKey: ['discoveries', q],
    queryFn: ({ signal }) =>
      getJson<DiscoveriesResponse>(
        '/discoveries',
        {
          unit_type: q.unitType,
          mode: q.mode,
          book: q.book,
          cross_book: q.crossBook ? 'true' : undefined,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useResolve = (q: string) =>
  useQuery({
    queryKey: ['resolve', q],
    queryFn: ({ signal }) => getJson<ResolveResponse>('/resolve', { q }, signal),
    enabled: q.trim().length > 0,
    ...forever,
  })

export const useWords = (verseId: number | undefined) =>
  useQuery({
    queryKey: ['words', verseId],
    queryFn: ({ signal }) => getJson<WordDetail[]>(`/words/${verseId}`, {}, signal),
    enabled: verseId !== undefined,
    ...forever,
  })

export const useLemma = (lemma: string, book: number | undefined, limit: number, offset: number) =>
  useQuery({
    queryKey: ['lemma', lemma, book, limit, offset],
    queryFn: ({ signal }) =>
      getJson<ConcordanceResponse>(`/lemma/${encodeURIComponent(lemma)}`, { book, limit, offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePhrasesOf = (verseId: number | undefined) =>
  useQuery({
    queryKey: ['phrases-of', verseId],
    queryFn: ({ signal }) => getJson<PhrasePair[]>(`/phrases/${verseId}`, {}, signal),
    enabled: verseId !== undefined,
    ...forever,
  })

export interface PhrasesQuery {
  book: number | undefined
  crossBook: boolean
  minTokens: number
  maxSpread: number | undefined
  limit: number
  offset: number
}

export const usePhrases = (q: PhrasesQuery) =>
  useQuery({
    queryKey: ['phrases', q],
    queryFn: ({ signal }) =>
      getJson<PhrasesResponse>(
        '/phrases',
        {
          book: q.book,
          cross_book: q.crossBook ? 'true' : undefined,
          min_tokens: q.minTokens,
          max_spread: q.maxSpread,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useStructure = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['structure', unitId],
    queryFn: ({ signal }) => getJson<StructureResponse>(`/structure/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export interface StructureQuery {
  unitType: UnitType
  by: StructureSort
  minVerses: number
  limit: number
  offset: number
}

export const useStructureRanking = (q: StructureQuery) =>
  useQuery({
    queryKey: ['structure-ranking', q],
    queryFn: ({ signal }) =>
      getJson<StructureRankingResponse>(
        '/structure',
        { unit_type: q.unitType, by: q.by, min_verses: q.minVerses, limit: q.limit, offset: q.offset },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useCorpusMap = (unitType: UnitType) =>
  useQuery({
    queryKey: ['map', unitType],
    queryFn: ({ signal }) => getJson<MapResponse>(`/map/${unitType}`, {}, signal),
    ...forever,
  })

export const useAffinity = () =>
  useQuery({
    queryKey: ['affinity'],
    queryFn: ({ signal }) => getJson<AffinityResponse>('/affinity', {}, signal),
    ...forever,
  })

export const useAffinityPairs = (a: number | undefined, b: number | undefined) =>
  useQuery({
    queryKey: ['affinity-pairs', a, b],
    queryFn: ({ signal }) => getJson<AffinityPair[]>(`/affinity/${a}/${b}`, {}, signal),
    enabled: a !== undefined && b !== undefined,
    ...forever,
  })

export const useStylometry = () =>
  useQuery({
    queryKey: ['stylometry'],
    queryFn: ({ signal }) => getJson<StylometryResponse>('/stylometry', {}, signal),
    ...forever,
  })

export const useBookStyle = (book: number | undefined) =>
  useQuery({
    queryKey: ['book-style', book],
    queryFn: ({ signal }) => getJson<BookStyle>(`/stylometry/book/${book}`, {}, signal),
    enabled: book !== undefined,
    ...forever,
  })

export const useMeta = () =>
  useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => getJson<Meta>('/meta', {}, signal) })

export interface SequencesQuery {
  book?: number
  crossBook?: boolean
  hideSameChapter?: boolean
  maxQ?: number
  unit?: string
  limit: number
  offset: number
}

export const useSequences = (q: SequencesQuery, enabled = true) =>
  useQuery({
    queryKey: ['sequences', q],
    queryFn: ({ signal }) =>
      getJson<SequencesResponse>(
        '/sequences',
        {
          book: q.book,
          cross_book: q.crossBook ? 'true' : undefined,
          hide_same_chapter: q.hideSameChapter ? 'true' : undefined,
          max_q: q.maxQ,
          unit: q.unit,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    enabled,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useSequence = (id: number | undefined) =>
  useQuery({
    queryKey: ['sequence', id],
    queryFn: ({ signal }) => getJson<SequenceDetail>(`/sequences/${id}`, {}, signal),
    enabled: id !== undefined,
    ...forever,
  })

export interface ChangesQuery {
  op: DiffOp
  aBook?: number
  bBook?: number
  limit: number
  offset: number
}

export const useChanges = (q: ChangesQuery) =>
  useQuery({
    queryKey: ['changes', q],
    queryFn: ({ signal }) =>
      getJson<ChangesResponse>(
        '/changes',
        { op: q.op, a_book: q.aBook, b_book: q.bBook, limit: q.limit, offset: q.offset },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useUnitParallelism = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['parallelism', unitId],
    queryFn: ({ signal }) => getJson<UnitParallelism>(`/parallelism/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export interface ParallelismQuery {
  unitType: UnitType
  book?: number
  excludePoetic: boolean
  limit: number
  offset: number
}

export const useParallelism = (q: ParallelismQuery) =>
  useQuery({
    queryKey: ['parallelism-ranking', q],
    queryFn: ({ signal }) =>
      getJson<ParallelismResponse>(
        '/parallelism',
        {
          unit_type: q.unitType,
          book: q.book,
          exclude_poetic: q.excludePoetic ? 'true' : undefined,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })
