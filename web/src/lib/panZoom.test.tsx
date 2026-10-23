// @vitest-environment jsdom
import { cleanup, fireEvent, render } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { type PanZoomOptions, usePanZoom } from './panZoom'

function Box(opts: PanZoomOptions) {
  const ref = useRef<HTMLDivElement>(null)
  const { handlers } = usePanZoom(ref, opts)
  return <div ref={ref} data-testid="box" {...handlers} />
}

afterEach(cleanup)

describe('usePanZoom', () => {
  it('leaves a plain wheel to the page by default, zooming with Ctrl', () => {
    const onZoom = vi.fn()
    const { getByTestId } = render(<Box onZoom={onZoom} />)
    fireEvent.wheel(getByTestId('box'), { deltaY: 100 })
    expect(onZoom).not.toHaveBeenCalled()
    fireEvent.wheel(getByTestId('box'), { deltaY: 100, ctrlKey: true })
    expect(onZoom).toHaveBeenCalledOnce()
    expect(onZoom.mock.calls[0][0]).toBeLessThan(1)
  })

  it('zooms with any wheel in zoom mode, a notch at most ×1.5; Shift or a sideways swipe pans', () => {
    const onZoom = vi.fn()
    const onPan = vi.fn()
    const { getByTestId } = render(<Box wheel="zoom" onZoom={onZoom} onPan={onPan} />)
    const box = getByTestId('box')
    fireEvent.wheel(box, { deltaY: -100 })
    expect(onZoom.mock.calls[0][0]).toBeGreaterThan(1)
    fireEvent.wheel(box, { deltaY: -3, deltaMode: 1 }) // lines: 48 pixels
    expect(onZoom.mock.calls[1][0]).toBeCloseTo(Math.exp(48 * 0.002))
    fireEvent.wheel(box, { deltaY: -5000 })
    expect(onZoom.mock.calls[2][0]).toBe(1.5)
    fireEvent.wheel(box, { deltaY: 40, shiftKey: true })
    fireEvent.wheel(box, { deltaX: 30, deltaY: 5 })
    expect(onPan.mock.calls).toEqual([
      [-40, 0],
      [-30, 0],
    ])
    expect(onZoom).toHaveBeenCalledTimes(3)
  })
})
