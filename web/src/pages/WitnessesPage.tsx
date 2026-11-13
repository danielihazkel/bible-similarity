import { Link } from 'react-router'
import { isStageMissing } from '../api/client'
import { useBooks, useUnit, useWitnesses, useWitnessPluses, useWitnessUnit } from '../api/hooks'
import type { ChronologyRow, OpCounts, WitnessesResponse, WitnessReading, WitnessVerse } from '../api/types'
import { Segmented } from '../components/Controls'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import type { WitnessKind } from '../i18n/pages/witnesses'
import '../i18n/pages/witnesses'
import { readLink, unitLink } from '../lib/links'
import { bookName, verseRef } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { parseKind, variantsPer100, witnessUrl } from '../lib/witnesses'
import '../i18n/pages/chronology'
import '../styles/pages/WitnessesPage.css'

const PAGE = 25
const SCROLLS = 15

/** Other witnesses (§16.78): the Samaritan Pentateuch and the Dead Sea Scrolls against the MT, word
 * by word; the largest pluses of one (`?kind=`), a unit's witnesses (`?unit=`), two chronologies. */
export function WitnessesPage() {
  const { m } = useLocale()
  const t = m.wt
  const res = useWitnesses()
  const [params, update] = useQueryParams()
  const kind = parseKind(params.get('kind'))
  const unit = params.get('unit') ?? undefined
  const d = res.data
  return (
    <div className="page witnesses-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">
        {t.sources} (
        <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noreferrer">
          {t.licence}
        </a>
        ){t.sourcesNote}
      </p>
      {isStageMissing(res.error) ? (
        <NotComputed>{t.notComputed}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <p>{t.described(d.samaritan.verses, d.scrolls.scrolls, d.scrolls.verses, d.scrolls.read)}</p>
          <Checks d={d} />
          {unit ? (
            <UnitWitnesses unit={unit} />
          ) : (
            <>
              <div className="toolbar">
                <Segmented<WitnessKind>
                  label={t.kindLabel}
                  value={kind}
                  options={[
                    { value: 'sp', label: t.sp },
                    { value: 'scroll', label: t.scrolls },
                  ]}
                  onChange={(k) => update({ kind: k === 'sp' ? null : k, page: null }, false)}
                />
              </div>
              <Pluses kind={kind} />
            </>
          )}
          <Chronology rows={d.chronology} />
          <Books d={d} />
          <Scrolls d={d} />
          <p className="muted small">{t.opsHint}</p>
          <p className="muted small">{t.limits(d.plus_min, d.max_unc)}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.wt
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function WitnessName({ w }: { w: string }) {
  const t = useLocale().m.wt
  return w === 'sp' ? <>{t.sp}</> : <span dir="ltr">{w}</span>
}

function Checks({ d }: { d: WitnessesResponse }) {
  const { m, locale } = useLocale()
  const t = m.wt
  return (
    <section aria-labelledby="wt-checks">
      <h2 id="wt-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.parallel.title} <Verdict holds={d.holds} />
          </h3>
          <p>{t.parallel.text(d.plus_in_parallel ?? 0, d.plus_elsewhere ?? 0, d.ratio, d.null_mean, d.p, d.shifts, d.parallel_verses)}</p>
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <ul className="wt-known">
            {d.known.map((k) => (
              <li key={`${k.witness}|${k.ref}`}>
                <WitnessName w={k.witness} />, {k.verse ? <Link to={witnessUrl({ unit: `v:${k.verse.verse_id}` })}>{verseRef(k.verse, locale)}</Link> : k.ref}:{' '}
                {k.plus !== null ? (
                  t.known.plus(k.plus)
                ) : (
                  <>
                    {t.known.reads}{' '}
                    <span lang="he" dir="rtl">
                      {k.reads}
                    </span>
                  </>
                )}
                {locale === 'en' && k.note && <span className="muted small"> ({k.note})</span>} <span className={k.found ? 'rc-found' : 'muted'}>({k.found ? t.known.found : t.known.missing})</span>
              </li>
            ))}
            {d.chronology_known.map((c) => (
              <li key={c.event}>
                {t.known.flood(c.year, c.expected)} <span className={c.holds ? 'rc-found' : 'muted'}>({c.holds ? t.known.found : t.known.missing})</span>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  )
}

function Pluses({ kind }: { kind: WitnessKind }) {
  const { m, locale } = useLocale()
  const t = m.wt
  const [params] = useQueryParams()
  const page = parsePage(params.get('page'))
  const res = useWitnessPluses(kind, undefined, PAGE, (page - 1) * PAGE)
  return (
    <section aria-labelledby="wt-pluses">
      <h2 id="wt-pluses">{t.plusesTitle}</h2>
      <p className="muted small">{t.plusesHint}</p>
      <PagedList csv="witness-pluses" res={res} empty={t.unitNone}>
        {(d, stale) => (
          <ol className={`wt-pluses rc-verses ${stale}`} start={(page - 1) * PAGE + 1}>
            {d.items.map((v) => (
              <li key={`${v.witness}|${v.verse.verse_id}`}>
                <Link to={witnessUrl({ unit: `v:${v.verse.verse_id}` })}>{verseRef(v.verse, locale)}</Link> <span className="rc-n">{t.plusOf(v.plus)}</span>{' '}
                <span className="muted small">
                  <WitnessName w={v.witness} />
                </span>
                <p className="hit-text he" dir="rtl" lang="he">
                  {v.verse.text_display}
                </p>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function UnitWitnesses({ unit }: { unit: string }) {
  const { m, locale } = useLocale()
  const t = m.wt
  const [params] = useQueryParams()
  const page = parsePage(params.get('vpage'))
  const detail = useUnit(unit)
  const res = useWitnessUnit(unit, PAGE, (page - 1) * PAGE)
  const u = detail.data?.unit
  return (
    <section aria-labelledby="wt-unit" className="wt-unit">
      <h2 id="wt-unit">{t.unitTitle(u ? (locale === 'he' ? u.label_he : u.label_en) : unit)}</h2>
      <p className="small">
        <Link to="/witnesses">{t.allVerses}</Link>
        {u && (
          <>
            {' · '}
            <Link to={readLink(u.unit_type === 'verse' ? `c:${u.book_id}:${detail.data!.verses[0].chapter}` : u.unit_id, '?layers=witnesses')}>{t.readWith}</Link>
          </>
        )}
      </p>
      {detail.isError ? (
        <ErrorBox error={detail.error} />
      ) : (
        <PagedList pageParam="vpage" res={res} empty={t.unitNone}>
          {(d, stale) => (
            <div className={stale}>
              <OpsKey />
              {d.items.map((v) => (
                <VerseWitnesses key={v.verse.verse_id} v={v} />
              ))}
            </div>
          )}
        </PagedList>
      )}
    </section>
  )
}

function OpsKey() {
  const t = useLocale().m.wt
  return (
    <p className="dv-legend small" role="group" aria-label={t.legend}>
      <span>{t.legend}:</span>
      {(['spelling', 'form', 'substitution', 'added'] as const).map((op) => (
        <span key={op} className={`wt-w wt-${op}`}>
          {t.ops[op]}
        </span>
      ))}
      <span className="wt-w wt-unread">{t.unread}</span>
    </p>
  )
}

function VerseWitnesses({ v }: { v: WitnessVerse }) {
  const { locale } = useLocale()
  const t = useLocale().m.wt
  return (
    <div className="wt-verse">
      <h3>
        <Link to={unitLink(`v:${v.verse.verse_id}`)}>{verseRef(v.verse, locale)}</Link>
      </h3>
      <dl className="wt-lines">
        <dt>{t.mt}</dt>
        <dd className="he" dir="rtl" lang="he">
          {v.verse.text_display}
        </dd>
        {v.readings.map((r) => (
          <Reading key={r.witness} r={r} tokens={v.verse.display_tokens} />
        ))}
      </dl>
    </div>
  )
}

function Reading({ r, tokens }: { r: WitnessReading; tokens: string[] }) {
  const t = useLocale().m.wt
  return (
    <>
      <dt>
        <WitnessName w={r.witness} />
      </dt>
      <dd>
        <span className="he wt-text" dir="rtl" lang="he">
          {r.words.map((w, i) => (
            <span key={i}>
              {i > 0 && ' '}
              <span className={`wt-w${w.r ? '' : ' wt-unread'}${w.op && w.op !== 'same' && w.r ? ` wt-${w.op}` : ''}`} title={w.op && w.r ? t.ops[w.op] : !w.r ? t.unread : undefined}>
                {w.t}
              </span>
            </span>
          ))}
        </span>
        {r.missing.length > 0 && (
          <span className="small wt-lacks">
            {' '}
            · {t.lacks}:{' '}
            <span className="he wt-omitted" dir="rtl" lang="he">
              {r.missing.map((k) => tokens[k] ?? '').join(' ')}
            </span>
          </span>
        )}
      </dd>
    </>
  )
}

function Chronology({ rows }: { rows: ChronologyRow[] }) {
  const { m, locale } = useLocale()
  const t = m.wt
  const flood = rows.find((r) => r.event === 'flood')?.sp_year
  const label = (r: ChronologyRow) => (r.name ? (r.death ? m.ch.died(r.name) : m.ch.born(r.name)) : (m.ch.events[r.event] ?? r.event))
  return (
    <section aria-labelledby="wt-chron">
      <h2 id="wt-chron">{t.chronTitle}</h2>
      <p className="muted small">{t.chronHint}</p>
      <TableCsv name="witnesses-chronology" tabIndex={0} role="region" aria-labelledby="wt-chron">
        <table className="change-table wt-chron">
          <thead>
            <tr>
              <th scope="col">{t.chronCols.event}</th>
              <th scope="col">{t.chronCols.verse}</th>
              <th scope="col">{t.chronCols.mt}</th>
              <th scope="col">{t.chronCols.sp}</th>
              <th scope="col">{t.chronCols.gap}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.seq} className={r.death && r.sp_year === flood ? 'wt-flood' : undefined}>
                <th scope="row">{label(r)}</th>
                <td>{r.verse_id !== null ? <Link to={witnessUrl({ unit: `v:${r.verse_id}` })}>{locale === 'he' ? r.ref_he : r.ref}</Link> : '—'}</td>
                <td className="num">{r.mt_year !== null ? m.num(r.mt_year) : '—'}</td>
                <td className="num">{m.num(r.sp_year)}</td>
                <td className="num" dir="ltr">
                  {r.mt_year !== null && r.sp_year !== r.mt_year ? (r.sp_year > r.mt_year ? '+' : '−') + m.num(Math.abs(r.sp_year - r.mt_year)) : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function Books({ d }: { d: WitnessesResponse }) {
  const { m, locale } = useLocale()
  const t = m.wt
  const books = useBooks()
  const byId = new Map((books.data ?? []).map((x) => [x.book_id, x]))
  return (
    <section aria-labelledby="wt-books">
      <h2 id="wt-books">{t.booksTitle}</h2>
      <TableCsv name="witnesses-books" tabIndex={0} role="region" aria-labelledby="wt-books">
        <table className="change-table">
          <thead>
            <tr>
              <th scope="col">{t.kindLabel}</th>
              <th scope="col">{t.cols.book}</th>
              <th scope="col">{t.cols.verses}</th>
              <th scope="col">{t.cols.read}</th>
              <th scope="col">{t.cols.variants}</th>
              <th scope="col">{t.cols.pluses}</th>
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => {
              const book = byId.get(b.book_id)
              return (
                <tr key={`${b.kind}|${b.book_id}`}>
                  <td>{b.kind === 'sp' ? t.sp : t.scrolls}</td>
                  <th scope="row">{book ? bookName(book, locale) : b.book_id}</th>
                  <td className="num">{m.num(b.verses)}</td>
                  <td className="num">{m.num(b.read)}</td>
                  <td className="num">{variantsPer100(b, b.read)}</td>
                  <td className="num">{m.num(b.pluses)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function Scrolls({ d }: { d: WitnessesResponse }) {
  const { m, locale } = useLocale()
  const t = m.wt
  const books = useBooks()
  const byId = new Map((books.data ?? []).map((x) => [x.book_id, x]))
  const rows = d.scroll_rows.slice(0, SCROLLS)
  return (
    <section aria-labelledby="wt-scrolls">
      <h2 id="wt-scrolls">{t.scrollsTitle}</h2>
      <p className="muted small">{t.scrollsHint(rows.length)}</p>
      <TableCsv name="witnesses-scrolls" tabIndex={0} role="region" aria-labelledby="wt-scrolls">
        <table className="change-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.scroll}</th>
              <th scope="col">{t.cols.book}</th>
              <th scope="col">{t.cols.verses}</th>
              <th scope="col">{t.cols.read}</th>
              <th scope="col">{t.cols.variants}</th>
              <th scope="col">{t.cols.pluses}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => {
              const book = byId.get(s.book_id)
              return (
                <tr key={s.scroll}>
                  <th scope="row" dir="ltr">
                    {s.scroll}
                  </th>
                  <td>{book ? bookName(book, locale) : s.book_id}</td>
                  <td className="num">{m.num(s.verses)}</td>
                  <td className="num">{m.num(s.read)}</td>
                  <td className="num">{variantsPer100(s as OpCounts, s.read)}</td>
                  <td className="num">{m.num(s.pluses)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

