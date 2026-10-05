// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { TextModeProvider } from '../context/TextMode'
import { Layout } from './Layout'

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname}</output>
}

function renderAt(path: string) {
  return render(
    <TextModeProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="*" element={<Location />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </TextModeProvider>,
  )
}

afterEach(() => {
  cleanup()
  localStorage.clear()
})

describe('Layout navigation', () => {
  it('groups pages into menus that open, navigate and close', async () => {
    const { container } = renderAt('/')
    const parallels = screen.getByRole('button', { name: /Parallels/ })
    expect(parallels.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(parallels)
    expect(parallels.getAttribute('aria-expanded')).toBe('true')
    expect(container.querySelector('.nav-group.open')?.textContent).toContain('Sequences')
    fireEvent.click(screen.getByRole('link', { name: /Sequences/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/sequences'))
    // navigation closes the menu and marks its group as the active one
    expect(parallels.getAttribute('aria-expanded')).toBe('false')
    expect(parallels.className).toContain('active')
  })

  it('closes a menu on Escape and on an outside click', () => {
    renderAt('/')
    const patterns = screen.getByRole('button', { name: /Patterns/ })
    fireEvent.click(patterns)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(patterns.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(patterns)
    fireEvent.mouseDown(document.body)
    expect(patterns.getAttribute('aria-expanded')).toBe('false')
  })

  it('toggles the narrow-screen menu', () => {
    const { container } = renderAt('/map')
    const toggle = screen.getByRole('button', { name: /Menu/ })
    expect(container.querySelector('#main-nav')?.className).not.toContain('open')
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(container.querySelector('#main-nav')?.className).toContain('open')
    expect(screen.getByRole('button', { name: /Overview/ }).className).toContain('active')
  })
})

describe('Interface language', () => {
  function renderLocalized(path: string) {
    return render(
      <LocaleProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="*" element={<h1>שלום</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </LocaleProvider>,
    )
  }

  it('is English and left to right by default', () => {
    renderLocalized('/')
    expect(screen.getByRole('link', { name: 'Browse' })).toBeTruthy()
    expect(document.documentElement.dir).toBe('ltr')
    expect(document.documentElement.lang).toBe('en')
  })

  it('switches to Hebrew, right to left, and remembers the choice', async () => {
    renderLocalized('/')
    fireEvent.click(screen.getByRole('radio', { name: 'עב' }))
    expect(screen.getByRole('link', { name: 'עיון' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /מקבילות/ })).toBeTruthy()
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('he')
    expect(localStorage.getItem('bsim.locale')).toBe('he')
    await waitFor(() => expect(document.title).toBe('שלום · מקבילות בתנ״ך'))
    cleanup()
    // a new visit starts in Hebrew
    renderLocalized('/')
    expect(screen.getByRole('link', { name: 'עיון' })).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'EN' }))
    expect(document.documentElement.dir).toBe('ltr')
    expect(localStorage.getItem('bsim.locale')).toBe('en')
  })

  it('ignores an unknown stored language', () => {
    localStorage.setItem('bsim.locale', 'fr')
    renderLocalized('/')
    expect(screen.getByRole('link', { name: 'Browse' })).toBeTruthy()
  })
})
