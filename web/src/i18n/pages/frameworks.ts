// Interface strings of the frameworks page (DESIGN.md §16.71): the judges' cycle and the kings'
// regnal accounts. English first, Hebrew typed against it. The formulas are quoted in Hebrew,
// isolated in the English sentences.

import { numEn } from '../fmt'
import { register } from '../en'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const x2 = (x: number) => x.toFixed(2)

export const fwEn = {
  title: 'Narrative frameworks',
  lede: 'Judges tells its deliverances in one frame: Israel did evil in the eyes of the LORD, he gave them into an enemy’s hand for so many years, they cried out, he raised them a deliverer, and the land was at rest. Kings frames every reign alike: the accession, the king’s age and his mother, the verdict, the high places, the sins of Jeroboam, the burial. Here each frame is looked for, slot by slot, in the words of the text.',
  notComputed: 'The frameworks were not computed in this build (run bsim frameworks).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  cycle: {
    title: 'The cycle breaks down through Judges',
    text: (rho: number, n: number, p: number) =>
      `Does each judge’s share of the cycle’s slots fall through the book? Spearman’s rho with the book’s order ${x2(rho)}, against every order of the ${numEn(n)} episodes (p ${fp(p)}).`,
  },
  cycleKnown: {
    title: 'Othniel whole, Samson broken',
    text: (othniel: string, samson: string) => `Othniel’s cycle has every slot (missing: ${othniel}); Samson’s has no cry and no rest (missing: ${samson}).`,
  },
  verdicts: {
    title: 'Each kingdom’s verdicts have their own wording',
    text: (n: number, within: number, between: number, p: number) =>
      `The ${numEn(n)} verdicts with the verses that follow them, compared word by word: verdicts of one kingdom ${x2(within)} alike on average, of different kingdoms ${x2(between)}, with the kingdoms shuffled (p ${fp(p)}).`,
  },
  verdictsKnown: {
    title: 'The verdicts are read right',
    text: (found: number, n: number, list: string) => `${numEn(found)} of ${numEn(n)} verdicts named in advance read as expected: ${list}.`,
    row: (name: string, expected: string, found: string) => `${name} ${found}${found === expected ? '' : ` (not ${expected})`}`,
  },
  none: 'nothing',
  slot: {
    evil: 'Did evil',
    oppression: 'Given into a hand',
    years: 'Years of servitude',
    cry: 'Cried out',
    deliverer: 'A deliverer raised',
    rest: 'The land at rest',
    age: 'Age',
    mother: 'Mother',
    high_places: 'High places',
    jeroboam: 'Sins of Jeroboam',
    burial: 'Burial',
    verdict_vid: 'Verdict',
  } as Record<string, string>,
  formulas: 'The formulas: ⁨ויעשו בני ישראל הרע בעיני יהוה⁩ · ⁨וימכרם ביד⁩ · ⁨ויעבדו ... שנה⁩ · ⁨ויזעקו אל יהוה⁩ · ⁨ויקם יהוה מושיע⁩ · ⁨ותשקט הארץ⁩.',
  cycleTitle: 'The judges’ cycle',
  cycleLede: (open: number) => `The opening slots are looked for in an episode’s first ${numEn(open)} verses, the rest in the whole episode. A tick links to the verse.`,
  episode: 'Judge',
  share: 'Slots',
  found: (ref: string) => `found in ${ref}`,
  absent: 'absent',
  kingsTitle: 'The kings’ verdicts',
  kingsLede: 'The verdict is the first verse after a king’s regnal formula that says he did evil, or what was right, in the eyes of the LORD. Choose a king to read it.',
  wording: (judah: number | undefined, israel: number | undefined, between: number | null) =>
    `How alike the verdicts are worded: within Judah ${judah === undefined ? '–' : x2(judah)}, within Israel ${israel === undefined ? '–' : x2(israel)}, across the kingdoms ${between === null ? '–' : x2(between)}.`,
  king: 'King',
  kingdom: { judah: 'Judah', israel: 'Israel' } as Record<string, string>,
  verdict: 'Verdict',
  verdictTag: { good: 'right', bad: 'evil' } as Record<string, string>,
  noVerdict: 'none found',
  showKing: (name: string) => `The account of ${name}`,
  kingTitle: (name: string) => `${name}: the verdict`,
  close: 'Close',
  byKingdomTitle: 'What each kingdom’s accounts hold',
  byKingdomLede: 'The share of each kingdom’s kings whose account holds the slot:',
}

register('fw', fwEn)
