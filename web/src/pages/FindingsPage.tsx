import { Link } from 'react-router'
import { useFindings } from '../api/hooks'
import type { Finding, FindingKey } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { type NavKey, navText } from '../lib/nav'

const VERDICTS: Finding['verdict'][] = ['holds', 'fails', 'lead']
// where each finding's evidence is read
const PAGES: Record<FindingKey, { to: string; nav: NavKey }> = {
  acrostics: { to: '/acrostics', nav: 'acrostics' },
  divisions: { to: '/divisions', nav: 'divisions' },
  dating: { to: '/language', nav: 'language' },
  borrowing: { to: '/borrowing', nav: 'borrowing' },
  citations: { to: '/citations?family=command', nav: 'citations' },
  voices: { to: '/speech?view=voices', nav: 'speech' },
  clauses: { to: '/structure?view=small', nav: 'structure' },
  meter: { to: '/poetry?view=meter', nav: 'poetry' },
  laments: { to: '/poetry?view=meter', nav: 'poetry' },
  cognate: { to: '/roots', nav: 'roots' },
  root_leitworte: { to: '/roots?view=key', nav: 'roots' },
  refrains: { to: '/refrains', nav: 'refrains' },
  refrain_regular: { to: '/refrains', nav: 'refrains' },
  refrain_turns: { to: '/refrains', nav: 'refrains' },
  psalm_genres: { to: '/psalms', nav: 'psalms' },
  psalm_forms: { to: '/psalms', nav: 'psalms' },
  lament_turn: { to: '/psalms?sort=turn', nav: 'psalms' },
  lament_turns: { to: '/psalms?genre=lament_individual&sort=turn', nav: 'psalms' },
  pentateuch_split: { to: '/pentateuch', nav: 'pentateuch' },
  pentateuch_genesis: { to: '/pentateuch', nav: 'pentateuch' },
  pentateuch_names: { to: '/pentateuch', nav: 'pentateuch' },
  dialogue_deference: { to: '/speech?view=dialogue', nav: 'speech' },
  dialogue_particle: { to: '/speech?view=dialogue', nav: 'speech' },
  dialogue_last_word: { to: '/speech?view=dialogue', nav: 'speech' },
  forms_known: { to: '/forms', nav: 'forms' },
  forms_chance: { to: '/forms', nav: 'forms' },
  forms_parallel: { to: '/forms', nav: 'forms' },
  forms_lists: { to: '/forms?view=lists', nav: 'forms' },
  divine_elohistic: { to: '/divine', nav: 'divine' },
  divine_doubled: { to: '/divine#pairs', nav: 'divine' },
  etiology_echo: { to: '/etiologies', nav: 'etiologies' },
  etiology_known: { to: '/etiologies?show=known', nav: 'etiologies' },
  brackets_insertion: { to: '/brackets', nav: 'brackets' },
  brackets_known: { to: '/brackets?show=known', nav: 'brackets' },
  retold_claim: { to: '/retold', nav: 'retold' },
  retold_known: { to: '/retold?known=1', nav: 'retold' },
  haftarot_claim: { to: '/haftarot', nav: 'haftarot' },
  haftarot_calendar: { to: '/haftarot', nav: 'haftarot' },
  haftarot_known: { to: '/haftarot?p=p%3ANoach', nav: 'haftarot' },
  ciphers_known: { to: '/ciphers?known=1', nav: 'ciphers' },
  ciphers_jeremiah: { to: '/ciphers', nav: 'ciphers' },
  ciphers_elsewhere: { to: '/ciphers', nav: 'ciphers' },
  ciphers_albam: { to: '/ciphers?cipher=albam', nav: 'ciphers' },
  masorah_letter: { to: '/masorah', nav: 'masorah' },
  masorah_words: { to: '/masorah', nav: 'masorah' },
  masorah_verse: { to: '/masorah', nav: 'masorah' },
  masorah_books: { to: '/masorah#totals', nav: 'masorah' },
  gematria_links: { to: '/gematria-links', nav: 'gematriaLinks' },
  gematria_measures: { to: '/gematria-links', nav: 'gematriaLinks' },
  gematria_genesis: { to: '/gematria-links#genesis', nav: 'gematriaLinks' },
  place_lists_order: { to: '/place-lists', nav: 'placeLists' },
  place_lists_districts: { to: '/place-lists#districts', nav: 'placeLists' },
  place_arc_order: { to: '/place-arc', nav: 'placeArc' },
  place_arc_moves: { to: '/place-arc#moves', nav: 'placeArc' },
  place_arc_oracles: { to: '/place-arc#oracles', nav: 'placeArc' },
  place_links_decay: { to: '/place-links', nav: 'placeLinks' },
  place_links_known: { to: '/place-links#leads', nav: 'placeLinks' },
  els_counts: { to: '/els', nav: 'els' },
  els_known: { to: '/els#known', nav: 'els' },
  echoes: { to: '/network?view=directions', nav: 'network' },
  sevens: { to: '/structure', nav: 'structure' },
  chiasm: { to: '/structure?view=small', nav: 'structure' },
  allusions: { to: '/phrases?view=spread', nav: 'phrases' },
}

/** The claim each analysis tested, the numbers that decide it and the verdict they give (`/findings`). */
export function FindingsPage() {
  const { m, locale } = useLocale()
  const t = m.find
  const res = useFindings()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { items, alpha } = res.data
  return (
    <div className="page findings-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede(alpha)}</p>
      {items.length === 0 && <p className="status">{t.noData}</p>}
      {VERDICTS.map((verdict) => {
        const group = items.filter((f) => f.verdict === verdict)
        if (group.length === 0) return null
        return (
          <section key={verdict} aria-labelledby={`findings-${verdict}`} className={`findings-group ${verdict}`}>
            <h2 id={`findings-${verdict}`}>{t.groups[verdict].title}</h2>
            <p className="muted small">{t.groups[verdict].hint}</p>
            <ul className="findings-list">
              {group.map((f) => {
                const item = t.items[f.key]
                const page = PAGES[f.key]
                const label = navText(m, page.nav).label
                return (
                  <li key={f.key} className="finding">
                    <h3>{item.title}</h3>
                    <p>{item.text(f.values)}</p>
                    <Link to={page.to} className="small" aria-label={`${item.title}: ${label}`}>
                      {label} {locale === 'he' ? '←' : '→'}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
