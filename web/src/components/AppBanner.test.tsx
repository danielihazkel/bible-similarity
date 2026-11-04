// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import { offerUpdate } from '../lib/pwa'
import { AppBanner } from './AppBanner'

function setOnline(online: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => online })
  window.dispatchEvent(new Event(online ? 'online' : 'offline'))
}

afterEach(() => {
  act(() => {
    setOnline(true)
    offerUpdate(null)
  })
  cleanup()
})

const renderBanner = (locale: 'en' | 'he' = 'en') =>
  render(
    <LocaleProvider initial={locale}>
      <AppBanner />
    </LocaleProvider>,
  )

describe('AppBanner', () => {
  it('is an empty live region while online with no new build', () => {
    renderBanner()
    expect(screen.getByRole('status').textContent).toBe('')
  })

  it('says so when the browser goes offline, and clears when it is back', () => {
    renderBanner()
    act(() => setOnline(false))
    expect(screen.getByRole('status').textContent).toMatch(/offline: the pages and answers already opened still work/)
    act(() => setOnline(true))
    expect(screen.getByRole('status').textContent).toBe('')
  })

  it('offers a waiting new build, and reloads into it', () => {
    const apply = vi.fn()
    renderBanner()
    act(() => offerUpdate(apply))
    expect(screen.getByRole('status').textContent).toContain('A new version of the viewer is ready.')
    fireEvent.click(screen.getByRole('button', { name: 'Reload' }))
    expect(apply).toHaveBeenCalledOnce()
  })

  it('speaks Hebrew', async () => {
    renderBanner('he')
    act(() => setOnline(false))
    expect((await screen.findByText(/אין חיבור לרשת/)).tagName).toBe('P')
  })
})
