import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { hasHebrew } from '../lib/hebrew'
import { getJson, getJsonWithTotal, type Params } from './client'
import type {
  Acrostic,
  AcrosticsResponse,
  AffinityPair,
  AlliterationResponse,
  AffinityResponse,
  Book,
  BookStyle,
  ChangesResponse,
  CommunityResponse,
  CompareResponse,
  DiffOp,
  ConcordanceResponse,
  DiscoveriesResponse,
  EntitiesResponse,
  EvalResponse,
  Entity,
  EntityDetail,
  EntityKind,
  Exclude,
  ExplainResponse,
  Meta,
  MapResponse,
  NetworkResponse,
  Mode,
  ParallelismResponse,
  PhrasePair,
  PhrasesResponse,
  ResolveResponse,
  RhymesResponse,
  RewriteOp,
  RewriteProfile,
  RewritesResponse,
  SeamsResponse,
  SearchResponse,
  SequenceDetail,
  SequenceDirection,
  SequencesResponse,
  SimilarResponse,
  StructureRankingResponse,
  StructureResponse,
  StructureSort,
  StylometryResponse,
  TypeScenesResponse,
  UnitDetail,
  UnitNetwork,
  UnitParallelism,
  UnitSummary,
  UnitType,
  VerseDiff,
  WordDetail,
  WordplayPair,
  WordplayResponse,
  WordPairsResponse,
} from './types'

// The DB is read-only while the server runs: everything except search is immutable.
const forever = { staleTime: Infinity, gcTime: 30 * 60_000 }

export const useBooks = () =>
  useQuery({ queryKey: ['books'], queryFn: ({ signal }) => getJson<Book[]>('/books', {}, signal), ...forever })

