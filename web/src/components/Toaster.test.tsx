// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { LocaleProvider } from '../context/Locale'
import { clearToasts, currentToasts, dismissToast, failToast, showToast, TOAST_MS } from '../lib/toast'
import { Toaster } from './Toaster'

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  cleanup()
  clearToasts()
  vi.useRealTimers()
})

const toaster = (locale: 'en' | 'he' = 'en') =>
  render(
    <LocaleProvider initial={locale}>
      <Toaster />
    </LocaleProvider>,
  )
const say = (fn: () => void) => act(fn)
const pass = (ms: number) => act(() => void vi.advanceTimersByTime(ms))

describe('the notes of a save (M177)', () => {
  it('keeps a few notes, and a later one of the same key takes the earlier one’s place', () => {
    showToast('one', { key: 'a' })
    showToast('two')
    showToast('three', { key: 'a' })
    expect(currentToasts().map((t) => t.text)).toEqual(['two', 'three'])
    showToast('four')
    showToast('five')
    expect(currentToasts().map((t) => t.text)).toEqual(['three', 'four', 'five'])
    dismissToast(currentToasts()[0].id)
    expect(currentToasts().map((t) => t.text)).toEqual(['four', 'five'])
  })

  it('says a note in the page’s live region and takes it away after a few seconds', () => {
    toaster()
    const region = screen.getByRole('status')
    expect(region.getAttribute('aria-live')).toBe('polite')
    expect(region.textContent).toBe('') // there before any note, so that a note is read out
    say(() => void showToast('Note saved'))
    expect(region.textContent).toContain('Note saved')
    pass(TOAST_MS.plain - 50)
    expect(screen.getByText('Note saved')).toBeTruthy()
    pass(100)
    expect(screen.queryByText('Note saved')).toBeNull()
  })

  it('offers an action for longer, runs it once and goes', () => {
    toaster()
    const undo = vi.fn()
    say(() => void showToast('Label removed', { action: { label: 'Undo', run: undo } }))
    pass(TOAST_MS.plain + 500)
    fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    expect(undo).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('Label removed')).toBeNull()
    // left alone, it goes by itself and nothing is run
    say(() => void showToast('Label removed', { action: { label: 'Undo', run: undo } }))
    pass(TOAST_MS.action + 50)
    expect(screen.queryByText('Label removed')).toBeNull()
    expect(undo).toHaveBeenCalledTimes(1)
  })

  it('waits while the pointer or the focus is on the notes', () => {
    const { container } = toaster()
    say(() => void showToast('Taken out', { action: { label: 'Undo', run: () => {} } }))
    fireEvent.mouseEnter(container.querySelector('.toaster')!)
    pass(TOAST_MS.action * 3)
    expect(screen.getByText('Taken out')).toBeTruthy()
    fireEvent.mouseLeave(container.querySelector('.toaster')!)
    pass(TOAST_MS.action + 50)
    expect(screen.queryByText('Taken out')).toBeNull()
  })

  it('keeps a failure until it is closed, as an alert with the server’s answer', () => {
    toaster()
    say(() => void failToast(new ApiError(500, 'disk full')))
    pass(60_000)
    const alert = screen.getByRole('alert')
    expect(alert.textContent).toContain('Could not save: 500: disk full')
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('alert')).toBeNull()
    // Escape closes the note the focus is in
    say(() => void failToast(new Error('Failed to fetch')))
    fireEvent.keyDown(screen.getByRole('button', { name: 'Close' }), { key: 'Escape' })
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('reads in Hebrew, and says that there is no connection', () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    toaster('he')
    say(() => void failToast(new TypeError('Failed to fetch')))
    expect(screen.getByRole('alert').textContent).toContain('השמירה נכשלה: אין חיבור')
    expect(screen.getByRole('button', { name: 'סגירה' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'שמירות והסרות' })).toBeTruthy()
    vi.restoreAllMocks()
  })
})
