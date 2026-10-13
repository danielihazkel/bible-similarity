// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EvalResponse } from '../api/types'
import { EvalPage } from './EvalPage'

const g = (mean: number, lo: number, hi: number) => ({ mean, lo, hi, better: 40, worse: 30, queries: 884 })
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
  etcbc: {
    split: 'dev',
    max_partners: 5,
    stats: { edges: 31742, pairs: 15618, parallels: 1973, formula_pairs: 13645 },
    gold: { etcbc_also_in_sefaria: 0.1111, etcbc_also_in_openbible: 0.1966 },
    results: { lexical: { system: 'bm25_lemma', etcbc: m(0.853), sefaria: m(0.176) } },
    bands: { '75-84': { pairs: 168, 'recall@10': 0.8988 }, '95-100': { pairs: 12, 'recall@10': 1 } },
    coverage: { pairs: 1973, in_sequence: 0.3756, in_phrase: 0.8033, in_fused_top10: 0.9437, sequence_pairs: 1317, sequence_pairs_in_etcbc: 0.5626 },
  },
  supervision: {
    split: 'dev',
    metric: 'ndcg@10',
    baseline: 'berel_sup',
    baseline_scores: { fused: { sefaria: 0.1895, openbible: 0.146, etcbc: 0.832 }, semantic: { sefaria: 0.15, openbible: 0.111, etcbc: 0.749 } },
    queries: { sefaria: 884, openbible: 2541, etcbc: 179 },
    noise: 'seed14',
    chosen: null,
    results: {
      seed14: {
        overrides: { seed: 14 },
        model: 'berel-sup-seed14',
        rows_by_source: { sefaria: 9026 },
        scores: {},
        gains: { sefaria: { fused: g(-0.002, -0.01, 0.006), semantic: g(0, -0.01, 0.01) }, openbible: { fused: g(0.001, -0.002, 0.004), semantic: g(0, -0.01, 0.01) }, etcbc: { fused: g(0, -0.01, 0.01), semantic: g(0, -0.01, 0.01) } },
        adopt: false,
      },
      openbible: {
        overrides: { extra_pairs: ['openbible'] },
        model: 'berel-sup-openbible',
        rows_by_source: { openbible: 27682, sefaria: 9026 },
        scores: {},
        gains: { sefaria: { fused: g(-0.02, -0.03, -0.01), semantic: g(0, -0.01, 0.01) }, openbible: { fused: g(0.03, 0.02, 0.04), semantic: g(0, -0.01, 0.01) }, etcbc: { fused: g(0, -0.01, 0.01), semantic: g(0, -0.01, 0.01) } },
        adopt: false,
      },
    },
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
    expect(screen.getByText(/1,973 parallels\. The 13,645 pairs among verses with more than 5 partners/)).toBeTruthy()
    expect(screen.getByText(/11.1% of them are also Sefaria links/)).toBeTruthy()
    expect(screen.getByText(/75-84 % 0.90 \(168\), 95-100 % 1.00 \(12\)/)).toBeTruthy()
    expect(screen.getByText(/94.4% are in the fused top 10, 80.3% share a phrase, 37.6% lie in a strong sequence/)).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Against ETCBC' })).toBeTruthy()
    // the encoder retrained with more supervision: each variant's gains, the rule's verdict
    const fused = screen.getByRole('region', { name: 'Fused list (lexical + semantic)' })
    expect(fused.querySelector('caption')?.textContent).toBe('Fused list (lexical + semantic) · gain over berel_sup (Sefaria 0.190, OpenBible 0.146, ETCBC 0.832)')
    const row = [...fused.querySelectorAll('tbody tr')].find((r) => r.querySelector('code')?.textContent === 'openbible')!
    expect([...row.querySelectorAll('td')].map((c) => c.textContent)).toEqual(['OpenBible 27,682 · Sefaria 9,026', '−0.020 [−0.030, −0.010]', '+0.030 [+0.020, +0.040]', '+0.000 [−0.010, +0.010]', 'no'])
    expect(row.querySelectorAll('td.on')).toHaveLength(1)
    expect(row.querySelector('td.on')?.getAttribute('title')).toBe('40 queries better, 30 worse, of 884')
    expect(screen.getByText(/No variant passed, so the model in use stays/)).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Semantic list alone' }).querySelector('th:last-child')?.textContent).toBe('ETCBC')
  })
})
