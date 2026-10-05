// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { isChunkLoadError } from '../lib/chunk'
import { ErrorBoundary } from './ErrorBoundary'

function Boom({ error }: { error: Error }): never {
  throw error
}

afterEach(() => {
  cleanup()
  sessionStorage.clear()
  vi.restoreAllMocks()
})

describe('ErrorBoundary', () => {
  it('recognises stale lazy chunks', () => {
    expect(isChunkLoadError(new TypeError('Failed to fetch dynamically imported module: /assets/x.js'))).toBe(true)
    expect(isChunkLoadError(new Error('Cannot read properties of undefined'))).toBe(false)
  })

  it('shows a render error with a reload button', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const reload = vi.fn()
    render(
      <ErrorBoundary reload={reload}>
        <Boom error={new Error('bad data')} />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert').textContent).toContain('bad data')
    expect(reload).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Reload' }))
    expect(reload).toHaveBeenCalledOnce()
  })

  it('reloads once for a stale chunk, not again right after', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const reload = vi.fn()
    const stale = new TypeError('Failed to fetch dynamically imported module')
    render(
      <ErrorBoundary reload={reload}>
        <Boom error={stale} />
      </ErrorBoundary>,
    )
    expect(reload).toHaveBeenCalledOnce()
    expect(screen.getByRole('alert').textContent).toContain('updated since this tab was opened')
    cleanup()
    render(
      <ErrorBoundary reload={reload}>
        <Boom error={stale} />
      </ErrorBoundary>,
    )
    expect(reload).toHaveBeenCalledOnce() // the guard stops a reload loop
  })
})
