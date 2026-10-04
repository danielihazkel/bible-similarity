import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { hasHebrew } from '../lib/hebrew'
import { getJson } from './client'
import type {
  Book,
  CompareResponse,
  ConcordanceResponse,
  DiscoveriesResponse,
  Exclude,
  ExplainResponse,
  Meta,
  Mode,
  ResolveResponse,
  SearchResponse,
  SimilarResponse,
  UnitDetail,
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

export const useMeta = () =>
  useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => getJson<Meta>('/meta', {}, signal) })
