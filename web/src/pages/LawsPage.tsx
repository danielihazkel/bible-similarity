import { Link } from 'react-router'
import { useLawList, useLawPair, useLawPairs, useLaws } from '../api/hooks'
import { isStageMissing } from '../api/client'
import type { Law, LawPair, LawSideVerse, LawsResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { diffHighlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'
import type { LawAddress, LawCodeKey, LawFormKey } from '../i18n/pages/laws'
import '../i18n/pages/laws'
import '../styles/pages/LawsPage.css'

const PAGE_SIZE = 25
const CODES: LawCodeKey[] = ['covenant', 'ritual', 'holiness', 'deuteronomic', 'priestly']
const FORMS: LawFormKey[] = ['casuistic', 'apodictic', 'other']
const ADDRESS: LawAddress[] = ['2ms', '2mp', '3', 'mixed']
const isCode = (x: string | null): x is LawCodeKey => CODES.includes(x as LawCodeKey)
const isForm = (x: string | null): x is LawFormKey => FORMS.includes(x as LawFormKey)

type T = ReturnType<typeof useLocale>['m']['laws']

/** The law codes side by side (DESIGN.md §16.93, D155): each code's laws by form and address,
 * the pairs named in advance, the matched pairs, and one pair aligned word by word. */
export function LawsPage() {
  const { m } = useLocale()
  const t = m.laws
  const res = useLaws()
  const [params] = useQueryParams()
  const d = res.data
  const pair = Number(params.get('pair'))
  return (
    <div className="page laws-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {isStageMissing(res.error) ? (
        <NotComputed>{t.noData}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <p className="muted small">{t.counts(d.laws, d.pairs)}</p>
          {pair > 0 && <Synopsis id={pair} />}
          <Profile d={d} />
          <Known d={d} />
          <Lists d={d} />
        </>
      )}
    </div>
  )
}

