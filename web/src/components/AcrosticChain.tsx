import type { Acrostic } from '../api/types'

const ALPHABET = 'אבגדהוזחטיכלמנסעפצקרשת'
const ORDERS: Record<Acrostic['order_name'], string> = {
  standard: ALPHABET,
  'pe-ayin': ALPHABET.replace('עפ', 'פע'),
}

/** The alphabet in the chain's order: letters found in order, skipped ones, and those outside it. */
export function AcrosticChain({ a }: { a: Acrostic }) {
  const order = ORDERS[a.order_name]
  const found = new Set(a.chain.map((l) => l.letter))
  const first = order.indexOf(a.first_letter)
  const last = order.indexOf(a.last_letter)
  return (
    <span
      className="acrostic-chain he"
      dir="rtl"
      lang="he"
      aria-label={`${a.n_letters} letters in order from ${a.first_letter} to ${a.last_letter}, ${a.missing} skipped`}
    >
      {[...order].map((ch, i) => {
        const cls = found.has(ch) && i >= first && i <= last ? 'in' : i > first && i < last ? 'skipped' : 'out'
        return (
          <span key={ch} className={`acr-${cls}`} title={cls === 'skipped' ? 'skipped' : undefined}>
            {ch}
          </span>
        )
      })}
    </span>
  )
}
