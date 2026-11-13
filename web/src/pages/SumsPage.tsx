import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { useBooks, useSums, useSumsItems, useSumsParallels } from '../api/hooks'
import type { SumsList, SumsParallel, SumsResponse, Verse } from '../api/types'
import { isStageMissing } from '../api/client'
import { BookSelect, Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { SmScope, SmStep } from '../i18n/pages/sums'
import '../i18n/pages/sums'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'
import '../styles/pages/SumsPage.css'

const PAGE_SIZE = 25

/** Do the sums add up (§16.75): each list against the total the text states, a list's counts,
 * and the numbers of parallel verses side by side. */
export function SumsPage() {
  const { m } = useLocale()
  const t = m.sm
  const res = useSums()
  const d = res.data
  return (
    <div className="page sums-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {isStageMissing(res.error) ? (
        <NotComputed>{t.notComputed}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <Checks d={d} />
          <Lists d={d} />
          <Parallels />
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.sm
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Ref({ v }: { v: Verse }) {
  return (
    <Link className="verse-ref" to={unitLink(`v:${v.verse_id}`)}>
      <UnitName en={v.ref} he={v.ref_he} />
    </Link>
  )
}

function Checks({ d }: { d: SumsResponse }) {
  const t = useLocale().m.sm
  const a = d.across
  return (
    <section aria-labelledby="sm-checks">
      <h2 id="sm-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.lists.title} <Verdict holds={d.lists_holds} />
          </h3>
          <p>{t.lists.text(d.lists_adding_up, d.lists.length)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.step.title} <Verdict holds={d.step_holds} />
          </h3>
          <p>{t.step.text(a.one_step, a.tested, a.share, a.expected, a.p)}</p>
          <p className="muted small">{t.step.every(d.every.share, d.every.expected, d.every.p)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <ul className="sm-known">
            {d.known_parallels.map((k) => (
              <li key={`${k.a.verse_id}:${k.b.verse_id}`}>
                <Ref v={k.a} /> · <Ref v={k.b} />: {t.known.found(k.a_value, k.b_value)} ({!k.found ? t.known.missing : k.one_step ? t.known.oneStep : t.known.notOneStep})
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  )
}

function Lists({ d }: { d: SumsResponse }) {
  const { m } = useLocale()
  const t = m.sm
  const [params, update] = useQueryParams()
  const sel = d.lists.find((l) => l.key === params.get('list'))
  const name = (l: SumsList) => t.name[l.key] ?? l.key
  return (
    <section aria-labelledby="sm-lists">
      <h2 id="sm-lists">{t.listsTitle}</h2>
      {sel && <ListPanel l={sel} name={name(sel)} onClose={() => update({ list: null }, false)} />}
      <TableCsv name="sums-1" tabIndex={0} role="region" aria-labelledby="sm-lists">
        <table className="change-table sm-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.list}</th>
              <th scope="col" className="num">
                {t.cols.items}
              </th>
              <th scope="col" className="num">
                {t.cols.sum}
              </th>
              <th scope="col" className="num">
                {t.cols.total}
              </th>
              <th scope="col" className="num">
                {t.cols.diff}
              </th>
              <th scope="col">{t.cols.adds}</th>
              <th scope="col">{t.cols.known}</th>
            </tr>
          </thead>
          <tbody>
            {d.lists.map((l) => (
              <tr key={l.key} className={l.adds_up ? '' : 'sm-off'}>
                <td>
                  <button type="button" className="linkish" aria-label={t.showItems(name(l))} aria-pressed={sel?.key === l.key} onClick={() => update({ list: sel?.key === l.key ? null : l.key }, false)}>
                    {name(l)}
                  </button>{' '}
                  <span className="muted small">
                    <UnitName en={l.first_verse.ref} he={l.first_verse.ref_he} />
                  </span>
                </td>
                <td className="num">{m.num(l.n_items)}</td>
                <td className="num">{m.num(l.sum)}</td>
                <td className="num">
                  <Link to={unitLink(`v:${l.total_verse.verse_id}`)}>{m.num(l.total)}</Link>
                </td>
                <td className="num">{l.sum === l.total ? '–' : m.num(l.total - l.sum)}</td>
                <td>{l.adds_up ? t.yes : t.no}</td>
                <td>
                  <Verdict holds={l.holds} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function span(first: number | null, last: number | null): Highlight {
  const hl: Highlight = new Map()
  if (first === null || last === null) return hl
  for (let i = first; i <= last; i++) hl.set(i, 'shared')
  return hl
}

function ListPanel({ l, name, onClose }: { l: SumsList; name: string; onClose: () => void }) {
  const { m } = useLocale()
  const t = m.sm
  const res = useSumsItems(l.key)
  // one row per verse, its counts marked
  const ref = useRef<HTMLElement>(null)
  // the list is chosen from the table below: bring its panel into view
  useEffect(() => ref.current?.scrollIntoView?.({ block: 'nearest' }), [l.key])
  const rows = new Map<number, { verse: Verse; values: number[]; hl: Highlight }>()
  for (const it of res.data?.items ?? []) {
    const r = rows.get(it.verse.verse_id) ?? { verse: it.verse, values: [] as number[], hl: new Map() as Highlight }
    r.values.push(it.value)
    for (const [k, v] of span(it.tok_first, it.tok_last)) r.hl.set(k, v)
    rows.set(it.verse.verse_id, r)
  }
  return (
    <section ref={ref} className="hf-list sm-panel" aria-labelledby="sm-panel">
      <h3 id="sm-panel">{t.itemsTitle(name)}</h3>
      {res.isError ? (
        <ErrorBox error={res.error} />
      ) : !res.data ? (
        <Loading />
      ) : (
        <ol className="hits">
          {[...rows.values()].map((r) => (
            <li key={r.verse.verse_id} className="hit">
              <div className="hit-head">
                <Ref v={r.verse} /> <b>{r.values.map((x) => m.num(x)).join(' + ')}</b>
              </div>
              <p className="hit-text">
                <HebrewText verse={r.verse} highlight={r.hl} />
              </p>
            </li>
          ))}
          <li className="hit sm-total">
            <div className="hit-head">
              {t.totalVerse}: <Ref v={l.total_verse} /> <b>{m.num(l.total)}</b>
            </div>
            <p className="hit-text">
              <HebrewText verse={l.total_verse} highlight={span(l.total_tok_first, l.total_tok_last)} />
            </p>
          </li>
        </ol>
      )}
      <button type="button" className="linkish small" onClick={onClose}>
        {t.close}
      </button>
    </section>
  )
}

function Parallels() {
  const { m } = useLocale()
  const t = m.sm
  const [params, update] = useQueryParams()
  const scope: SmScope = params.get('scope') === 'every' ? 'every' : 'across'
  const sp = params.get('step')
  const step: SmStep = sp === 'yes' || sp === 'no' ? sp : 'all'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useSumsParallels({
    across: scope === 'across',
    oneStep: step === 'all' ? undefined : step === 'yes',
    book,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  return (
    <section aria-labelledby="sm-parallels">
      <h2 id="sm-parallels">{t.parallelsTitle}</h2>
      <p className="muted small">{t.parallelsLede}</p>
      <div className="toolbar">
        <Segmented<SmScope> label={t.scope.label} value={scope} options={(['across', 'every'] as const).map((v) => ({ value: v, label: t.scope[v] }))} onChange={(v) => set({ scope: v === 'across' ? null : v })} />
        <Segmented<SmStep> label={t.step3.label} value={step} options={(['all', 'yes', 'no'] as const).map((v) => ({ value: v, label: t.step3[v] }))} onChange={(v) => set({ step: v === 'all' ? null : v })} />
        <BookSelect label={m.search.book} all={m.search.allBooks} books={books.data} value={book} onChange={(v) => set({ book: v })} />
      </div>
      <p className="muted small">{t.limits}</p>
      <PagedList csv="sums-parallels" res={res} empty={t.empty} summary={(d, p, pages) => `${t.pairCount(d.total)} · ${t.pageOf(p, pages)}`}>
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((r) => (
              <ParallelItem key={`${r.a.verse_id}:${r.b.verse_id}:${r.a_tok_first}:${r.b_tok_first}`} r={r} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function ParallelItem({ r }: { r: SumsParallel }) {
  const { m } = useLocale()
  const t = m.sm
  return (
    <li className="hit sm-parallel">
      <div className="hit-head">
        <b>
          {m.num(r.a_value)} / {m.num(r.b_value)}
        </b>{' '}
        <span className="type-tag">{t.unit[r.unit] ?? r.unit}</span>{' '}
        {r.one_step !== null && <span className="muted small">{r.one_step ? t.known.oneStep : t.known.notOneStep}</span>}
      </div>
      <p className="hit-text">
        <Ref v={r.a} /> <HebrewText verse={r.a} highlight={span(r.a_tok_first, r.a_tok_last)} />
      </p>
      <p className="hit-text">
        <Ref v={r.b} /> <HebrewText verse={r.b} highlight={span(r.b_tok_first, r.b_tok_last)} />
      </p>
    </li>
  )
}
