import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { hasHebrew } from '../lib/hebrew'
import { getJson, getJsonWithTotal, sendJson, type Params } from './client'
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
  DomainInfo,
  DatingChapter,
  DatingResponse,
  DomainResponse,
  LemmaSensesResponse,
  ShiftsResponse,
  EntitiesResponse,
  EvalResponse,
  Entity,
  EntityDetail,
  EntityKind,
  Exclude,
  ExplainResponse,
  Label,
  LabelIn,
  LabelsEval,
  LabelsResponse,
  BorrowingResponse,
  BorrowingSequence,
  SpeechBookResponse,
  SpeechResponse,
  VoiceDetail,
  SegmentCurve,
  KetivResponse,
  CitationFamily,
  AllusionsResponse,
  MirrorsResponse,
  MirrorVersesResponse,
  MirrorClausesResponse,
  CitationListResponse,
  CitationsResponse,
  EchoBasis,
  EchoesResponse,
  EchoListResponse,
  KqClass,
  KqGrammar,
  KqPairsResponse,
  KqParallel,
  SegmentGapsResponse,
  SegmentKind,
  SegmentsResponse,
  Dossier,
  VoicesResponse,
  UnitSyntax,
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
  UnitDomains,
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
  /** only the pairs this unit is in (the list then shows its unit type) */
  unit?: string
  limit: number
  offset: number
}

