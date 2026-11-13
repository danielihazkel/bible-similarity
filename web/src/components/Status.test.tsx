// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ApiError } from '../api/client'
import { Loading, PageWait } from './Status'

afterEach(cleanup)

describe('Loading (M176)', () => {
  it('is a line of text, or quiet rows in a list’s place that still say so to a screen reader', () => {
    const { container, rerender } = render(<Loading />)
    expect(screen.getByRole('status').textContent).toBe('Loading…')
    expect(container.querySelector('.list-placeholder')).toBeNull()
    rerender(<Loading list />)
    const status = screen.getByRole('status')
    expect(status.className).toBe('list-placeholder')
    expect(status.textContent).toBe('Loading…')
    expect(status.querySelector('.sr-only')?.textContent).toBe('Loading…')
    expect(status.querySelectorAll('span[aria-hidden="true"]').length).toBeGreaterThan(3)
  })
})

describe('PageWait: a page before its data (M176)', () => {
  it('draws the heading and the lede at once, then the placeholder', () => {
    const { container } = render(<PageWait className="page ketiv-page" title="Ketiv and qere" lede="Where the text is read otherwise than written." />)
    const page = container.firstElementChild!
    expect(page.className).toBe('page ketiv-page')
    expect([...page.children].map((c) => c.tagName)).toEqual(['H1', 'P', 'DIV'])
    expect(screen.getByRole('heading', { level: 1, name: 'Ketiv and qere' })).toBeTruthy()
    expect(page.querySelector('.lede')?.textContent).toContain('read otherwise')
    expect(screen.getByRole('status').className).toBe('list-placeholder')
    expect(container.querySelector('.heading-placeholder')).toBeNull()
  })

  it('holds the heading’s place on a page whose heading is its data', () => {
    const { container } = render(<PageWait className="page unit-page" />)
    expect(screen.queryByRole('heading')).toBeNull()
    const held = container.querySelector('.heading-placeholder')!
    expect(held.getAttribute('aria-hidden')).toBe('true')
    expect(held.nextElementSibling?.className).toBe('list-placeholder')
  })

  it('shows the error under the heading, in the placeholder’s place', () => {
    const { container, rerender } = render(<PageWait title="Citations" error={new ApiError(500, 'boom')} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Citations' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('boom')
    expect(container.querySelector('.list-placeholder')).toBeNull()
    // with no heading to give, the error stands alone
    rerender(<PageWait error={new ApiError(404, 'no such unit')} />)
    expect(container.querySelector('.heading-placeholder')).toBeNull()
    expect(screen.getByRole('alert').textContent).toContain('no such unit')
  })
})