function Profile({ d }: { d: LawsResponse }) {
  const t = useLocale().m.laws
  return (
    <section aria-labelledby="lw-profile">
      <h2 id="lw-profile">{t.profileTitle}</h2>
      <p className="muted small">{t.profileLede}</p>
      <ul className="small lw-forms">
        {FORMS.map((f) => (
          <li key={f}>
            <strong>{t.forms[f]}</strong>: {t.formHints[f]}
          </li>
        ))}
      </ul>
      <TableCsv name="law-codes" tabIndex={0} role="region" aria-labelledby="lw-profile">
        <table className="change-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.code}</th>
              <th scope="col">{t.cols.ranges}</th>
              <th scope="col" className="num">
                {t.cols.laws}
              </th>
              {FORMS.map((f) => (
                <th key={f} scope="col" className="num">
                  {t.forms[f]}
                </th>
              ))}
              <th scope="col">{t.cols.address}</th>
            </tr>
          </thead>
          <tbody>
            {d.codes.map((c) => {
              const top = ADDRESS.map((a) => [a, a === 'mixed' ? c.mixed : c[`v${a}` as 'v2ms' | 'v2mp' | 'v3']] as const).sort((x, y) => y[1] - x[1])
              return (
                <tr key={c.code}>
                  <th scope="row">{t.codes[c.code]}</th>
                  <td className="small">{t.codeRanges[c.code]}</td>
                  <td className="num">{c.laws}</td>
                  {FORMS.map((f) => (
                    <td key={f} className="num">
                      {t.cols.share(c[f], c.laws)}
                    </td>
                  ))}
                  <td>{t.address[top[0][0]]}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function Known({ d }: { d: LawsResponse }) {
  const t = useLocale().m.laws
  const [, update] = useQueryParams()
  return (
    <section aria-labelledby="lw-known">
      <h2 id="lw-known">{t.knownTitle}</h2>
      <p className="muted small">{t.knownLede}</p>
      <p>
        {t.known(d.known_found, d.known_total)} <span className="muted small">{t.strict(d.known_strict, d.known_total)}</span>
      </p>
      <ul className="lw-known">
        {d.known.map((k) => (
          <li key={k.group}>
            <span className={`dv-verdict ${k.found === k.of ? 'holds' : 'fails'}`}>{t.verdict[k.found === k.of ? 'holds' : 'fails']}</span> <strong>{t.groups[k.group] ?? k.group}</strong>
            <ul className="small">
              {k.members.map((mb) => (
                <li key={`${mb.a}|${mb.b}`}>
                  {t.member(mb.a, mb.b, mb.found)}
                  {mb.pairs.length > 0 && (
                    <>
                      {' '}
                      <button type="button" className="linkish" onClick={() => update({ pair: String(mb.pairs[0]) })}>
                        {t.showPair}
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Lists({ d }: { d: LawsResponse }) {
  const t = useLocale().m.laws
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'laws' ? 'laws' : 'pairs'
  return (
    <section aria-labelledby="lw-lists">
      <h2 id="lw-lists">{view === 'laws' ? t.lawsTitle : t.pairsTitle}</h2>
      <div className="toolbar">
        <Segmented<'pairs' | 'laws'>
          label={t.view.label}
          value={view}
          options={[
            { value: 'pairs', label: t.view.pairs },
            { value: 'laws', label: t.view.laws },
          ]}
          onChange={(v) => update({ view: v === 'pairs' ? null : v, page: null, form: null })}
        />
      </div>
      {view === 'laws' ? <LawList /> : <Pairs d={d} />}
    </section>
  )
}

function CodeSelect({ value, onChange }: { value: LawCodeKey | undefined; onChange: (v: string | null) => void }) {
  const t = useLocale().m.laws
  return (
    <label>
      {t.code}{' '}
      <select value={value ?? ''} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">{t.allCodes}</option>
        {CODES.map((c) => (
          <option key={c} value={c}>
            {t.codes[c]}
          </option>
        ))}
      </select>
    </label>
  )
}

function Pairs({ d }: { d: LawsResponse }) {
  const t = useLocale().m.laws
  const [params, update] = useQueryParams()
  const cp = params.get('code')
  const code = isCode(cp) ? cp : undefined
  const order = params.get('order') === 'canon' ? 'canon' : 'score'
  const known = params.get('known') === '1'
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useLawPairs({ order, code, known, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <>
      <p className="muted small">{t.pairsLede(d.top_k, d.min_links)}</p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented<'score' | 'canon'>
          label={t.order.label}
          value={order}
          options={[
            { value: 'score', label: t.order.score },
            { value: 'canon', label: t.order.canon },
          ]}
          onChange={(v) => set({ order: v === 'score' ? null : v })}
        />
        <CodeSelect value={code} onChange={(v) => set({ code: v })} />
        <label className="check">
          <input type="checkbox" checked={known} onChange={(e) => set({ known: e.target.checked ? '1' : null })} />
          {t.knownOnly}
        </label>
      </div>
      <PagedList res={res} empty={t.none} summary={(x, p, pages) => t.pairCount(x.total, p, pages)}>
        {(x, stale) => (
          <ol className={`hits lw-pairs ${stale}`}>
            {x.items.map((p) => (
              <PairItem key={p.pair_id} p={p} />
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function lawName(l: Law, t: T, locale: 'en' | 'he') {
  const first = locale === 'he' ? l.first_label_he : l.first_label
  const last = locale === 'he' ? l.last_label_he : l.last_label
  return `${t.codes[l.code]}, ${l.first_vid === l.last_vid ? first : `${first} – ${last}`}`
}

function PairItem({ p }: { p: LawPair }) {
  const { m, locale } = useLocale()
  const t = m.laws
  const [, update] = useQueryParams()
  const extra = [t.links(p.links), t.kept(p.kept), ...(p.known ? [t.namedTag(t.groups[p.known] ?? p.known)] : [])]
  return (
    <li className="hit lw-pair">
      <div className="hit-head">
        <span className="verse-ref">{lawName(p.a, t, locale)}</span> ↔ <span className="verse-ref">{lawName(p.b, t, locale)}</span>
      </div>
      <p className="muted small">
        {extra.join(' · ')}{' '}
        <button type="button" className="linkish" onClick={() => update({ pair: String(p.pair_id) })}>
          {t.showPair}
        </button>
      </p>
    </li>
  )
}

function LawList() {
  const { m, locale } = useLocale()
  const t = m.laws
  const [params, update] = useQueryParams()
  const cp = params.get('code')
  const code = isCode(cp) ? cp : undefined
  const fp = params.get('form')
  const form = isForm(fp) ? fp : undefined
  const page = parsePage(params.get('page'))
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useLawList({ code, form, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <>
      <div className="toolbar">
        <CodeSelect value={code} onChange={(v) => set({ code: v })} />
        <Segmented<string>
          label={t.form}
          value={form ?? 'all'}
          options={[{ value: 'all', label: t.allForms }, ...FORMS.map((f) => ({ value: f, label: t.forms[f] }))]}
          onChange={(v) => set({ form: v === 'all' ? null : v })}
        />
      </div>
      <PagedList res={res} empty={t.none} summary={(x, p, pages) => t.lawCount(x.total, p, pages)}>
        {(x, stale) => (
          <ol className={`hits lw-laws ${stale}`}>
            {x.items.map((l) => (
              <li key={l.law_id} className="hit lw-law">
                <div className="hit-head">
                  <Link to={unitLink(l.unit_id)} className="verse-ref">
                    {lawName(l, t, locale)}
                  </Link>{' '}
                  <span className="muted small">
                    {[t.forms[l.form], l.address ? t.address[l.address] : null, t.lawPairs(l.pairs)].filter(Boolean).join(' · ')}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function Side({ verses, label, rest }: { verses: LawSideVerse[]; label: string; rest: number }) {
  const { m, locale } = useLocale()
  return (
    <div className="lw-side" role="group" aria-label={label}>
      <h3>{label}</h3>
      {verses.map((v) => (
        <p key={v.verse.verse_id} className="lw-verse">
          <span className="verse-ref small">{locale === 'he' ? v.verse.ref_he : v.verse.ref}</span> <HebrewText verse={v.verse} highlight={diffHighlight(v.marks)} />
        </p>
      ))}
      {rest > 0 && <p className="muted small">{m.laws.more(rest)}</p>}
    </div>
  )
}

function Synopsis({ id }: { id: number }) {
  const { m, locale } = useLocale()
  const t = m.laws
  const [, update] = useQueryParams()
  const res = useLawPair(id)
  if (res.isPending) return <Loading />
  if (res.isError) return <ErrorBox error={res.error} />
  const { pair, a, b } = res.data
  const span = (x: 'a' | 'b') => (locale === 'he' ? pair[`${x}_span_he`] : pair[`${x}_span`])
  const nameA = `${t.codes[pair.a.code]}, ${span('a')}`
  const nameB = `${t.codes[pair.b.code]}, ${span('b')}`
  return (
    <section className="lw-synopsis" aria-labelledby="lw-syn">
      <h2 id="lw-syn">{t.synopsisTitle(t.codes[pair.a.code], t.codes[pair.b.code])}</h2>
      <p className="muted small">
        {t.synopsisLede} {t.kept(pair.kept)}.{' '}
        <button type="button" className="linkish" onClick={() => update({ pair: null })}>
          {t.close}
        </button>
      </p>
      <DiffLegend />
      <div className="lw-columns">
        <Side verses={a} label={nameA} rest={pair.a_last - pair.a_first + 1 - a.length} />
        <Side verses={b} label={nameB} rest={pair.b_last - pair.b_first + 1 - b.length} />
      </div>
    </section>
  )
}