/** API parameters of `useDiscoveries` (also used by the page's full CSV export). */
export const discoveriesParams = (q: DiscoveriesQuery): Params => ({
  unit_type: q.unitType,
  mode: q.mode,
  book: q.book,
  cross_book: q.crossBook ? 'true' : undefined,
  unit: q.unit,
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

/** Every SDBH semantic domain (DESIGN.md §16.22), in tree order. */
export const useDomains = () =>
  useQuery({
    queryKey: ['domains'],
    queryFn: ({ signal }) => getJson<DomainInfo[]>('/domains', {}, signal),
    ...forever,
  })

/** The verses of a domain and its subdomains, with its place in the tree. */
export const useDomain = (code: string, book: number | undefined, limit: number, offset: number) =>
  useQuery({
    queryKey: ['domain', code, book, limit, offset],
    queryFn: ({ signal }) =>
      getJson<DomainResponse>(`/domain/${encodeURIComponent(code)}`, { book, limit, offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

/** Lemmas ranked by how much their senses (`sense`) or uses (`use`) differ across the canon. */
export const useShifts = (by: 'sense' | 'use', maxQ: number | null, limit: number, offset: number) =>
  useQuery({
    queryKey: ['shifts', by, maxQ, limit, offset],
    queryFn: ({ signal }) =>
      getJson<ShiftsResponse>('/shifts', { by, max_q: maxQ ?? undefined, limit, offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

/** One lemma's dictionary senses and contextual uses by corpus group. */
export const useLemmaSenses = (lemma: string) =>
  useQuery({
    queryKey: ['lemma-senses', lemma],
    queryFn: ({ signal }) => getJson<LemmaSensesResponse>(`/lemma/${encodeURIComponent(lemma)}/senses`, {}, signal),
    ...forever,
  })

/** Every book's Late Biblical Hebrew profile and the model's checks (DESIGN.md §16.24). */
export const useDating = () =>
  useQuery({
    queryKey: ['dating'],
    queryFn: ({ signal }) => getJson<DatingResponse>('/dating', {}, signal),
    ...forever,
  })

export const useDatingBook = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['dating-book', bookId],
    queryFn: ({ signal }) => getJson<DatingChapter[]>(`/dating/book/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    ...forever,
  })

/** The language profile of the chapter a unit starts in (null without it). */
export const useUnitDating = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-dating', unitId],
    queryFn: ({ signal }) => getJson<DatingChapter | null>(`/unit-dating/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: unitId !== undefined,
    ...forever,
  })

/** Which side of each cross-book parallel looks like the borrower (DESIGN.md §16.27). */
export const useBorrowing = (unit?: string) =>
  useQuery({
    queryKey: ['borrowing', unit],
    queryFn: ({ signal }) => getJson<BorrowingResponse>('/borrowing', { unit }, signal),
    ...forever,
  })

export const useBorrowingSequence = (seqId: number | undefined) =>
  useQuery({
    queryKey: ['borrowing-sequence', seqId],
    queryFn: ({ signal }) => getJson<BorrowingSequence | null>(`/borrowing/sequence/${seqId}`, {}, signal),
    enabled: seqId !== undefined,
    ...forever,
  })

export const useBorrowingBetween = (a: string | undefined, b: string | undefined) =>
  useQuery({
    queryKey: ['borrowing-between', a, b],
    queryFn: ({ signal }) => getJson<BorrowingSequence[]>('/borrowing/between', { a, b }, signal),
    enabled: a !== undefined && b !== undefined,
    ...forever,
  })

/** Your labelled pairs (DESIGN.md §16.25): they change while the viewer runs, unlike the DB. */
export const useLabels = () =>
  useQuery({ queryKey: ['labels'], queryFn: ({ signal }) => getJson<LabelsResponse>('/labels', {}, signal) })

export const useLabelsEval = () =>
  useQuery({ queryKey: ['labels-eval'], queryFn: ({ signal }) => getJson<LabelsEval>('/labels/eval', {}, signal) })

/** The key of a pair in either order. */
export const pairKey = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`)

/** Label a pair (`label` given) or clear its label (`label` null). */
export function useSetLabel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (v: LabelIn | { a_id: string; b_id: string; label: null }) =>
      v.label === null
        ? sendJson<null>('DELETE', `/labels/${encodeURIComponent(v.a_id)}/${encodeURIComponent(v.b_id)}`)
        : sendJson<Label>('PUT', '/labels', v),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ['labels'] })
      void client.invalidateQueries({ queryKey: ['labels-eval'] })
    },
  })
}

/** A unit's BHSA clauses and speakers; for a verse, the verses built the same way (§16.26). */
export const useUnitSyntax = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-syntax', unitId],
    queryFn: ({ signal }) => getJson<UnitSyntax>(`/syntax/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: unitId !== undefined,
    ...forever,
  })

export const useSpeech = () =>
  useQuery({ queryKey: ['speech'], queryFn: ({ signal }) => getJson<SpeechResponse>('/speech', {}, signal), ...forever })

/** What every analysis says about one unit (`/dossier`). */
export const useDossier = (unitId: string) =>
  useQuery({
    queryKey: ['dossier', unitId],
    queryFn: ({ signal }) => getJson<Dossier>(`/dossier/${encodeURIComponent(unitId)}`, {}, signal),
    staleTime: 60_000,
  })

export const useVoices = () =>
  useQuery({ queryKey: ['voices'], queryFn: ({ signal }) => getJson<VoicesResponse>('/voices', {}, signal), ...forever })

export const useVoice = (key: string | undefined) =>
  useQuery({
    queryKey: ['voice', key],
    queryFn: ({ signal }) => getJson<VoiceDetail>(`/voices/${encodeURIComponent(key ?? '')}`, {}, signal),
    enabled: key !== undefined,
    ...forever,
  })

export const useSegments = () =>
  useQuery({ queryKey: ['segments'], queryFn: ({ signal }) => getJson<SegmentsResponse>('/segments', {}, signal), ...forever })

export const useSegmentGaps = (q: { kind?: SegmentKind; book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['segment-gaps', q],
    queryFn: ({ signal }) =>
      getJson<SegmentGapsResponse>('/segments/gaps', { kind: q.kind, book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useSegmentCurve = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['segment-curve', bookId],
    queryFn: ({ signal }) => getJson<SegmentCurve>(`/segments/book/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    ...forever,
  })

export const useMirrors = () =>
  useQuery({ queryKey: ['mirrors'], queryFn: ({ signal }) => getJson<MirrorsResponse>('/mirrors', {}, signal), ...forever })

const flag = (b: boolean | undefined) => (b === undefined ? undefined : String(b))

export const useMirrorVerses = (q: { book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['mirror-verses', q],
    queryFn: ({ signal }) => getJson<MirrorVersesResponse>('/mirrors/verses', { book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useMirrorClauses = (q: { pair?: string; mirrored?: boolean; poetic?: boolean; book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['mirror-clauses', q],
    queryFn: ({ signal }) =>
      getJson<MirrorClausesResponse>(
        '/mirrors/clauses',
        { pair: q.pair, mirrored: flag(q.mirrored), poetic: flag(q.poetic), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useAllusions = (q: { known?: boolean; book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['allusions', q],
    queryFn: ({ signal }) =>
      getJson<AllusionsResponse>(
        '/allusions',
        { known: q.known === undefined ? undefined : String(q.known), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useCitations = () =>
  useQuery({ queryKey: ['citations'], queryFn: ({ signal }) => getJson<CitationsResponse>('/citations', {}, signal), ...forever })

export const useCitationList = (q: { family?: CitationFamily; resolved?: boolean; book?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['citation-list', q],
    queryFn: ({ signal }) =>
      getJson<CitationListResponse>(
        '/citations/list',
        {
          family: q.family,
          resolved: q.resolved === undefined ? undefined : String(q.resolved),
          book: q.book,
          unit: q.unit,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useEchoes = () =>
  useQuery({ queryKey: ['echoes'], queryFn: ({ signal }) => getJson<EchoesResponse>('/echoes', {}, signal), ...forever })

export const useEchoList = (q: {
  basis?: EchoBasis
  directed?: boolean
  backward?: boolean
  book?: number
  unit?: string
  limit: number
  offset: number
}) =>
  useQuery({
    queryKey: ['echo-list', q],
    queryFn: ({ signal }) =>
      getJson<EchoListResponse>(
        '/echoes/list',
        {
          basis: q.basis,
          directed: q.directed === undefined ? undefined : String(q.directed),
          backward: q.backward === undefined ? undefined : String(q.backward),
          book: q.book,
          unit: q.unit,
          limit: q.limit,
          offset: q.offset,
        },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useKetiv = () =>
  useQuery({ queryKey: ['ketiv'], queryFn: ({ signal }) => getJson<KetivResponse>('/ketiv', {}, signal), ...forever })

export const useKqPairs = (q: {
  cls?: KqClass
  grammar?: KqGrammar
  parallel?: KqParallel
  euphemism?: boolean
  book?: number
  unit?: string
  limit: number
  offset: number
}) =>
  useQuery({
    queryKey: ['ketiv-pairs', q],
    queryFn: ({ signal }) =>
      getJson<KqPairsResponse>(
        '/ketiv/pairs',
        { cls: q.cls, grammar: q.grammar, parallel: q.parallel, euphemism: q.euphemism === undefined ? undefined : String(q.euphemism), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset },
        signal,
      ),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useSpeechBook = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['speech-book', bookId],
    queryFn: ({ signal }) => getJson<SpeechBookResponse>(`/speech/book/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    ...forever,
  })

/** The semantic domains a unit uses more than the corpus. */
export const useUnitDomains = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-domains', unitId],
    queryFn: ({ signal }) => getJson<UnitDomains>(`/unit-domains/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: unitId !== undefined,
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
  /** only phrases with a side in this unit */
  unit?: string
  limit: number
  offset: number
}

/** API parameters of `usePhrases` (also used by the page's full CSV export). */
export const phrasesParams = (q: PhrasesQuery): Params => ({
  book: q.book,
  cross_book: q.crossBook ? 'true' : undefined,
  min_tokens: q.minTokens,
  max_spread: q.maxSpread,
  unit: q.unit,
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
  /** only verse pairs with a side in this unit */
  unit?: string
  limit: number
  offset: number
}

/** API parameters of `useChanges` (also used by the page's full CSV export). */
export const changesParams = (q: ChangesQuery): Params => ({
  op: q.op,
  a_book: q.aBook,
  b_book: q.bBook,
  unit: q.unit,
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
  sort?: 'prob' | 'antithetic'
  limit: number
  offset: number
}

/** API parameters of `useParallelism` (also used by the page's full CSV export). */
export const parallelismParams = (q: ParallelismQuery): Params => ({
  unit_type: q.unitType,
  book: q.book,
  exclude_poetic: q.excludePoetic ? 'true' : undefined,
  sort: q.sort === 'antithetic' ? 'antithetic' : undefined,
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

export const useWordplay = (q: WordplayQuery, enabled = true) =>
  useQuery({
    enabled,
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

export const useRhymes = (q: { book?: number; maxQ?: number; unit?: string; limit: number; offset: number }) =>
  useQuery({
    queryKey: ['rhymes', q],
    queryFn: ({ signal }) =>
      getJson<RhymesResponse>('/rhymes', { book: q.book, max_q: q.maxQ, unit: q.unit, limit: q.limit, offset: q.offset }, signal),
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
