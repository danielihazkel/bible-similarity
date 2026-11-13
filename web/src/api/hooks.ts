import { keepPreviousData, type QueryClient, useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query'
import { hasHebrew } from '../lib/hebrew'
import { failToast } from '../lib/toast'
import { ApiError, getJson, getJsonWithTotal, sendJson, type Params } from './client'
import type {
  DetectorPrecisionResponse,
  MainlineOrder,
  MainlinePauses,
  MainlineResponse,
  ProphForm,
  LawCode,
  LawForm,
  LawList,
  LawPairs,
  LawsResponse,
  LawSynopsis,
  ProphItems,
  PropheticResponse,
  NeighbourhoodResponse,
  TheophoricResponse,
  PairNoteResponse,
  DialogueBookResponse,
  DialogueExchangesResponse,
  DialogueResponse,
  Acrostic,
  AcrosticsResponse,
  ReaderResponse,
  PentateuchChaptersResponse,
  PentateuchResponse,
  PsalmsListResponse,
  PsalmsResponse,
  QueueSide,
  RefrainsListResponse,
  RefrainsResponse,
  FormsListsResponse,
  PatternResponse,
  CheckResponse,
  DivinePairsResponse,
  DivineResponse,
  EtiologiesResponse,
  BracketOrder,
  BracketShow,
  BracketsPage,
  BracketsResponse,
  RetoldGroup,
  RetoldOrder,
  RetoldPage,
  RetoldResponse,
  HaftarotResponse,
  ChronologyResponse,
  FrameworksResponse,
  AlignResponse,
  SynopsesResponse,
  SynopsisDetail,
  BinomialsResponse,
  BinomialOccurrencesResponse,
  SumsItemsResponse,
  SumsParallelsResponse,
  SumsResponse,
  VocabularyResponse,
  ReceptionResponse,
  ReceptionVersesResponse,
  ReceptionCitationsResponse,
  WitnessesResponse,
  SourceExamples,
  SourceResponse,
  WitnessPlusesResponse,
  WitnessUnitResponse,
  WeekResponse,
  ContrastResponse,
  WorkbenchFeature,
  WorkbenchWithin,
  NotebookCollection,
  NotebookEntry,
  NotebookResponse,
  FormsResponse,
  GematriaFormsResponse,
  CipherHitsResponse,
  CipherName,
  CiphersResponse,
  CipherValueResponse,
  MasorahResponse,
  BasemapResponse,
  PlaceDetail,
  PlaceLookup,
  PlaceKind,
  DistrictDetail,
  PlaceListDetail,
  PlaceListsResponse,
  PlaceArcBookResponse,
  PlaceArcResponse,
  ElsResponse,
  PlaceLinkPairsResponse,
  PlaceLinkSort,
  PlaceLinksResponse,
  PlacesResponse,
  PlaceVersesResponse,
  PersonDetail,
  PersonLookup,
  SkeletonResponse,
  GematriaLemmasResponse,
  GematriaResponse,
  GematriaSystem,
  GematriaValueResponse,
  GematriaVersesResponse,
  GematriaLinksResponse,
  GematriaPairSort,
  GematriaPairsResponse,
  FormsSayingsResponse,
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
  LabelQueue,
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
  MeterGroup,
  MeterResponse,
  HiddenRootsResponse,
  RootFamily,
  RootPairKind,
  RootPairsResponse,
  RootsResponse,
  UnitMeter,
  MirrorsResponse,
  MirrorVersesResponse,
  MirrorClausesResponse,
  CitationListResponse,
  CitationsResponse,
  EchoBasis,
  FindingsResponse,
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
  LemmaLookup,
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
  SequenceArcsResponse,
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

/** A paged list's result with the parameters it was asked with, so the list's "export all" asks
 * the server for the same rows (`components/Pager.tsx`: `PagedList csv=`). */
export type Listed<T> = UseQueryResult<T> & { params: Params }
const listed = <T,>(res: UseQueryResult<T>, params: Params): Listed<T> => Object.assign(res, { params })

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

/** Two verses' words linked through the encoder's token vectors (§16.73). */
export const useAlign = (a: number | undefined, b: number | undefined, enabled: boolean) =>
  useQuery({
    queryKey: ['align', a, b],
    queryFn: ({ signal }) => getJson<AlignResponse>('/align', { a, b }, signal),
    enabled: enabled && a !== undefined && b !== undefined,
    retry: false,
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

/** Lemmas by Strong's number or Hebrew form, for the jump box. */
export const useLemmaLookup = (q: string) =>
  useQuery({
    queryKey: ['lemma-lookup', q],
    queryFn: ({ signal }) => getJson<LemmaLookup>('/lemmas', { q }, signal),
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
    ...forever,
  })

/** Places by a Hebrew name or a name's Strong's number, for the jump box. */
export const usePlaceLookup = (q: string) =>
  useQuery({
    queryKey: ['place-lookup', q],
    queryFn: ({ signal }) => getJson<PlaceLookup>('/places/lookup', { q }, signal),
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
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
export const useDomain = (code: string, book: number | undefined, limit: number, offset: number) => {
  const params = { book, limit, offset }
  return listed(
    useQuery({
      queryKey: ['domain', code, book, limit, offset],
      queryFn: ({ signal }) =>
        getJson<DomainResponse>(`/domain/${encodeURIComponent(code)}`, params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    { code, ...params },
  )
}

/** Lemmas ranked by how much their senses (`sense`) or uses (`use`) differ across the canon. */
export const useShifts = (by: 'sense' | 'use', maxQ: number | null, limit: number, offset: number) => {
  const params = { by, max_q: maxQ ?? undefined, limit, offset }
  return listed(
    useQuery({
      queryKey: ['shifts', by, maxQ, limit, offset],
      queryFn: ({ signal }) =>
        getJson<ShiftsResponse>('/shifts', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

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
export const useLabels = () => {
  const { personal } = useServer()
  return useQuery({ queryKey: ['labels'], queryFn: ({ signal }) => getJson<LabelsResponse>('/labels', {}, signal), enabled: personal })
}

export const useLabelsEval = () => {
  const { personal } = useServer()
  return useQuery({ queryKey: ['labels-eval'], queryFn: ({ signal }) => getJson<LabelsEval>('/labels/eval', {}, signal), enabled: personal })
}

/** The label queue (DESIGN.md §16.79): its own key, so a label does not refetch it at once (the
 * pair judged stays in view until "Next pairs" refetches). */
export const useLabelQueue = (side: QueueSide, suggested = false) => {
  const { personal } = useServer()
  return useQuery({
    queryKey: ['label-queue', side, suggested],
    queryFn: ({ signal }) => getJson<LabelQueue>('/labels/queue', { side, suggested: suggested ? 'true' : undefined }, signal),
    enabled: personal,
  })
}

/** Claude's note on a verse pair (DESIGN.md §16.88), on a personal server only. */
export const usePairNote = (a: number | undefined, b: number | undefined) => {
  const { personal } = useServer()
  return useQuery({
    queryKey: ['pair-note', Math.min(a ?? 0, b ?? 0), Math.max(a ?? 0, b ?? 0)],
    queryFn: ({ signal }) => getJson<PairNoteResponse>('/pair-note', { a, b }, signal),
    enabled: personal && a !== undefined && b !== undefined,
  })
}

/** Each audited detector's precision by Claude's reading (§16.86, D147); personal only, as the
 * notes are. Read once: the runs change by hand. */
export const useDetectorPrecision = () => {
  const { personal } = useServer()
  return useQuery({
    queryKey: ['detector-precision'],
    queryFn: ({ signal }) => getJson<DetectorPrecisionResponse>('/detector-precision', {}, signal),
    enabled: personal,
    staleTime: Infinity,
  })
}

/** A unit's parallels two steps out, as a graph (§11.1, D149): stored lists only, so a public
 * server has it too. */
export const useNeighbourhood = (unitId: string, k?: number, hops?: number) =>
  useQuery({
    queryKey: ['neighbourhood', unitId, k, hops],
    queryFn: ({ signal }) => getJson<NeighbourhoodResponse>(`/neighbourhood/${encodeURIComponent(unitId)}`, { k, hops }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

/** Names built on God's name (§16.90): their forms by book, the claim, the known answers. */
export const useTheophoric = () =>
  useQuery({
    queryKey: ['theophoric'],
    queryFn: ({ signal }) => getJson<TheophoricResponse>('/theophoric', {}, signal),
    ...forever,
  })

/** The narrative main line (§16.91): the books, the claim, the known pauses. */
export const useMainline = () =>
  useQuery({ queryKey: ['mainline'], queryFn: ({ signal }) => getJson<MainlineResponse>('/mainline', {}, signal), ...forever })

/** A page of the main line's pauses. */
export const useMainlinePauses = (q: { order: MainlineOrder; book?: number; known: boolean; unit?: string; limit: number; offset: number }) => {
  const params = { order: q.order, book: q.book, known: q.known ? 'true' : undefined, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['mainline-pauses', q],
      queryFn: ({ signal }) =>
        getJson<MainlinePauses>(
          '/mainline/pauses',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

/** The prophetic forms (§16.92): each form's findings by book, the passages named in advance. */
export const useProphetic = () =>
  useQuery({ queryKey: ['prophetic'], queryFn: ({ signal }) => getJson<PropheticResponse>('/prophetic', {}, signal), ...forever })

/** A page of the prophetic forms' findings, in canon order. */
export const usePropheticItems = (q: { form?: ProphForm; book?: number; known: boolean; unit?: string; limit: number; offset: number }) => {
  const params = { form: q.form, book: q.book, known: q.known ? 'true' : undefined, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['prophetic-items', q],
      queryFn: ({ signal }) =>
        getJson<ProphItems>(
          '/prophetic/items',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

/** The law codes (§16.93): each code's profile, the pairs named in advance. */
export const useLaws = () =>
  useQuery({ queryKey: ['laws'], queryFn: ({ signal }) => getJson<LawsResponse>('/laws', {}, signal), ...forever })

/** A page of laws in canon order. */
export const useLawList = (q: { code?: LawCode; form?: LawForm; limit: number; offset: number }) => {
  const params = { code: q.code, form: q.form, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['law-list', q],
      queryFn: ({ signal }) => getJson<LawList>('/laws/list', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

/** A page of matched law pairs. */
export const useLawPairs = (q: { order: 'score' | 'canon'; code?: LawCode; known: boolean; unit?: string; limit: number; offset: number }) => {
  const params = { order: q.order, code: q.code, known: q.known ? 'true' : undefined, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['law-pairs', q],
      queryFn: ({ signal }) =>
        getJson<LawPairs>(
          '/laws/pairs',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

/** One matched pair side by side. */
export const useLawPair = (id: number) =>
  useQuery({ queryKey: ['law-pair', id], queryFn: ({ signal }) => getJson<LawSynopsis>(`/laws/pair/${id}`, {}, signal), ...forever })

/** The key of a pair in either order. */
export const pairKey = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`)

export type LabelChange = LabelIn | { a_id: string; b_id: string; label: null }

const sendLabel = (v: LabelChange) =>
  v.label === null ? sendJson<null>('DELETE', `/labels/${encodeURIComponent(v.a_id)}/${encodeURIComponent(v.b_id)}`) : sendJson<Label>('PUT', '/labels', v)

function labelsChanged(client: QueryClient) {
  void client.invalidateQueries({ queryKey: ['labels'] })
  void client.invalidateQueries({ queryKey: ['labels-eval'] })
}

/** Label a pair (`label` given) or clear its label (`label` null). A failure is said by the
 * toaster (M177), whichever component asked. */
export function useSetLabel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: sendLabel,
    onError: (error) => void failToast(error, 'label'),
    onSettled: () => labelsChanged(client),
  })
}

/** The same change outside a component's life: an Undo, pressed after the row it was on has gone. */
export function changeLabel(client: QueryClient, v: LabelChange): Promise<void> {
  return sendLabel(v)
    .then(() => undefined)
    .catch((error) => void failToast(error, 'label'))
    .finally(() => labelsChanged(client))
}

/** Your notebook (DESIGN.md §16.47): like the labels, it changes while the viewer runs. */
export const useNotebook = () => {
  // not before the server has said what it offers (the start page asks at once): a public one
  // does not serve the notebook
  const meta = useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => getJson<Meta>('/meta', {}, signal), staleTime: Infinity })
  const personal = meta.data?.runtime?.personal !== false
  return useQuery({
    queryKey: ['notebook'],
    queryFn: ({ signal }) => getJson<NotebookResponse>('/notebook', {}, signal),
    enabled: personal && !meta.isPending,
  })
}

const enc = encodeURIComponent

/** One change to the notebook; every kind refetches it when done. */
export type NotebookChange =
  | { kind: 'keep'; unit: string; note?: string }
  | { kind: 'drop'; unit: string }
  | { kind: 'create'; name: string; description?: string; unit?: string }
  | { kind: 'rename'; id: number; name: string; description: string }
  | { kind: 'delete'; id: number }
  | { kind: 'add'; id: number; unit: string }
  | { kind: 'remove'; id: number; unit: string }

async function sendNotebook(c: NotebookChange): Promise<unknown> {
  switch (c.kind) {
    case 'keep':
      return sendJson<NotebookEntry>('PUT', `/notebook/entries/${enc(c.unit)}`, { note: c.note ?? null })
    case 'drop':
      return sendJson<null>('DELETE', `/notebook/entries/${enc(c.unit)}`)
    case 'create': {
      const made = await sendJson<NotebookCollection>('POST', '/notebook/collections', { name: c.name, description: c.description ?? '' })
      if (made && c.unit) await sendJson<NotebookEntry>('PUT', `/notebook/collections/${made.collection_id}/entries/${enc(c.unit)}`)
      return made
    }
    case 'rename':
      return sendJson<NotebookCollection>('PUT', `/notebook/collections/${c.id}`, { name: c.name, description: c.description })
    case 'delete':
      return sendJson<null>('DELETE', `/notebook/collections/${c.id}`)
    case 'add':
      return sendJson<NotebookEntry>('PUT', `/notebook/collections/${c.id}/entries/${enc(c.unit)}`)
    case 'remove':
      return sendJson<null>('DELETE', `/notebook/collections/${c.id}/entries/${enc(c.unit)}`)
  }
}

/** A name that is taken (409) is said beside the form that asked (`ChangeError`); every other
 * failure by the toaster (M177). */
const notebookFailed = (error: Error) => {
  if (!(error instanceof ApiError && error.status === 409)) failToast(error, 'notebook')
}

export function useNotebookChange() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: sendNotebook,
    onError: notebookFailed,
    onSettled: () => void client.invalidateQueries({ queryKey: ['notebook'] }),
  })
}

/** The same change outside a component's life: an Undo, or a note saved as its editor goes. */
export function changeNotebook(client: QueryClient, c: NotebookChange): Promise<void> {
  return sendNotebook(c)
    .then(() => undefined)
    .catch(notebookFailed)
    .finally(() => void client.invalidateQueries({ queryKey: ['notebook'] }))
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

export const useSegmentGaps = (q: { kind?: SegmentKind; book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { kind: q.kind, book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['segment-gaps', q],
      queryFn: ({ signal }) =>
        getJson<SegmentGapsResponse>('/segments/gaps', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useSegmentCurve = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['segment-curve', bookId],
    queryFn: ({ signal }) => getJson<SegmentCurve>(`/segments/book/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    ...forever,
  })

export const useMirrors = () =>
  useQuery({ queryKey: ['mirrors'], queryFn: ({ signal }) => getJson<MirrorsResponse>('/mirrors', {}, signal), ...forever })

export type MeterQuery = { group?: MeterGroup; book?: number; limit: number; offset: number }
export const meterParams = (q: MeterQuery): Params => ({ group: q.group, book: q.book })

export const useMeter = (q: MeterQuery) =>
  useQuery({
    queryKey: ['meter', q],
    queryFn: ({ signal }) => getJson<MeterResponse>('/meter', { ...meterParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useUnitMeter = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['unit-meter', unitId],
    queryFn: ({ signal }) => getJson<UnitMeter>(`/meter/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export const useReader = (unitId: string | undefined) =>
  useQuery({
    queryKey: ['reader', unitId],
    queryFn: ({ signal }) => getJson<ReaderResponse>(`/reader/${encodeURIComponent(unitId!)}`, {}, signal),
    enabled: !!unitId,
    ...forever,
  })

export const usePentateuch = () =>
  useQuery({
    queryKey: ['pentateuch'],
    queryFn: ({ signal }) => getJson<PentateuchResponse>('/pentateuch', {}, signal),
    ...forever,
  })

export const usePentateuchChapters = (book: number | undefined, limit: number, offset: number) =>
  useQuery({
    queryKey: ['pentateuch-chapters', book, limit, offset],
    queryFn: ({ signal }) => getJson<PentateuchChaptersResponse>('/pentateuch/chapters', { book, limit, offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useDialogue = () =>
  useQuery({
    queryKey: ['dialogue'],
    queryFn: ({ signal }) => getJson<DialogueResponse>('/dialogue', {}, signal),
    ...forever,
  })

export const useDialogueBook = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['dialogue-book', bookId],
    queryFn: ({ signal }) => getJson<DialogueBookResponse>(`/dialogue/book/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    ...forever,
  })

export const useDialogueExchanges = (
  book: number | undefined,
  party: string | undefined,
  unequal: boolean,
  limit: number,
  offset: number,
) =>
  useQuery({
    queryKey: ['dialogue-exchanges', book, party, unequal, limit, offset],
    queryFn: ({ signal }) =>
      getJson<DialogueExchangesResponse>('/dialogue/exchanges', { book, party, unequal: unequal ? 'true' : undefined, limit, offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePsalms = () =>
  useQuery({
    queryKey: ['psalms'],
    queryFn: ({ signal }) => getJson<PsalmsResponse>('/psalms', {}, signal),
    ...forever,
  })

export interface PsalmQuery {
  genre?: string
  cluster?: number
  turned: boolean
  unit?: string
  sort: 'chapter' | 'turn'
  limit: number
  offset: number
}

export const psalmParams = (q: PsalmQuery): Params => ({
  genre: q.genre,
  cluster: q.cluster,
  turned: q.turned ? 1 : undefined,
  unit: q.unit,
  sort: q.sort,
})

export const usePsalmList = (q: PsalmQuery) =>
  useQuery({
    queryKey: ['psalm-list', q],
    queryFn: ({ signal }) => getJson<PsalmsListResponse>('/psalms/list', { ...psalmParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useRefrains = () =>
  useQuery({
    queryKey: ['refrains'],
    queryFn: ({ signal }) => getJson<RefrainsResponse>('/refrains', {}, signal),
    ...forever,
  })

export interface RefrainQuery {
  book?: number
  unit?: string
  strongest: boolean
  known: boolean
  limit: number
  offset: number
}

export const refrainParams = (q: RefrainQuery): Params => ({
  book: q.book,
  unit: q.unit,
  strongest: q.strongest ? undefined : 0,
  known: q.known ? 1 : undefined,
})

export const useRefrainList = (q: RefrainQuery) =>
  useQuery({
    queryKey: ['refrain-list', q],
    queryFn: ({ signal }) =>
      getJson<RefrainsListResponse>('/refrains/list', { ...refrainParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export interface PatternQuery {
  q: string
  book?: number
  unit?: string
  limit: number
  offset: number
}

export const patternParams = (q: PatternQuery): Params => ({ q: q.q, book: q.book, unit: q.unit })

export const usePatterns = (q: PatternQuery) =>
  useQuery({
    queryKey: ['patterns', q],
    queryFn: ({ signal }) => getJson<PatternResponse>('/patterns', { ...patternParams(q), limit: q.limit, offset: q.offset }, signal),
    enabled: q.q.trim() !== '',
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useDivine = () =>
  useQuery({ queryKey: ['divine'], queryFn: ({ signal }) => getJson<DivineResponse>('/divine', {}, signal), ...forever })

export const useDivinePairs = () =>
  useQuery({ queryKey: ['divine-pairs'], queryFn: ({ signal }) => getJson<DivinePairsResponse>('/divine/pairs', {}, signal), ...forever })

export const useEtiologies = () =>
  useQuery({ queryKey: ['etiologies'], queryFn: ({ signal }) => getJson<EtiologiesResponse>('/etiologies', {}, signal), ...forever })

export const useBrackets = () =>
  useQuery({ queryKey: ['brackets'], queryFn: ({ signal }) => getJson<BracketsResponse>('/brackets', {}, signal), ...forever })

export interface BracketsQuery {
  show: BracketShow
  order: BracketOrder
  book?: number
  limit: number
  offset: number
}

export const useBracketItems = (q: BracketsQuery) => {
  const params = { show: q.show, order: q.order, book: q.book, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['bracket-items', q],
      queryFn: ({ signal }) =>
        getJson<BracketsPage>('/brackets/items', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useRetold = () =>
  useQuery({ queryKey: ['retold'], queryFn: ({ signal }) => getJson<RetoldResponse>('/retold', {}, signal), ...forever })

export interface RetoldQuery {
  group?: RetoldGroup
  known: boolean
  order: RetoldOrder
  limit: number
  offset: number
}

export const useRetoldItems = (q: RetoldQuery) => {
  const params = { group: q.group, known: q.known ? 'true' : undefined, order: q.order, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['retold-items', q],
      queryFn: ({ signal }) =>
        getJson<RetoldPage>('/retold/items', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useHaftarot = () =>
  useQuery({ queryKey: ['haftarot'], queryFn: ({ signal }) => getJson<HaftarotResponse>('/haftarot', {}, signal), ...forever })

export const useChronology = () =>
  useQuery({ queryKey: ['chronology'], queryFn: ({ signal }) => getJson<ChronologyResponse>('/chronology', {}, signal), ...forever })

export const useFrameworks = () =>
  useQuery({ queryKey: ['frameworks'], queryFn: ({ signal }) => getJson<FrameworksResponse>('/frameworks', {}, signal), ...forever })

export const useBinomials = () =>
  useQuery({ queryKey: ['binomials'], queryFn: ({ signal }) => getJson<BinomialsResponse>('/binomials', {}, signal), ...forever })

export const useBinomialOccurrences = (pair: string) =>
  useQuery({
    queryKey: ['binomial-occurrences', pair],
    queryFn: ({ signal }) => getJson<BinomialOccurrencesResponse>('/binomials/occurrences', { pair }, signal),
    ...forever,
  })

export const useSums = () =>
  useQuery({ queryKey: ['sums'], queryFn: ({ signal }) => getJson<SumsResponse>('/sums', {}, signal), ...forever })

export const useSumsItems = (key: string) =>
  useQuery({
    queryKey: ['sums-items', key],
    queryFn: ({ signal }) => getJson<SumsItemsResponse>('/sums/items', { key }, signal),
    ...forever,
  })

export const useReception = () =>
  useQuery({ queryKey: ['reception'], queryFn: ({ signal }) => getJson<ReceptionResponse>('/reception', {}, signal), ...forever })

export const useReceptionVerses = (corpus: string | undefined, book: number | undefined, limit: number, offset: number) => {
  const params = { corpus, book, limit, offset }
  return listed(
    useQuery({
      queryKey: ['reception-verses', corpus, book, limit, offset],
      queryFn: ({ signal }) => getJson<ReceptionVersesResponse>('/reception/verses', params, signal),
      ...forever,
      placeholderData: keepPreviousData,
    }),
    params,
  )
}

export const useReceptionCitations = (unit: string | undefined, corpus: string | undefined, limit: number, offset: number) => {
  const params = { unit: unit!, corpus, limit, offset }
  return listed(
    useQuery({
      queryKey: ['reception-citations', unit, corpus, limit, offset],
      queryFn: ({ signal }) => getJson<ReceptionCitationsResponse>('/reception/citations', params, signal),
      enabled: unit !== undefined,
      ...forever,
      placeholderData: keepPreviousData,
    }),
    params,
  )
}

export const useSourceExamples = () =>
  useQuery({ queryKey: ['source-examples'], queryFn: ({ signal }) => getJson<SourceExamples>('/source-find/examples', {}, signal), ...forever })

/** The source finder's answer for a text (a POST that only reads; cached by the text). */
export const useSourceFind = (text: string | undefined) =>
  useQuery({
    queryKey: ['source-find', text],
    queryFn: async () => (await sendJson<SourceResponse>('POST', '/source-find', { text }))!,
    enabled: text !== undefined && text.trim() !== '',
    ...forever,
    retry: false,
  })

export const useWitnesses = () =>
  useQuery({ queryKey: ['witnesses'], queryFn: ({ signal }) => getJson<WitnessesResponse>('/witnesses', {}, signal), ...forever })

export const useWitnessPluses = (kind: 'sp' | 'scroll', book: number | undefined, limit: number, offset: number) => {
  const params = { kind, book, limit, offset }
  return listed(
    useQuery({
      queryKey: ['witness-pluses', kind, book, limit, offset],
      queryFn: ({ signal }) => getJson<WitnessPlusesResponse>('/witnesses/pluses', params, signal),
      ...forever,
      placeholderData: keepPreviousData,
    }),
    params,
  )
}

export const useWitnessUnit = (unit: string | undefined, limit: number, offset: number) => {
  const params = { unit: unit!, limit, offset }
  return listed(
    useQuery({
      queryKey: ['witness-unit', unit, limit, offset],
      queryFn: ({ signal }) => getJson<WitnessUnitResponse>('/witnesses/unit', params, signal),
      enabled: unit !== undefined,
      ...forever,
      placeholderData: keepPreviousData,
    }),
    params,
  )
}

export const useVocabulary = () =>
  useQuery({ queryKey: ['vocabulary'], queryFn: ({ signal }) => getJson<VocabularyResponse>('/vocabulary', {}, signal), ...forever })

export const useWeek = (date: string, israel: boolean) =>
  useQuery({
    queryKey: ['week', date, israel],
    queryFn: ({ signal }) => getJson<WeekResponse>('/week', { date, israel: israel ? 'true' : undefined }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export interface SumsParallelsQuery {
  across: boolean
  oneStep?: boolean
  book?: number
  limit: number
  offset: number
}

export const useSumsParallels = (q: SumsParallelsQuery) => {
  const params = { across: q.across ? undefined : 'false', one_step: q.oneStep === undefined ? undefined : String(q.oneStep), book: q.book, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['sums-parallels', q],
      queryFn: ({ signal }) =>
        getJson<SumsParallelsResponse>(
          '/sums/parallels',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export interface ContrastQuery {
  a: string
  b: string
  feature: WorkbenchFeature
}

/** Two sets contrasted value by value (§16.64); nothing until set A is written. */
export const useContrast = (q: ContrastQuery) =>
  useQuery({
    queryKey: ['workbench-contrast', q],
    queryFn: ({ signal }) => getJson<ContrastResponse>('/workbench/contrast', { a: q.a, b: q.b || undefined, feature: q.feature }, signal),
    enabled: q.a.trim() !== '',
    placeholderData: keepPreviousData,
    // a set may name a notebook collection, which changes while the server runs
    staleTime: 60_000,
  })

export interface CheckQuery {
  q: string
  set: string
  within: WorkbenchWithin
}

/** A pattern checked on a set against its shuffled surroundings (§16.64). */
export const useCheck = (q: CheckQuery) =>
  useQuery({
    queryKey: ['workbench-check', q],
    queryFn: ({ signal }) => getJson<CheckResponse>('/workbench/check', { q: q.q, set: q.set, within: q.within }, signal),
    enabled: q.q.trim() !== '' && q.set.trim() !== '',
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  })

export const useForms = () =>
  useQuery({ queryKey: ['forms'], queryFn: ({ signal }) => getJson<FormsResponse>('/forms', {}, signal), ...forever })

export interface SayingsQuery {
  book?: number
  unit?: string
  known: boolean
  limit: number
  offset: number
}

export const sayingsParams = (q: SayingsQuery): Params => ({ book: q.book, unit: q.unit, known: q.known ? 'true' : undefined })

export const useSayings = (q: SayingsQuery) =>
  useQuery({
    queryKey: ['forms-sayings', q],
    queryFn: ({ signal }) => getJson<FormsSayingsResponse>('/forms/sayings', { ...sayingsParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export interface ListsQuery {
  book?: number
  unit?: string
  kind?: string
  limit: number
  offset: number
}

export const listsParams = (q: ListsQuery): Params => ({ book: q.book, unit: q.unit, kind: q.kind })

export const useLists = (q: ListsQuery) =>
  useQuery({
    queryKey: ['forms-lists', q],
    queryFn: ({ signal }) => getJson<FormsListsResponse>('/forms/lists', { ...listsParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useGematriaValue = (text: string | undefined) =>
  useQuery({
    queryKey: ['gematria-value', text],
    queryFn: ({ signal }) => getJson<GematriaValueResponse>('/gematria/value', { text }, signal),
    enabled: !!text,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useGematria = (value: number | undefined, system: GematriaSystem) =>
  useQuery({
    queryKey: ['gematria', value, system],
    queryFn: ({ signal }) => getJson<GematriaResponse>('/gematria', { value, system }, signal),
    enabled: value !== undefined,
    placeholderData: keepPreviousData,
    ...forever,
  })

export type GematriaQuery = { value: number; system: GematriaSystem; book?: number; limit: number; offset: number }

const gematriaList = <T,>(path: string, q: GematriaQuery | undefined) => ({
  queryKey: [path, q],
  queryFn: ({ signal }: { signal: AbortSignal }) => getJson<T>(path, { ...q }, signal),
  enabled: q !== undefined,
  placeholderData: keepPreviousData,
  ...forever,
})

export const useGematriaForms = (q: GematriaQuery | undefined) => listed(useQuery(gematriaList<GematriaFormsResponse>('/gematria/forms', q)), { ...q })
export const useGematriaLemmas = (q: GematriaQuery | undefined) => listed(useQuery(gematriaList<GematriaLemmasResponse>('/gematria/lemmas', q)), { ...q })
export const useGematriaVerses = (q: GematriaQuery | undefined) => listed(useQuery(gematriaList<GematriaVersesResponse>('/gematria/verses', q)), { ...q })

export const useGematriaLinks = () =>
  useQuery({ queryKey: ['gematria-links'], queryFn: ({ signal }) => getJson<GematriaLinksResponse>('/gematria-links', {}, signal), ...forever })

export type GematriaPairsQuery = { value?: number; sort: GematriaPairSort; sameLetters: boolean; limit: number; offset: number }

export const useGematriaPairs = (q: GematriaPairsQuery) => {
  const params = { value: q.value, sort: q.sort, same_letters: q.sameLetters ? 'true' : undefined, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['gematria-pairs', q],
      queryFn: ({ signal }) =>
        getJson<GematriaPairsResponse>('/gematria-links/pairs', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useCiphers = () =>
  useQuery({ queryKey: ['ciphers'], queryFn: ({ signal }) => getJson<CiphersResponse>('/ciphers', {}, signal), ...forever })

export type CipherHitsQuery = { cipher?: CipherName; book?: number; unit?: string; known: boolean; limit: number; offset: number }

export const useCipherHits = (q: CipherHitsQuery) => {
  const params = { cipher: q.cipher, book: q.book, unit: q.unit, known: q.known ? 'true' : undefined, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['cipher-hits', q],
      queryFn: ({ signal }) =>
        getJson<CipherHitsResponse>('/ciphers/hits', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useCipherValue = (text: string | undefined) =>
  useQuery({
    queryKey: ['cipher-value', text],
    queryFn: ({ signal }) => getJson<CipherValueResponse>('/ciphers/value', { text }, signal),
    enabled: !!text,
    ...forever,
  })

export const useBasemap = () =>
  useQuery({ queryKey: ['basemap'], queryFn: ({ signal }) => getJson<BasemapResponse>('/places/basemap', {}, signal), ...forever })

export type PlacesQuery = { kind?: PlaceKind; book?: number; unit?: string }

export const usePlaces = (q: PlacesQuery | undefined) =>
  useQuery({
    queryKey: ['places', q],
    queryFn: ({ signal }) => getJson<PlacesResponse>('/places', { kind: q?.kind, book: q?.book, unit: q?.unit }, signal),
    enabled: !!q,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePlace = (placeId: number | undefined) =>
  useQuery({
    queryKey: ['place', placeId],
    queryFn: ({ signal }) => getJson<PlaceDetail>(`/places/${placeId}`, {}, signal),
    enabled: placeId !== undefined,
    ...forever,
  })

export const usePlaceVerses = (placeId: number | undefined, limit: number, offset: number) =>
  listed(
    useQuery({
      queryKey: ['place-verses', placeId, limit, offset],
      queryFn: ({ signal }) => getJson<PlaceVersesResponse>(`/places/${placeId}/verses`, { limit, offset }, signal),
      enabled: placeId !== undefined,
      placeholderData: keepPreviousData,
      ...forever,
    }),
    // the export takes the place as a parameter (the list has it in its path)
    { place_id: placeId, limit, offset },
  )

export const usePlaceLists = () =>
  useQuery({ queryKey: ['place-lists'], queryFn: ({ signal }) => getJson<PlaceListsResponse>('/place-lists', {}, signal), ...forever })

export const usePlaceList = (key: string | undefined) =>
  useQuery({
    queryKey: ['place-list', key],
    queryFn: ({ signal }) => getJson<PlaceListDetail>(`/place-lists/${encodeURIComponent(key ?? '')}`, {}, signal),
    enabled: !!key,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePlaceArc = () =>
  useQuery({ queryKey: ['place-arc'], queryFn: ({ signal }) => getJson<PlaceArcResponse>('/place-arc', {}, signal), ...forever })

export const usePlaceArcBook = (bookId: number | undefined) =>
  useQuery({
    queryKey: ['place-arc', bookId],
    queryFn: ({ signal }) => getJson<PlaceArcBookResponse>(`/place-arc/${bookId}`, {}, signal),
    enabled: bookId !== undefined,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePlaceLinks = () =>
  useQuery({ queryKey: ['place-links'], queryFn: ({ signal }) => getJson<PlaceLinksResponse>('/place-links', {}, signal), ...forever })

export const usePlaceLinkPairs = (q: { place?: number; sort: PlaceLinkSort; limit: number; offset: number }) => {
  const params = q
  return listed(
    useQuery({
      queryKey: ['place-link-pairs', q],
      queryFn: ({ signal }) => getJson<PlaceLinkPairsResponse>('/place-links/pairs', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

/** The family tree, compact: every node and the link it hangs by (§16.63). */
export const useGenealogySkeleton = () =>
  useQuery({ queryKey: ['genealogy-skeleton'], queryFn: ({ signal }) => getJson<SkeletonResponse>('/genealogy/skeleton', {}, signal), ...forever })

export const useGenealogyPerson = (personId: number | undefined) =>
  useQuery({
    queryKey: ['genealogy-person', personId],
    queryFn: ({ signal }) => getJson<PersonDetail>(`/genealogy/person/${personId}`, {}, signal),
    enabled: personId !== undefined,
    ...forever,
  })

/** People by a Hebrew name, for the tree's search. */
export const usePersonLookup = (q: string) =>
  useQuery({
    queryKey: ['person-lookup', q],
    queryFn: ({ signal }) => getJson<PersonLookup>('/genealogy/lookup', { q }, signal),
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const usePlaceDistricts = (key: string | undefined) =>
  useQuery({
    queryKey: ['place-districts', key],
    queryFn: ({ signal }) => getJson<DistrictDetail>(`/place-districts/${encodeURIComponent(key ?? '')}`, {}, signal),
    enabled: !!key,
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useEls = () => useQuery({ queryKey: ['els'], queryFn: ({ signal }) => getJson<ElsResponse>('/els', {}, signal), ...forever })

export const useMasorah = () =>
  useQuery({ queryKey: ['masorah'], queryFn: ({ signal }) => getJson<MasorahResponse>('/masorah', {}, signal), ...forever })

export const useRoots = () =>
  useQuery({ queryKey: ['roots'], queryFn: ({ signal }) => getJson<RootsResponse>('/roots', {}, signal), ...forever })

export type RootPairsQuery = { kind?: RootPairKind; book?: number; unit?: string; limit: number; offset: number }
export const rootPairsParams = (q: RootPairsQuery): Params => ({ kind: q.kind, book: q.book, unit: q.unit })

export const useRootPairs = (q: RootPairsQuery) =>
  useQuery({
    queryKey: ['root-pairs', q],
    queryFn: ({ signal }) => getJson<RootPairsResponse>('/roots/pairs', { ...rootPairsParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export type HiddenRootsQuery = { book?: number; unit?: string; limit: number; offset: number }
export const hiddenRootsParams = (q: HiddenRootsQuery): Params => ({ book: q.book, unit: q.unit })

export const useHiddenRoots = (q: HiddenRootsQuery) =>
  useQuery({
    queryKey: ['hidden-roots', q],
    queryFn: ({ signal }) => getJson<HiddenRootsResponse>('/roots/hidden', { ...hiddenRootsParams(q), limit: q.limit, offset: q.offset }, signal),
    placeholderData: keepPreviousData,
    ...forever,
  })

export const useRootFamily = (root: string | undefined, q: { book?: number; limit: number; offset: number }) => {
  const params = { book: q.book, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['root', root, q],
      queryFn: ({ signal }) => getJson<RootFamily>(`/root/${encodeURIComponent(root!)}`, params, signal),
      enabled: !!root,
      placeholderData: keepPreviousData,
      ...forever,
    }),
    { root, ...params },
  )
}

const flag = (b: boolean | undefined) => (b === undefined ? undefined : String(b))

export const useMirrorVerses = (q: { book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['mirror-verses', q],
      queryFn: ({ signal }) => getJson<MirrorVersesResponse>('/mirrors/verses', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useMirrorClauses = (q: { pair?: string; mirrored?: boolean; poetic?: boolean; book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { pair: q.pair, mirrored: flag(q.mirrored), poetic: flag(q.poetic), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['mirror-clauses', q],
      queryFn: ({ signal }) =>
        getJson<MirrorClausesResponse>(
          '/mirrors/clauses',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useAllusions = (q: { known?: boolean; book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { known: q.known === undefined ? undefined : String(q.known), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['allusions', q],
      queryFn: ({ signal }) =>
        getJson<AllusionsResponse>(
          '/allusions',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useCitations = () =>
  useQuery({ queryKey: ['citations'], queryFn: ({ signal }) => getJson<CitationsResponse>('/citations', {}, signal), ...forever })

export const useCitationList = (q: { family?: CitationFamily; resolved?: boolean; book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { family: q.family, resolved: q.resolved === undefined ? undefined : String(q.resolved), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['citation-list', q],
      queryFn: ({ signal }) =>
        getJson<CitationListResponse>(
          '/citations/list',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useFindings = () =>
  useQuery({ queryKey: ['findings'], queryFn: ({ signal }) => getJson<FindingsResponse>('/findings', {}, signal), ...forever })

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
}) => {
  const params = { basis: q.basis, directed: q.directed === undefined ? undefined : String(q.directed), backward: q.backward === undefined ? undefined : String(q.backward), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['echo-list', q],
      queryFn: ({ signal }) =>
        getJson<EchoListResponse>(
          '/echoes/list',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

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
}) => {
  const params = { cls: q.cls, grammar: q.grammar, parallel: q.parallel, euphemism: q.euphemism === undefined ? undefined : String(q.euphemism), book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['ketiv-pairs', q],
      queryFn: ({ signal }) =>
        getJson<KqPairsResponse>(
          '/ketiv/pairs',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

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

/** What this server offers (DESIGN.md §10.3): your labels and notebook, semantic search, the verse
 * vectors. A public deploy turns them off (configs/public.yaml); all on until /meta says. */
export interface ServerFeatures {
  personal: boolean
  encoder: boolean
  embeddings: boolean
}

export const useServer = (): ServerFeatures => {
  const rt = useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => getJson<Meta>('/meta', {}, signal), staleTime: Infinity }).data
    ?.runtime
  return { personal: rt?.personal !== false, encoder: rt?.encoder_on !== false, embeddings: rt?.embeddings_shape !== null }
}

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

/** Every chain matching a significance and an order, for the arcs across the canon. */
export const useSequenceArcs = (q: { maxQ?: number; direction?: SequenceDirection }) =>
  useQuery({
    queryKey: ['sequence-arcs', q],
    queryFn: ({ signal }) =>
      getJson<SequenceArcsResponse>('/sequences/arcs', { max_q: q.maxQ, direction: q.direction }, signal),
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

export const useSynopses = () =>
  useQuery({
    queryKey: ['synopses'],
    queryFn: ({ signal }) => getJson<SynopsesResponse>('/synopses', {}, signal),
    ...forever,
  })

export const useSynopsis = (id: number | undefined, base: number) =>
  useQuery({
    queryKey: ['synopsis', id, base],
    queryFn: ({ signal }) => getJson<SynopsisDetail>(`/synopses/${id}`, { base }, signal),
    enabled: id !== undefined,
    placeholderData: keepPreviousData,
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

export const useAlliteration = (q: { book?: number; unit?: string; limit: number; offset: number }) => {
  const params = { book: q.book, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['alliteration', q],
      queryFn: ({ signal }) =>
        getJson<AlliterationResponse>('/alliteration', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useRhymes = (q: { book?: number; maxQ?: number; unit?: string; limit: number; offset: number }) => {
  const params = { book: q.book, max_q: q.maxQ, unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['rhymes', q],
      queryFn: ({ signal }) =>
        getJson<RhymesResponse>('/rhymes', params, signal),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}

export const useTypeScenes = (q: {
  book?: number
  maxQ?: number
  hideTextual: boolean
  unit?: string
  limit: number
  offset: number
}) => {
  const params = { book: q.book, max_q: q.maxQ ?? 1, hide_textual: q.hideTextual ? 'true' : 'false', unit: q.unit, limit: q.limit, offset: q.offset }
  return listed(
    useQuery({
      queryKey: ['typescenes', q],
      queryFn: ({ signal }) =>
        getJson<TypeScenesResponse>(
          '/typescenes',
          params,
          signal,
        ),
      placeholderData: keepPreviousData,
      ...forever,
    }),
    params,
  )
}
