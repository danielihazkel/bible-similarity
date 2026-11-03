// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { TERMS } from '../i18n/pages/glossary'
import { GlossaryPage } from './GlossaryPage'
import { ToursPage } from './ToursPage'

afterEach(cleanup)

const wrap = (ui: React.ReactNode, locale: 'en' | 'he' = 'en') =>
  render(
    <LocaleProvider initial={locale}>
      <MemoryRouter>{ui}</MemoryRouter>
    </LocaleProvider>,
  )

describe('GlossaryPage', () => {
  it('lists every term with an anchor', () => {
    const { container } = wrap(<GlossaryPage />)
    expect(container.querySelectorAll('.glossary-entry')).toHaveLength(TERMS.length)
    expect(container.querySelector('#term-g2 dt')!.textContent).toBe('G² · G² (log-likelihood ratio)')
    expect(container.querySelector('#term-hapax dd')!.textContent).toBe('A word found once in the whole Bible.')
  })

  it('runs in the Hebrew interface', () => {
    wrap(<GlossaryPage />, 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('מילון מונחים')
  })
})

describe('ToursPage', () => {
  it('lists the tours with a start link each', () => {
    wrap(<ToursPage />)
    const start = screen.getByRole('link', { name: 'Start: Counting and dating' })
    expect(start.getAttribute('href')).toBe('/chronology?tour=numbers&step=1')
    expect(screen.getAllByText('· 4 steps')).toHaveLength(4)
  })
})
