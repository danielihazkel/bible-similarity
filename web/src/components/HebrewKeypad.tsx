import { KEYPAD_LETTERS } from '../lib/hebrew'

interface Props {
  onKey: (text: string) => void
  onBackspace: () => void
}

/** On-screen Hebrew letters for machines without a Hebrew keyboard layout. */
export function HebrewKeypad({ onKey, onBackspace }: Props) {
  return (
    <div className="keypad" dir="rtl" lang="he" aria-label="Hebrew keyboard">
      {KEYPAD_LETTERS.map((l) => (
        <button key={l} type="button" onClick={() => onKey(l)}>
          {l}
        </button>
      ))}
      <button type="button" className="wide" onClick={() => onKey(' ')} aria-label="Space">
        ␣
      </button>
      <button type="button" className="wide" onClick={onBackspace} aria-label="Backspace">
        ⌫
      </button>
    </div>
  )
}
