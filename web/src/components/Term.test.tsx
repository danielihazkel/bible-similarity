// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { glossEn } from '../i18n/pages/glossary'
import { tableRows } from '../lib/csv'
import { firstUses } from '../lib/gloss'
import { Glossed, Term } from './Term'

afterEach(cleanup)

const wrap = (ui: React.ReactNode, locale: 'en' | 'he' = 'en') =>
  render(
    <LocaleProvider initial={locale}>
      <MemoryRouter>{ui}</MemoryRouter>
    </LocaleProvider>,
  )

describe('firstUses', () => {
  it('marks each term where the page first uses it', () => {
    const uses = firstUses(['rare (p 0.04) and G² 12', 'again p 0.01, q ≤ 0.05', 'p < 0.001 and nDCG@10 0.2'], glossEn.patterns)
    expect(uses.map((u) => [...u].sort())).toEqual([['g2', 'p'], ['q'], ['ndcg']])
  })

  it('does not take a p in a word for the term', () => {
    expect([...firstUses(['up 3 steps, top 10'], glossEn.patterns)[0]]).toEqual([])
  })
})

describe('Term', () => {
  it('opens its entry on focus and hover, closes on Escape, and describes the button', () => {
    wrap(<Term k="g2" />)
    const button = screen.getByRole('button', { name: 'G²' })
    const tip = document.getElementById(button.getAttribute('aria-describedby')!)!
    expect(tip.getAttribute('role')).toBe('tooltip')
    expect(tip.textContent).toContain('G² (log-likelihood ratio).')
    expect(tip.classList.contains('open')).toBe(false)
    fireEvent.focus(button)
    expect(tip.classList.contains('open')).toBe(true)
    fireEvent.keyDown(button, { key: 'Escape' })
    expect(tip.classList.contains('open')).toBe(false)
    fireEvent.mouseEnter(button.parentElement!)
    expect(tip.classList.contains('open')).toBe(true)
    fireEvent.mouseLeave(button.parentElement!)
    expect(tip.classList.contains('open')).toBe(false)
  })

  it('marks only the terms it is given, once each, in a text', () => {
    const { container } = wrap(<Glossed text="shuffled 99 times (p 0.04); p again, q 0.2" keys={new Set(['p', 'shuffle'])} />)
    expect([...container.querySelectorAll('.term-button')].map((b) => b.textContent)).toEqual(['shuffled', 'p'])
  })

  it('reads Hebrew terms in the Hebrew interface', () => {
    const { container } = wrap(<Glossed text="מול סדרים מעורבבים (p 0.04)" keys={new Set(['p', 'shuffle'])} />, 'he')
    expect([...container.querySelectorAll('.term-button')].map((b) => b.textContent)).toEqual(['מעורבבים', 'p'])
  })

  it('leaves the entry out of a table’s CSV', () => {
    const { container } = wrap(
      <table>
        <thead>
          <tr>
            <th>
              <Term k="mrr">MRR</Term>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>0.5</td>
          </tr>
        </tbody>
      </table>,
    )
    expect(tableRows(container.querySelector('table')!)).toEqual([{ MRR: '0.5' }])
  })
})
