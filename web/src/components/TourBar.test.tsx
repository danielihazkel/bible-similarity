// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { TOURS, tourHref } from '../lib/tours'
import { trEn } from '../i18n/pages/tours'
import { TourBar } from './TourBar'

afterEach(cleanup)

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const renderAt = (path: string, locale: 'en' | 'he' = 'en') =>
  render(
    <LocaleProvider initial={locale}>
      <MemoryRouter initialEntries={[path]}>
        <TourBar />
        <Location />
      </MemoryRouter>
    </LocaleProvider>,
  )

describe('tours', () => {
  it('give every step a caption in both languages', async () => {
    const { trHe } = await import('../i18n/pages/he/tours')
    for (const [k, routes] of Object.entries(TOURS) as [keyof typeof TOURS, string[]][]) {
      expect(trEn.tours[k].steps).toHaveLength(routes.length)
      expect(trHe.tours[k].steps).toHaveLength(routes.length)
    }
  })

  it('carry the tour on a step’s own query', () => {
    expect(tourHref('numbers', 2)).toBe('/sums?list=ezra2&tour=numbers&step=2')
    expect(tourHref('numbers', 1)).toBe('/chronology?tour=numbers&step=1')
  })
})

describe('TourBar', () => {
  it('shows nothing outside a tour', () => {
    const { container } = renderAt('/chronology')
    expect(container.querySelector('.tour-bar')).toBeNull()
    cleanup()
    expect(renderAt('/chronology?tour=nope&step=1').container.querySelector('.tour-bar')).toBeNull()
    cleanup()
    expect(renderAt('/chronology?tour=numbers&step=9').container.querySelector('.tour-bar')).toBeNull()
  })

  it('leads from step to step and out', () => {
    renderAt('/chronology?tour=numbers&step=1')
    expect(screen.getByText('Counting and dating · step 1 of 4')).toBeTruthy()
    expect(screen.getByText(/The years from Adam/)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Back' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByTestId('loc').textContent).toBe('/sums?list=ezra2&tour=numbers&step=2')
    expect(screen.getByText(/Ezra lists the families/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Leave the tour' }))
    expect(screen.getByTestId('loc').textContent).toBe('/sums?list=ezra2')
  })

  it('finishes on the tours page', () => {
    renderAt(tourHref('poetry', 4))
    fireEvent.click(screen.getByRole('button', { name: 'Finish' }))
    expect(screen.getByTestId('loc').textContent).toBe('/tours')
  })

  it('runs in the Hebrew interface', () => {
    renderAt('/chronology?tour=numbers&step=1', 'he')
    expect(screen.getByText('מנייה ותיארוך · צעד 1 מתוך 4')).toBeTruthy()
  })
})
