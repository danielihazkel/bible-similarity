import { useT } from '../context/localeContext'
import { useOnline, useUpdate } from '../lib/pwa'
import '../styles/components/AppBanner.css'

/**
 * Under the header: that the browser is offline (pages and answers already opened still work,
 * from the service worker), and that a new build of the viewer is ready, with a reload into it.
 * The live region is always there, so a screen reader hears it when it fills.
 */
export function AppBanner() {
  const m = useT()
  const online = useOnline()
  const update = useUpdate()
  return (
    <div className="app-banner" role="status">
      {!online && <p>{m.offline.notice}</p>}
      {update && (
        <p>
          {m.offline.update}{' '}
          <button type="button" onClick={update}>
            {m.status.reload}
          </button>
        </p>
      )}
    </div>
  )
}
