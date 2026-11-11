// Interface strings of the prophetic forms (DESIGN.md §16.92, D154). English first, Hebrew typed
// against it.

import { countEn, numEn, pct } from '../fmt'
import { register } from '../en'

export type ProphFormKey = 'messenger' | 'woe' | 'nations' | 'lawsuit' | 'call'

export const prophEn = {
  title: 'Forms of prophetic speech',
  lede: 'Five forms the prophets speak in, each found by the words that mark it: the messenger formula (כה אמר יהוה, נאם יהוה), the woe saying (הוי מגיעי בית בבית), the oracle against a foreign nation (משא בבל), the covenant lawsuit (שמעו שמים … כי ריב ליהוה) and the call of a prophet (God sends, the one sent objects or is reassured: אהה אדני יהוה). The words of each form are fixed in the settings, and so are the passages the commentaries name for four of them.',
  forms: {
    messenger: 'Messenger formula',
    woe: 'Woe saying',
    nations: 'Against the nations',
    lawsuit: 'Covenant lawsuit',
    call: 'Call narrative',
  } as Record<ProphFormKey, string>,
  formHints: {
    messenger: 'כה אמר or נאם followed by God’s name; counted, not judged (the words are matched as written)',
    woe: 'הוי opening a clause, followed by a participle, a noun or an adjective; not the cry over the dead (הוי אחי); to the next woe or the end of its paragraph',
    nations: 'In the Latter Prophets, a paragraph headed משא with a nation’s name, or naming the nations more than Israel in speech; adjacent paragraphs joined',
    lawsuit: 'A call to hear (שמעו, האזינו) with ריב, or heaven and earth, the mountains or the hills, within five verses',
    call: 'God’s commission (שלח with “you”, לך with a verb of speaking) with the objection of the one sent or God’s reassurance within five verses',
  } as Record<ProphFormKey, string>,
  counts: (n: number) => `${countEn(n, 'finding', 'findings')} in all.`,
  formCount: (n: number) => countEn(n, 'finding', 'findings'),
  verdict: { holds: 'Found', fails: 'Not all found' } as Record<'holds' | 'fails', string>,
  knownTitle: 'The passages named in advance',
  knownLede: (cover: number) =>
    `A passage of a form that fills it (the nations, the woe) counts as found when the form’s findings cover ${pct(cover)} of its verses; a passage that only locates the form (a call somewhere in the chapters, a lawsuit’s verse) when a finding overlaps it.`,
  known: (found: number, n: number) => `${numEn(found)} of ${numEn(n)} found.`,
  knownRef: (ref: string, found: boolean, cover: number) => `${ref}: ${found ? 'found' : 'not found'} (${pct(cover)} of its verses covered)`,
  booksTitle: 'The forms by book',
  booksLede: 'Findings of each form in each book; the books without any left out.',
  book: 'Book',
  listTitle: 'The findings',
  form: 'Form',
  allForms: 'All forms',
  knownOnly: 'Only those in a passage named in advance',
  itemCount: (total: number, page: number, pages: number) => `${countEn(total, 'finding', 'findings')} · page ${numEn(page)} of ${numEn(pages)}`,
  kind: { thus: 'כה אמר', oracle: 'נאם' } as Record<'thus' | 'oracle', string>,
  names: (names: string) => `naming ${names}`,
  heading: 'headed משא',
  paragraphs: (n: number) => countEn(n, 'paragraph', 'paragraphs'),
  dispute: 'ריב',
  witnesses: 'witnesses called',
  objection: 'an objection',
  reassurance: 'a reassurance',
  namedTag: 'named in advance',
  more: (n: number) => `and ${countEn(n, 'more verse', 'more verses')}`,
  read: 'read it with the layer',
  noData: 'The prophetic forms were not computed in this build.',
  none: 'No finding here.',
}

register('proph', prophEn)
