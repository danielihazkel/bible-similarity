// Interface strings of the guided tours (DESIGN.md §11): four short walks through the site's
// strongest findings, each step a page and a sentence on what to look at. The routes are in
// `lib/tours.ts`. English first, Hebrew typed against it.

import { numEn } from '../fmt'

export type TourKey = 'parallels' | 'numbers' | 'poetry' | 'stories'

export interface TourText {
  title: string
  lede: string
  steps: string[] // one caption per route of `lib/tours.ts`
}

export const trEn = {
  title: 'Guided tours',
  lede: 'Four short walks through the site, each a few pages with a sentence on what to look at. A bar at the foot of the page leads from one step to the next; leave it whenever you like.',
  start: 'Start',
  steps: (n: number) => `${numEn(n)} steps`,
  bar: (title: string, step: number, of: number) => `${title} · step ${numEn(step)} of ${numEn(of)}`,
  back: 'Back',
  next: 'Next',
  finish: 'Finish',
  end: 'Leave the tour',
  homeTitle: 'New here?',
  homeLede: 'Take a guided tour, or look up a term in the glossary.',
  tours: {
    parallels: {
      title: 'One text, told twice',
      lede: 'Passages the Bible tells more than once, and what the tellings change.',
      steps: [
        'Psalms 14 and 53 are one psalm written twice. Hover a verse of either list to see the words they share and where they part: Psalm 53 has אלהים where Psalm 14 has יהוה.',
        'That swap is not chance: across Psalms 42–83 God is called אלהים far more than in the rest of the book. Each cell is a psalm; the darker, the more אלהים.',
        'Synopses set three or four tellings side by side, verse by verse: Kings, Isaiah and Chronicles on Hezekiah; Samuel and Chronicles on David. Open one to see each change marked.',
        'Where parallel tellings give different numbers, the difference is often one copying step: a power of ten, or one place. Each pair is shown with both verses and the numbers marked.',
      ],
    },
    numbers: {
      title: 'Counting and dating',
      lede: 'The text counts its years, its people and its letters. Do the counts hold?',
      steps: [
        'The years from Adam, read from the verses themselves: each father’s age at his son’s birth, the stated spans, the kings’ reigns. The Flood, Abram and the Exodus land where the tradition puts them.',
        'Ezra lists the families who came back from Babylon and then gives the whole assembly: 42,360. Open the list: its numbers add up to far fewer, a gap known since antiquity.',
        'The Masorah counted the Torah’s letters, words and verses and named their middles. Here the counts are made again on our text, and the distance from the tradition is shown.',
        'Every word has a numerical value. 318 is the number of Abraham’s men and the value of Eliezer, his servant’s name; search any value to see the words and verses that have it.',
      ],
    },
    poetry: {
      title: 'The shape of poetry',
      lede: 'Verse halves, alphabets, refrains and the turn of a lament.',
      steps: [
        'Most poetic verses fall into two halves, the second echoing the first. The pairs of words that answer each other across the halves are listed, the commonest first.',
        'Acrostics run through the alphabet, a letter to a verse or a line: Psalm 119, Lamentations 1–4, Proverbs 31. Each is checked against the letters shuffled.',
        'Psalm 22 in the reader, with the speakers and the mood of each verse shown: the lament turns to praise at verse 23, where the psalmist begins to speak of thanks.',
        'Refrains recur through a poem at intervals: Amos 4’s “yet you did not return to me”, Psalm 136’s “for his mercy endures forever”. Each is listed with its gaps.',
      ],
    },
    stories: {
      title: 'How the stories are told',
      lede: 'Patterns in the narrative: cycles, retellings, names and readings.',
      steps: [
        'Judges tells each judge’s story in a cycle: Israel does evil, is given into a hand, cries out, is saved, and the land rests. The cycle is whole for Othniel and breaks down by Samson.',
        'Speech retold: when a character repeats what someone said earlier (Eve the command of Eden, Abraham’s servant his master’s charge), the words change, and the changes are marked.',
        'Names explained in the text: “he called his name Noah, saying, this one will comfort us”. The name’s letters are found again in its explanation more than chance gives.',
        'Each Torah portion’s haftarah, chosen by the sages, ranked against all the chapters of the Prophets by the site’s own measures of likeness: Vayera’s, the Shunammite’s son, stands near the top.',
      ],
    },
  } satisfies Record<TourKey, TourText>,
}