export const useUnits = (type: UnitType, book: number | undefined, chapter?: number) =>
  useQuery({
    queryKey: ['units', type, book, chapter],
    queryFn: ({ signal }) => getJson<UnitSummary[]>(`/units/${type}`, { book, chapter }, signal),
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

/** Word-level changes from verse a to verse b. */
export const useVerseDiff = (a: number | undefined, b: number | undefined, enabled = true) =>
  useQuery({
    queryKey: ['diff', a, b],
    queryFn: ({ signal }) => getJson<VerseDiff>('/diff', { a, b }, signal),
    enabled: enabled && a !== undefined && b !== undefined,
    ...forever,
  })

export const useCompare = (a: string | undefined, b: string | undefined) =>
  useQuery({
    queryKey: ['compare', a, b],
    queryFn: ({ signal }) => getJson<CompareResponse>('/compare', { a, b }, signal),
    enabled: !!a && !!b,
    ...forever,
  })

export const useSearch = (q: string, mode: Mode, k: number, enabled = true, book?: number) =>
  useQuery({
    queryKey: ['search', q, mode, k, book],
    queryFn: ({ signal }) => getJson<SearchResponse>('/search', { q, mode, k, book }, signal),
    // the API rejects queries without Hebrew letters (e.g. an English reference)
    enabled: enabled && hasHebrew(q),
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

/** API parameters of `useDiscoveries` (also used by the page's full CSV export). */
export const discoveriesParams = (q: DiscoveriesQuery): Params => ({
  unit_type: q.unitType,
  mode: q.mode,
  book: q.book,
  cross_book: q.crossBook ? 'true' : undefined,
  limit: q.limit,
  offset: q.offset,
})

export const useDiscoveries = (q: DiscoveriesQuery) =>
  useQuery({
    queryKey: ['discoveries', q],
    queryFn: ({ signal }) =>
      getJson<DiscoveriesResponse>(
        '/discoveries',
        discoveriesParams(q),
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

/** Phrase partners of a verse: the strongest `limit`, and how many there are in all. */
export const usePhrasesOf = (verseId: number | undefined, limit = 50) =>
  useQuery({
    queryKey: ['phrases-of', verseId, limit],
    queryFn: ({ signal }) => getJsonWithTotal<PhrasePair>(`/phrases/${verseId}`, { limit }, signal),
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

/** API parameters of `usePhrases` (also used by the page's full CSV export). */
export const phrasesParams = (q: PhrasesQuery): Params => ({
  book: q.book,
  cross_book: q.crossBook ? 'true' : undefined,
  min_tokens: q.minTokens,
  max_spread: q.maxSpread,
  limit: q.limit,
  offset: q.offset,
})

export const usePhrases = (q: PhrasesQuery) =>
  useQuery({
    queryKey: ['phrases', q],
    queryFn: ({ signal }) =>
      getJson<PhrasesResponse>(
        '/phrases',
        phrasesParams(q),
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

/** API parameters of `useStructureRanking` (also used by the page's full CSV export). */
export const structureParams = (q: StructureQuery): Params => ({
  unit_type: q.unitType,
  by: q.by,
  min_verses: q.minVerses,
  limit: q.limit,
  offset: q.offset,
})

export const useStructureRanking = (q: StructureQuery) =>
  useQuery({
    queryKey: ['structure-ranking', q],
    queryFn: ({ signal }) =>
      getJson<StructureRankingResponse>(
  '/structure',
  structureParams(q),
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
  direction?: SequenceDirection
  limit: number
  offset: number
}

/** API parameters of `useSequences` (also used by the page's full CSV export). */
export const sequencesParams = (q: SequencesQuery): Params => ({
  book: q.book,
  cross_book: q.crossBook ? 'true' : undefined,
  hide_same_chapter: q.hideSameChapter ? 'true' : undefined,
  max_q: q.maxQ,
  unit: q.unit,
  direction: q.direction,
  limit: q.limit,
  offset: q.offset,
})

export const useSequences = (q: SequencesQuery, enabled = true) =>
  useQuery({
    queryKey: ['sequences', q],
    queryFn: ({ signal }) =>
      getJson<SequencesResponse>(
        '/sequences',
        sequencesParams(q),
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

/** API parameters of `useChanges` (also used by the page's full CSV export). */
export const changesParams = (q: ChangesQuery): Params => ({
  op: q.op,
  a_book: q.aBook,
  b_book: q.bBook,
  limit: q.limit,
  offset: q.offset,
})

export const useChanges = (q: ChangesQuery) =>
  useQuery({
    queryKey: ['changes', q],
    queryFn: ({ signal }) =>
      getJson<ChangesResponse>(
  '/changes',
  changesParams(q),
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

/** API parameters of `useParallelism` (also used by the page's full CSV export). */
export const parallelismParams = (q: ParallelismQuery): Params => ({
  unit_type: q.unitType,
  book: q.book,
  exclude_poetic: q.excludePoetic ? 'true' : undefined,
  limit: q.limit,
  offset: q.offset,
})

export const useParallelism = (q: ParallelismQuery) =>
  useQuery({
    queryKey: ['parallelism-ranking', q],
    queryFn: ({ signal }) =>
      getJson<ParallelismResponse>(
        '/parallelism',
        parallelismParams(q),
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export interface WordplayQuery {
  book?: number
  kind?: WordplayPair['kind']
  unit?: string
  limit: number
  offset: number
}

/** API parameters of `useWordplay` (also used by the page's full CSV export). */
export const wordplayParams = (q: WordplayQuery): Params => ({
  book: q.book,
  kind: q.kind,
  unit: q.unit,
  limit: q.limit,
  offset: q.offset,
})

export const useWordplay = (q: WordplayQuery) =>
  useQuery({
    queryKey: ['wordplay', q],
    queryFn: ({ signal }) =>
      getJson<WordplayResponse>(
  '/wordplay',
  wordplayParams(q),
  signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export interface EntitiesQuery {
  kind?: EntityKind
  book?: number
  q?: string
  limit: number
  offset: number
}

/** API parameters of `useEntities` (also used by the page's full CSV export). */
export const entitiesParams = (q: EntitiesQuery): Params => ({
  kind: q.kind,
  book: q.book,
  q: q.q,
  limit: q.limit,
  offset: q.offset,
})

export const useEntities = (q: EntitiesQuery) =>
  useQuery({
    queryKey: ['entities', q],
    queryFn: ({ signal }) =>
      getJson<EntitiesResponse>(
  '/entities',
  entitiesParams(q),
  signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useEntity = (lemma: string | undefined) =>
  useQuery({
    queryKey: ['entity', lemma],
    queryFn: ({ signal }) => getJson<EntityDetail>(`/entities/${encodeURIComponent(lemma!)}`, {}, signal),
    enabled: !!lemma,
    ...forever,
  })

export const useUnitEntities = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-entities', unitId],
    queryFn: ({ signal }) => getJson<Entity[]>(`/unit-entities/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export const useSeams = (book: number | undefined) =>
  useQuery({
    queryKey: ['seams', book],
    queryFn: ({ signal }) => getJson<SeamsResponse>('/seams', { book, limit: book === undefined ? 25 : 50 }, signal),
    ...forever,
  })

const ENCODER_POLL_MS = 2000

export interface EncoderStatus {
  /** undefined while unknown */
  ready?: boolean
  /** why the encoder failed to load (polling stops) */
  error?: string
}

/** Whether the server's query encoder has loaded (polled while it is still loading). */
export const useEncoderStatus = (enabled: boolean): EncoderStatus => {
  const q = useQuery({
    queryKey: ['meta', 'encoder'],
    queryFn: ({ signal }) => getJson<Meta>('/meta', {}, signal),
    enabled,
    refetchInterval: (query) => {
      const rt = query.state.data?.runtime
      return rt?.encoder_ready || rt?.encoder_error ? false : ENCODER_POLL_MS
    },
    staleTime: 0,
  })
  const rt = q.data?.runtime
  return { ready: rt?.encoder_ready, error: rt?.encoder_error ?? undefined }
}

export const useEval = () =>
  useQuery({ queryKey: ['eval'], queryFn: ({ signal }) => getJson<EvalResponse>('/eval', {}, signal), ...forever })

export interface AcrosticsQuery {
  maxQ?: number
  book?: number
  limit: number
  offset: number
}

/** API parameters of `useAcrostics` (also used by the page's full CSV export). */
export const acrosticsParams = (q: AcrosticsQuery): Params => ({
  max_q: q.maxQ ?? 1,
  book: q.book,
  limit: q.limit,
  offset: q.offset,
})

export const useAcrostics = (q: AcrosticsQuery) =>
  useQuery({
    queryKey: ['acrostics', q],
    queryFn: ({ signal }) =>
      getJson<AcrosticsResponse>(
  '/acrostics',
  // the API's default is q <= 0.05: 'all' is sent as max_q=1
  acrosticsParams(q),
  signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useUnitAcrostic = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['acrostic', unitId],
    queryFn: ({ signal }) => getJson<Acrostic | null>(`/acrostics/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export interface RewritesQuery {
  aBook?: number
  bBook?: number
  op?: RewriteOp
  maxQ?: number
  limit: number
  offset: number
}

/** API parameters of `useRewrites` (also used by the page's full CSV export). */
export const rewritesParams = (q: RewritesQuery): Params => ({
  a_book: q.aBook,
  b_book: q.bBook,
  op: q.op,
  max_q: q.maxQ ?? 1,
  limit: q.limit,
  offset: q.offset,
})

export const useRewrites = (q: RewritesQuery) =>
  useQuery({
    queryKey: ['rewrites', q],
    queryFn: ({ signal }) =>
      getJson<RewritesResponse>(
  '/rewrites',
  rewritesParams(q),
  signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useRewriteProfiles = () =>
  useQuery({
    queryKey: ['rewrite-profiles'],
    queryFn: ({ signal }) => getJson<RewriteProfile[]>('/rewrite-profiles', {}, signal),
    ...forever,
  })

export const useNetwork = (unitType: UnitType) =>
  useQuery({
    queryKey: ['network', unitType],
    queryFn: ({ signal }) => getJson<NetworkResponse>(`/network/${unitType}`, {}, signal),
    ...forever,
  })

export const useCommunity = (unitType: UnitType, community: number | undefined) =>
  useQuery({
    queryKey: ['network', unitType, community],
    queryFn: ({ signal }) => getJson<CommunityResponse>(`/network/${unitType}/${community}`, {}, signal),
    enabled: community !== undefined,
    ...forever,
  })

export const useUnitNetwork = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-network', unitId],
    queryFn: ({ signal }) => getJson<UnitNetwork | null>(`/unit-network/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export interface WordPairsQuery {
  maxQ?: number
  lemma?: string
  limit: number
  offset: number
}

/** API parameters of `useWordPairs` (also used by the page's full CSV export). */
export const wordPairsParams = (q: WordPairsQuery): Params => ({
  max_q: q.maxQ ?? 1,
  lemma: q.lemma,
  limit: q.limit,
  offset: q.offset,
})

export const useWordPairs = (q: WordPairsQuery) =>
  useQuery({
    queryKey: ['word-pairs', q],
    queryFn: ({ signal }) =>
      getJson<WordPairsResponse>(
  '/word-pairs',
  wordPairsParams(q),
  signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useAlliteration = (q: { book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['alliteration', q],
    queryFn: ({ signal }) =>
      getJson<AlliterationResponse>('/alliteration', { book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useRhymes = (q: { book?: number; maxQ?: number; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['rhymes', q],
    queryFn: ({ signal }) =>
      getJson<RhymesResponse>('/rhymes', { book: q.book, max_q: q.maxQ, limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useTypeScenes = (q: {
  book?: number
  maxQ?: number
  hideTextual: boolean
  unit?: string
  limit: number
  offset: number
}) =>
  useQuery({
    queryKey: ['typescenes', q],
    queryFn: ({ signal }) =>
      getJson<TypeScenesResponse>(
        '/typescenes',
        {
          book: q.book,
          max_q: q.maxQ ?? 1,
          hide_textual: q.hideTextual ? 'true' : 'false',
          unit: q.unit,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })
