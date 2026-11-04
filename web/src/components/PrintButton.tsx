import { useT } from '../context/localeContext'

/** "Print": the page through the print stylesheet (no menus or controls, light, on white); the
 * print dialog also saves it as a PDF (§11.1). */
export function PrintButton() {
  const m = useT()
  return (
    <button type="button" className="linkish print-button" title={m.out.printTitle} onClick={() => window.print()}>
      {m.out.print}
    </button>
  )
}
