// Interface strings of Overview → Place lists on the ground (DESIGN.md §16.58). English first,
// Hebrew typed against it.

import type { PlaceListKind } from '../../api/types'
import { countEn, countHe, numEn, pct } from '../fmt'
import { register } from '../en'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const townsHe = (n: number) => countHe(n, 'עיר אחת', 'שתי ערים', 'ערים')
export const placesHe = (n: number) => countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')

export const plsEn = {
  title: 'Place lists on the ground',
  lede: 'The text lists places: the stations of the wilderness, the borders of the land, the towns of Judah and of the tribes, the cities of the table of nations. Are they named in an order that walks the ground? A list’s places, in the order the text names them, make a path; its length is set against the same places in random order. Joshua’s town lists are checked by district as well.',
  noData: 'Not computed in this build: run `bsim place-lists`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (held: number, n: number, heldSure: number, nSure: number, shuffles: number, sure: number) =>
    `${numEn(held)} of ${numEn(n)} lists make a shorter path than random orders of their places (${numEn(shuffles)} orders each); on sure sites alone (an OpenBible vote of at least ${numEn(sure)}), ${numEn(heldSure)} of ${numEn(nSure)}.`,
  caveat: 'Why sure sites alone: an obscure town is often placed by the company it keeps in the list, which would make the test circular. Regions are left out, having no single site.',
  listsTitle: 'The lists',
  cols: { list: 'List', kind: 'Kind', places: 'Places', path: 'Its path', random: 'Random orders', short: 'A short path', order: 'Order', p: 'p', sure: 'Sure sites only' },
  colHints: {
    places: 'Located places of the list, of those it names',
    order: 'How far the text’s path goes from the random orders’ mean towards a short path through the same places: 0 no better than random, 100% as short',
  },
  kinds: { itinerary: 'Itinerary', boundary: 'Boundary', towns: 'Town list', nations: 'Table of nations' } satisfies Record<PlaceListKind, string>,
  km: (n: number) => `${numEn(Math.round(n))} km`,
  placesOf: (n: number, named: number) => (n === named ? numEn(n) : `${numEn(n)} of ${numEn(named)}`),
  order: (x: number) => pct(x),
  p: fp,
  untested: (n: number) => `${countEn(n, 'place', 'places')}: too few`,
  open: (label: string) => `Open ${label}`,
  // one list
  pathTitle: (label: string) => `The path of ${label}`,
  mapLabel: (label: string) => `The places of ${label} on the map, joined in the order the text names them`,
  show: 'Show',
  shows: { text: 'The text’s order', short: 'A short path' },
  pathNote: (n: number, path: number, mean: number, short: number, p: number) =>
    `${countEn(n, 'place', 'places')}: the text’s order walks ${numEn(Math.round(path))} km; random orders of the same places ${numEn(Math.round(mean))} km on average, a short path ${numEn(Math.round(short))} km (p ${fp(p)}).`,
  histTitle: 'The text’s path among random orders',
  histLabel: (path: number, mean: number) =>
    `A histogram of the random orders’ path lengths, centred near ${numEn(Math.round(mean))} km; the text’s path, ${numEn(Math.round(path))} km, is marked.`,
  histText: 'the text',
  histShort: 'short path',
  stepsTitle: 'In the text’s order',
  stepsLede: 'Each place with the km from the one before; a sure site is marked. A long step is a place far from its neighbours in the list: often an identification to doubt.',
  sure: 'sure',
  sureTitle: (score: number) => `A sure site: OpenBible’s vote ${numEn(score)} / 1,000`,
  onMap: (he: string) => `${he} on Places on the map`,
  // districts
  districtsTitle: 'Joshua’s towns by district',
  districtsLede: 'Judah’s towns come in districts, each closed by “cities … with their villages”; the tribes’ towns likewise. Do two towns of one district lie closer than two towns of the list with the districts shuffled over them?',
  grouping: 'Grouping',
  groupings: { judah: 'Judah’s districts (Joshua 15:21–62)', tribes: 'The tribes’ towns (Joshua 18–19)' } as Record<string, string>,
  districtSummary: (n: number, k: number, within: number, mean: number, p: number, nearest: number) =>
    `${countEn(n, 'town', 'towns')} in ${numEn(k)} districts: two towns of one district lie ${numEn(Math.round(within))} km apart on average, against ${numEn(Math.round(mean))} km with the districts shuffled (p ${fp(p)}); ${pct(nearest)} of the towns have a town of their own district nearest.`,
  districtSure: (n: number, within: number, mean: number, p: number) =>
    `On sure sites alone (${countEn(n, 'town', 'towns')}): ${numEn(Math.round(within))} km against ${numEn(Math.round(mean))} km (p ${fp(p)}).`,
  districtMap: (label: string) => `The towns of ${label} on the map, coloured by district`,
  dcols: { district: 'District', towns: 'Towns', apart: 'Km apart', random: 'Shuffled', p: 'p', sure: 'Sure sites only' },
  single: 'one town',
  credit: 'Map: Natural Earth (public domain). Places: STEPBible’s TIPNR and OpenBible.info (CC BY 4.0).',
}

register('pls', plsEn)
