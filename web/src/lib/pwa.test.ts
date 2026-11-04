// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { currentUpdate, offerUpdate, type RegisterSW, startServiceWorker } from './pwa'

// What startServiceWorker sees of the browser: the worker's container (an event target), and the
// plugin's registerSW, which returns its update function and calls onNeedRefresh when a new
// build is waiting.
function fakeBrowser() {
  const container = new EventTarget()
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: container })
  let needRefresh = () => {}
  const updateSW = vi.fn(async () => {})
  const register: RegisterSW = (o) => {
    needRefresh = o.onNeedRefresh
    return updateSW
  }
  return { container, register, updateSW, needRefresh: () => needRefresh() }
}

afterEach(() => offerUpdate(null))

describe('startServiceWorker', () => {
  it('offers nothing until a new build waits', () => {
    startServiceWorker(fakeBrowser().register, vi.fn())
    expect(currentUpdate()).toBeNull()
  })

  it('reloads once the new worker controls the page, not before', () => {
    const b = fakeBrowser()
    const reload = vi.fn()
    startServiceWorker(b.register, reload)
    b.needRefresh()
    currentUpdate()!() // the banner's Reload
    expect(b.updateSW).toHaveBeenCalledOnce() // the waiting worker is told to take over
    expect(reload).not.toHaveBeenCalled()
    b.container.dispatchEvent(new Event('controllerchange'))
    expect(reload).toHaveBeenCalledOnce()
    b.container.dispatchEvent(new Event('controllerchange'))
    expect(reload).toHaveBeenCalledOnce()
  })
})
