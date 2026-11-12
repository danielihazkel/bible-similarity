// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { TextModeProvider } from '../context/TextMode'
import { ThemeProvider } from '../context/Theme'
import type { Locale } from '../i18n'
import { applyTheme, loadTheme, shadeOf } from '../lib/theme'
import { Layout } from './Layout'

// the system's theme, as `matchMedia('(prefers-color-scheme: dark)')` reports it, and its listeners
function stubSystem(dark: boolean) {
  const listeners = new Set<() => void>()
  const q = {
    matches: dark,
    addEventListener: (_: string, f: () => void) => listeners.add(f),
    removeEventListener: (_: string, f: () => void) => listeners.delete(f),
  }
  vi.stubGlobal('matchMedia', () => q)
  return {
    set(next: boolean) {
      q.matches = next
      act(() => listeners.forEach((f) => f()))
    },
    listeners,
  }
}

function renderApp(locale: Locale = 'en') {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LocaleProvider initial={locale}>
        <TextModeProvider>
          <ThemeProvider>
            <MemoryRouter initialEntries={['/a']}>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="*" element={<h1>Page</h1>} />
                </Route>
              </Routes>
            </MemoryRouter>
          </ThemeProvider>
        </TextModeProvider>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

const html = document.documentElement

afterEach(() => {
  cleanup()
  localStorage.clear()
  html.removeAttribute('data-theme')
  vi.unstubAllGlobals()
})

describe('the theme (lib/theme)', () => {
  it('is auto by default and for an unknown stored value', () => {
    expect(loadTheme()).toBe('auto')
    localStorage.setItem('bsim.theme', 'sepia')
    expect(loadTheme()).toBe('auto')
    localStorage.setItem('bsim.theme', 'dark')
    expect(loadTheme()).toBe('dark')
  })

  it('resolves auto by the system and writes the result on <html>', () => {
    stubSystem(true)
    expect(shadeOf('auto')).toBe('dark')
    expect(shadeOf('light')).toBe('light')
    expect(applyTheme('auto')).toBe('dark')
    expect(html.getAttribute('data-theme')).toBe('dark')
    applyTheme('light')
    expect(html.getAttribute('data-theme')).toBe('light')
  })

  it('is light where the system cannot be asked', () => {
    vi.stubGlobal('matchMedia', undefined)
    expect(applyTheme('auto')).toBe('light')
  })
})

describe('DisplayMenu', () => {
  it('holds the text display, the language, the theme and the link behind one button', () => {
    stubSystem(false)
    renderApp()
    const button = screen.getByRole('button', { name: /Display/ })
    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('radiogroup')).toBeNull()
    fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('true')
    expect(button.getAttribute('aria-controls')).toBe('display-panel')
    expect(screen.getByRole('group', { name: 'Display' }).id).toBe('display-panel')
    expect(screen.getAllByRole('radiogroup').map((g) => g.getAttribute('aria-label'))).toEqual(['Text display', 'Interface language', 'Theme'])
    expect(screen.getByRole('button', { name: /Copy link/ })).toBeTruthy()
  })

  it('closes on Escape with the focus back on its button, and on a click outside it', () => {
    stubSystem(false)
    renderApp()
    const button = screen.getByRole('button', { name: /Display/ })
    fireEvent.click(button)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(button)
    fireEvent.click(button)
    fireEvent.mouseDown(screen.getByRole('radio', { name: 'Dark' })) // inside: stays open
    expect(button.getAttribute('aria-expanded')).toBe('true')
    fireEvent.mouseDown(screen.getByRole('heading', { name: 'Page' }))
    expect(button.getAttribute('aria-expanded')).toBe('false')
  })

  it('leaves the phone menu open when Escape closes it', () => {
    stubSystem(false)
    renderApp()
    const menu = screen.getByRole('button', { name: /Menu/ })
    fireEvent.click(menu)
    fireEvent.click(screen.getByRole('button', { name: /Display/ }))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.getByRole('button', { name: /Display/ }).getAttribute('aria-expanded')).toBe('false')
    expect(menu.getAttribute('aria-expanded')).toBe('true')
  })

  it('sets the theme, remembers it, and starts a new visit with it', () => {
    stubSystem(false)
    renderApp()
    expect(html.getAttribute('data-theme')).toBe('light') // auto, a light system
    fireEvent.click(screen.getByRole('button', { name: /Display/ }))
    expect(screen.getByRole('radio', { name: 'Auto' }).getAttribute('aria-checked')).toBe('true')
    fireEvent.click(screen.getByRole('radio', { name: 'Dark' }))
    expect(html.getAttribute('data-theme')).toBe('dark')
    expect(localStorage.getItem('bsim.theme')).toBe('dark')
    expect(screen.getByRole('radio', { name: 'Dark' }).getAttribute('aria-checked')).toBe('true')
    cleanup()
    html.removeAttribute('data-theme')
    renderApp()
    expect(html.getAttribute('data-theme')).toBe('dark')
  })

  it('follows the system on auto, and not once a theme is chosen', () => {
    const system = stubSystem(false)
    renderApp()
    system.set(true)
    expect(html.getAttribute('data-theme')).toBe('dark')
    system.set(false)
    expect(html.getAttribute('data-theme')).toBe('light')
    fireEvent.click(screen.getByRole('button', { name: /Display/ }))
    fireEvent.click(screen.getByRole('radio', { name: 'Light' }))
    expect(system.listeners.size).toBe(0)
    system.set(true)
    expect(html.getAttribute('data-theme')).toBe('light')
    // back on auto, the system's theme at once
    fireEvent.click(screen.getByRole('radio', { name: 'Auto' }))
    expect(html.getAttribute('data-theme')).toBe('dark')
  })

  it('copies the link to this view', async () => {
    stubSystem(false)
    const writeText = vi.fn(() => Promise.resolve())
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    renderApp()
    fireEvent.click(screen.getByRole('button', { name: /Display/ }))
    fireEvent.click(screen.getByRole('button', { name: /Copy link/ }))
    expect(writeText).toHaveBeenCalledWith(window.location.href)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Copied' })).toBeTruthy())
  })

  it('is in Hebrew in the Hebrew interface', () => {
    stubSystem(false)
    renderApp('he')
    fireEvent.click(screen.getByRole('button', { name: /תצוגה/ }))
    expect(screen.getAllByRole('radiogroup').map((g) => g.getAttribute('aria-label'))).toEqual(['תצוגת הטקסט', 'שפת הממשק', 'ערכת צבעים'])
    expect(screen.getAllByRole('radio', { name: /אוטומטי|בהיר|כהה/ })).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'העתקת קישור' })).toBeTruthy()
  })
})
