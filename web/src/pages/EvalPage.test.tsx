// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EvalResponse } from '../api/types'
import { EvalPage } from './EvalPage'

const m = (ndcg: number) => ({ 'ndcg@10': ndcg, 'mrr@10': ndcg, 'recall@1': 0.1, 'recall@5': 0.2, 'recall@10': 0.3, 'recall@50': 0.4, queries: 9 })
const RES: EvalResponse = {
  splits: {
    dev: {
      evaluated_at: '2026-10-04T19:17:04+00:00',
      gold: { verse: { queries: 884, pairs: 1204 } },
      results: { verse: { bm25_lemma: m(0.12), fused: m(0.16), berel_mean: m(0.11) } },
    },
  },
  openbible: {
    split: 'dev',
    gold: { openbible_also_in_sefaria: 0.0298 },
    results: { fused: { system: 'fused', openbible: m(0.15), sefaria: m(0.17) } },
  },
  final: { verse: { lexical: 'bm25_lemma', semantic: 'berel_sup_csls', fused: 'fused', structural: 'bm25_morph' } },
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('EvalPage', () => {
  it('ranks systems by nDCG and marks the served ones', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(RES))))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <EvalPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const table = (await screen.findByText(/884 queries, 1204 gold pairs/)).closest('table')!
    const rows = [...table.querySelectorAll('tbody tr')].map((r) => r.querySelector('code')!.textContent)
    expect(rows).toEqual(['fused', 'bm25_lemma', 'berel_mean'])
    expect(table.querySelectorAll('tr.served')).toHaveLength(2)
    expect(screen.getByText('served: lexical')).toBeTruthy()
    expect(screen.getByText(/Only 3.0% of OpenBible pairs/)).toBeTruthy()
  })
})
