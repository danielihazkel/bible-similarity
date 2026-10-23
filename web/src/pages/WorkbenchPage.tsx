import { useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useCheck, useContrast, useNotebook } from '../api/hooks'
import type { Book, CheckResponse, ContrastResponse, ContrastRow, SetProblem, SetSummary, WorkbenchFeature, WorkbenchWithin } from '../api/types'
import { Segmented } from '../components/Controls'
import { DomainName } from '../components/DomainName'
import { ExportCsv } from '../components/ExportCsv'
import { useLocale } from '../context/localeContext'
import { domainLink, lemmaLink, rootLink, unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'
import { addItem, formatP, joinSet, parseRange, patternFor, removeItem, splitSet, type SetItem } from '../lib/workbench'

const FEATURES: WorkbenchFeature[] = ['lemma', 'root', 'domain', 'pos', 'stem', 'form', 'person', 'function', 'clause']
const WITHINS: WorkbenchWithin[] = ['book', 'chapter', 'corpus']
const ALPHA = 0.05

type Tab = 'contrast' | 'check'

/** The workbench (§16.64): two sets of verses contrasted value by value, or a pattern checked on a
 * set against the set's verses drawn again around it. Sets and queries live in the URL. */
export function WorkbenchPage() {
  const { m } = useLocale()
  const t = m.wb
  const [params, update] = useQueryParams()
  const tab: Tab = params.get('tab') === 'check' ? 'check' : 'contrast'
  return (
    <div className="page workbench-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <Segmented
        label={t.tabsLabel}
        value={tab}
        options={(['contrast', 'check'] as Tab[]).map((v) => ({ value: v, label: t.tabs[v] }))}
        onChange={(v) => update({ tab: v === 'contrast' ? null : v }, false)}
      />
      {tab === 'contrast' ? <ContrastView /> : <CheckView />}
      <details className="query-help">
        <summary>{t.syntaxTitle}</summary>
        <ul>
          {t.syntax.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}

function ContrastView() {
  const { m } = useLocale()
  const t = m.wb
  const [params, update] = useQueryParams()
  const a = params.get('a') ?? ''
  const b = params.get('b') ?? ''
  const fp = params.get('feature') as WorkbenchFeature | null
  const feature: WorkbenchFeature = fp && FEATURES.includes(fp) ? fp : 'lemma'
  const res = useContrast({ a, b, feature })
  const d = res.data
  return (
    <>
      <div className="wb-sets">
        <SetEditor name={t.setA} spec={a} onChange={(s) => update({ a: s || null }, false)} allowOnly />
        <SetEditor name={t.setB} spec={b} onChange={(s) => update({ b: s || null }, false)} allowOnly emptyText={t.emptyB} hint={t.restHint} />
      </div>
      <label className="control">
        <span>{t.feature}</span>
        <select value={feature} onChange={(e) => update({ feature: e.target.value === 'lemma' ? null : e.target.value }, false)}>
          {FEATURES.map((f) => (
            <option key={f} value={f}>
              {t.features[f]}
            </option>
          ))}
        </select>
      </label>
      {!a.trim() ? (
        <p className="status">{t.promptA}</p>
      ) : res.isError ? (
        <p className="status error" role="alert">
          {res.error.message}
        </p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : d.error ? (
        <Problem problem={d.error} />
      ) : (
        <ContrastResult d={d} stale={res.isPlaceholderData} />
      )}
    </>
  )
}

function ContrastResult({ d, stale }: { d: ContrastResponse; stale: boolean }) {
  const t = useLocale().m.wb
  const rows = () =>
    (['a', 'b'] as const).flatMap((side) =>
      (side === 'a' ? d.over_a : d.over_b).map((r) => ({
        side: side.toUpperCase(),
        value: r.key,
        label: r.label ?? '',
        a: r.a,
        b: r.b,
        rate_a: r.rate_a,
        rate_b: r.rate_b,
        log2_ratio: r.log_ratio,
        g2: r.g2,
        p: r.p,
        q: r.q,
      })),
    )
  return (
    <section className={stale ? 'stale' : undefined} aria-busy={stale}>
      <p className="wb-counts">
        {d.a && <SetCount name={t.setA} s={d.a} />}
        {d.b && <SetCount name={t.setB} s={d.b} />}
      </p>
      <p>
        {t.summary(d.tested, d.significant_a, d.significant_b)}
        {d.overlap > 0 && ` ${t.overlap(d.overlap)}`}
        {' · '}
        <ExportCsv filename={`workbench-${d.feature}.csv`} rows={rows} />
      </p>
      <div className="wb-sides">
        <Side title={t.overA} rows={d.over_a} feature={d.feature} side="a" />
        <Side title={t.overB} rows={d.over_b} feature={d.feature} side="b" />
      </div>
      <p className="muted small">{t.method}</p>
    </section>
  )
}

function SetCount({ name, s }: { name: string; s: SetSummary }) {
  const t = useLocale().m.wb
  return (
    <span className="wb-count">
      <strong>{t.inSet(name)}</strong>
      {t.setCount(s.verses, s.words)}
      {s.filtered && ` (${t.partWords})`}
    </span>
  )
}

function Side({ title, rows, feature, side }: { title: string; rows: ContrastRow[]; feature: WorkbenchFeature; side: 'a' | 'b' }) {
  const { m, locale } = useLocale()
  const t = m.wb
  return (
    <section className="wb-side">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="muted">{t.none}</p>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={title}>
          <table className="change-table wb-table">
            <thead>
              <tr>
                <th>{t.cols.value}</th>
                <th className="num">{t.cols.a}</th>
                <th className="num">{t.cols.b}</th>
                <th className="num" title={t.ratioTitle}>
                  {t.cols.ratio}
                </th>
                <th className="num">{t.cols.g2}</th>
                <th className="num">{t.cols.q}</th>
                <th>{t.cols.verses}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const find = patternFor(feature, r.key)
                return (
                  <tr key={r.key} className={r.q <= ALPHA ? 'wb-sig' : undefined}>
                    <td>
                      <Value feature={feature} row={r} />
                      {find && (
                        <>
                          {' '}
                          <Link className="small" to={`/query?q=${encodeURIComponent(find)}`} title={t.findTitle}>
                            {t.find}
                          </Link>
                        </>
                      )}
                    </td>
                    <Count n={r.a} rate={r.rate_a} />
                    <Count n={r.b} rate={r.rate_b} />
                    <td className="num">{t.ratio(side === 'a' ? r.log_ratio : -r.log_ratio)}</td>
                    <td className="num">{r.g2.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US', { maximumFractionDigits: 1 })}</td>
                    <td className="num">{formatP(r.q)}</td>
                    <td className="wb-examples">
                      {r.examples.map((e, i) => (
                        <span key={e.verse_id}>
                          {i > 0 && ', '}
                          <Link to={unitLink(`v:${e.verse_id}`)}>{locale === 'he' ? e.label_he : e.label}</Link>
                        </span>
                      ))}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function Count({ n, rate }: { n: number; rate: number }) {
  const { m, locale } = useLocale()
  const num = n.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US', { maximumFractionDigits: 1 })
  return (
    <td className="num">
      {num}
      <br />
      <span className="muted small">{m.wb.perThousand(rate)}</span>
    </td>
  )
}

function Value({ feature, row }: { feature: WorkbenchFeature; row: ContrastRow }) {
  if (feature === 'domain') {
    return (
      <Link to={domainLink(row.key)}>
        <DomainName domain={{ code: row.key, label_en: row.label ?? row.key }} />
      </Link>
    )
  }
  if (feature === 'lemma' || feature === 'root') {
    return (
      <Link to={feature === 'lemma' ? lemmaLink(row.key) : rootLink(row.key)}>
        <span dir="rtl" lang="he" className="he">
          {row.label ?? row.key}
        </span>
      </Link>
    )
  }
  return (
    <code dir="ltr">
      {row.key}
    </code>
  )
}

function CheckView() {
  const { m, locale } = useLocale()
  const t = m.wb
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const set = params.get('set') ?? ''
  const wp = params.get('within') as WorkbenchWithin | null
  const within: WorkbenchWithin = wp && WITHINS.includes(wp) ? wp : 'book'
  const res = useCheck({ q, set, within })
  const d = res.data
  return (
    <>
      <PatternForm key={q} initial={q} onSubmit={(text) => update({ q: text.trim() || null }, false)} />
      <SetEditor name={t.set} spec={set} onChange={(s) => update({ set: s || null }, false)} />
      <Segmented
        label={t.within}
        value={within}
        options={WITHINS.map((w) => ({ value: w, label: t.withins[w] }))}
        onChange={(w) => update({ within: w === 'book' ? null : w }, false)}
      />
      {!q.trim() || !set.trim() ? (
        <p className="status">{t.checkPrompt}</p>
      ) : res.isError ? (
        <p className="status error" role="alert">
          {res.error.message}
        </p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : d.pattern_error ? (
        <p className="status error" role="alert">
          {m.qry.errors[d.pattern_error.code](d.pattern_error.token)}
        </p>
      ) : d.error ? (
        <Problem problem={d.error} />
      ) : (
        <CheckResult d={d} stale={res.isPlaceholderData} locale={locale} />
      )}
    </>
  )
}

function CheckResult({ d, stale, locale }: { d: CheckResponse; stale: boolean; locale: string }) {
  const t = useLocale().m.wb
  const books = useBooks()
  const byId = new Map((books.data ?? []).map((b) => [b.book_id, b]))
  const verdict =
    d.p_high <= ALPHA ? t.denser(formatP(d.p_high)) : d.p_low <= ALPHA ? t.sparser(formatP(d.p_low)) : t.chance(formatP(d.p_high), formatP(d.p_low))
  const num = (x: number) => x.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US', { maximumFractionDigits: 2 })
  return (
    <section className={stale ? 'stale wb-check' : 'wb-check'} aria-busy={stale}>
      <p>{t.found(d.matches, d.set?.verses ?? 0, d.words, d.rate)}</p>
      {d.testable ? (
        <>
          <p>{t.null(d.within, d.draws, d.null_mean, d.null_low, d.null_high)}</p>
          <p className="wb-verdict">
            <strong>{verdict}</strong>
          </p>
          <p className="muted">{t.rest(d.rest_rate, d.rest_matches, d.rest_words)}</p>
          {d.fixed_verses > 0 && <p className="muted small">{t.fixed(d.fixed_verses)}</p>}
        </>
      ) : (
        <p className="status">{t.untestable}</p>
      )}
      {d.books.length > 1 && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.byBook}>
          <table className="change-table">
            <caption>{t.byBook}</caption>
            <thead>
              <tr>
                <th>{t.bookCols.book}</th>
                <th className="num">{t.bookCols.matches}</th>
                <th className="num">{t.bookCols.words}</th>
                <th className="num">{t.bookCols.rate}</th>
              </tr>
            </thead>
            <tbody>
              {d.books.map((b) => {
                const book = byId.get(b.book_id)
                return (
                  <tr key={b.book_id}>
                    <td>{book ? bookName(book, locale) : b.book_id}</td>
                    <td className="num">{num(b.matches)}</td>
                    <td className="num">{num(b.words)}</td>
                    <td className="num">{num(b.words ? (1000 * b.matches) / b.words : 0)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted small">{t.checkMethod}</p>
    </section>
  )
}

function PatternForm({ initial, onSubmit }: { initial: string; onSubmit: (text: string) => void }) {
  const t = useLocale().m.wb
  const [draft, setDraft] = useState(initial)
  return (
    <form
      className="search-form"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(draft)
      }}
    >
      <input
        className="search-input query-input"
        dir="ltr"
        type="text"
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder={t.patternPlaceholder}
        aria-label={t.queryLabel}
      />
      <button type="submit" className="primary">
        {t.run}
      </button>
    </form>
  )
}

function Problem({ problem }: { problem: SetProblem }) {
  const { m } = useLocale()
  const t = m.wb
  const name = problem.set === 'a' ? t.setA : problem.set === 'b' ? t.setB : t.set
  return (
    <div className="status error" role="alert">
      <p>
        {t.inSet(name)}
        {t.setErrors[problem.code](problem.token)}
      </p>
      {problem.pattern && <p>{m.qry.errors[problem.pattern.code](problem.pattern.token)}</p>}
    </div>
  )
}

// set editor

type Kind = 'book' | 'chapters' | 'section' | 'collection' | 'pattern' | 'only'

function SetEditor({
  name,
  spec,
  onChange,
  allowOnly = false,
  emptyText,
  hint,
}: {
  name: string
  spec: string
  onChange: (spec: string) => void
  allowOnly?: boolean
  emptyText?: string
  hint?: string
}) {
  const t = useLocale().m.wb
  const items = splitSet(spec)
  return (
    <fieldset className="wb-set">
      <legend>{name}</legend>
      {items.length === 0 ? (
        <p className="muted small">{emptyText ?? t.empty}</p>
      ) : (
        <ul className="wb-items">
          {items.map((it, i) => (
            <li key={`${i}:${it.kind}:${it.value}`} className="chip">
              <ItemLabel item={it} />
              <button type="button" className="linkish wb-remove" aria-label={t.remove(itemText(it))} onClick={() => onChange(removeItem(spec, i))}>
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      {hint && <p className="muted small">{hint}</p>}
      <AddItem name={name} allowOnly={allowOnly} onAdd={(it) => onChange(addItem(spec, it))} />
      <details className="wb-text">
        <summary>{t.asText}</summary>
        <SetText key={spec} name={name} spec={spec} onApply={(s) => onChange(joinSet(splitSet(s)))} />
      </details>
    </fieldset>
  )
}

const itemText = (it: SetItem) => (it.kind ? `${it.kind}:${it.value}` : it.value)

function ItemLabel({ item }: { item: SetItem }) {
  const { m, locale } = useLocale()
  const t = m.wb
  const books = useBooks()
  const notebook = useNotebook()
  const book = (id: string) => {
    const b = books.data?.find((x) => String(x.book_id) === id)
    return b ? bookName(b, locale) : id
  }
  switch (item.kind) {
    case 'book': {
      const r = parseRange(item.value)
      return <>{r && r[0] !== r[1] ? t.books(book(String(r[0])), book(String(r[1]))) : book(item.value)}</>
    }
    case 'chapters': {
      const [b, range] = item.value.split(':')
      return <>{t.chapters(book(b), (range ?? '').replace('-', '–'))}</>
    }
    case 'section':
      return <>{t.sections[item.value.toLowerCase()] ?? item.value}</>
    case 'only':
      return <>{t.only[item.value.toLowerCase()] ?? item.value}</>
    case 'collection': {
      const c = notebook.data?.collections.find((x) => String(x.collection_id) === item.value)
      return <>{c ? t.collectionName(c.name) : t.collectionId(item.value)}</>
    }
    case 'unit':
      return <>{t.unit(item.value)}</>
    case 'pattern':
      return <code dir="ltr">{item.value}</code>
    default:
      return <code dir="ltr">{itemText(item)}</code>
  }
}

function AddItem({ name, allowOnly, onAdd }: { name: string; allowOnly: boolean; onAdd: (it: SetItem) => void }) {
  const { m, locale } = useLocale()
  const t = m.wb
  const books = useBooks()
  const notebook = useNotebook()
  const kinds: Kind[] = ['book', 'chapters', 'section', 'collection', 'pattern', ...(allowOnly ? (['only'] as Kind[]) : [])]
  const [kind, setKind] = useState<Kind>('book')
  const [book, setBook] = useState('0')
  const [from, setFrom] = useState('1')
  const [to, setTo] = useState('')
  const [section, setSection] = useState('torah')
  const [collection, setCollection] = useState('')
  const [pattern, setPattern] = useState('')
  const [only, setOnly] = useState('speech')
  const collections = notebook.data?.collections ?? []
  const chosenBook: Book | undefined = books.data?.find((b) => String(b.book_id) === book)
  const item = (): SetItem | null => {
    switch (kind) {
      case 'book':
        return { kind, value: book }
      case 'chapters': {
        const a = Number(from)
        const b = to === '' ? a : Number(to)
        if (!Number.isInteger(a) || !Number.isInteger(b) || a < 1 || b < a) return null
        return { kind, value: `${book}:${a === b ? a : `${a}-${b}`}` }
      }
      case 'section':
        return { kind, value: section }
      case 'collection':
        return collection || collections[0] ? { kind, value: collection || String(collections[0].collection_id) } : null
      case 'pattern':
        return pattern.trim() ? { kind, value: pattern.trim() } : null
      case 'only':
        return { kind, value: only }
    }
  }
  const ready = item()
  const bookSelect = (
    <label className="control">
      <span>{t.book}</span>
      <select value={book} onChange={(e) => setBook(e.target.value)}>
        {(books.data ?? []).map((b) => (
          <option key={b.book_id} value={b.book_id}>
            {bookName(b, locale)}
          </option>
        ))}
      </select>
    </label>
  )
  return (
    <form
      className="wb-add"
      aria-label={`${t.kindLabel}: ${name}`}
      onSubmit={(e) => {
        e.preventDefault()
        if (ready) onAdd(ready)
      }}
    >
      <label className="control">
        <span>{t.kindLabel}</span>
        <select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {t.kinds[k]}
            </option>
          ))}
        </select>
      </label>
      {kind === 'book' && bookSelect}
      {kind === 'chapters' && (
        <>
          {bookSelect}
          <label className="control">
            <span>{t.fromChapter}</span>
            <input type="number" inputMode="numeric" min={1} max={chosenBook?.n_chapters} value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="control">
            <span>{t.toChapter}</span>
            <input type="number" inputMode="numeric" min={1} max={chosenBook?.n_chapters} value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
        </>
      )}
      {kind === 'section' && (
        <label className="control">
          <span>{t.kinds.section}</span>
          <select value={section} onChange={(e) => setSection(e.target.value)}>
            {Object.entries(t.sections).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      {kind === 'collection' &&
        (collections.length === 0 ? (
          <span className="muted small">{t.noCollections}</span>
        ) : (
          <label className="control">
            <span>{t.collection}</span>
            <select value={collection || String(collections[0].collection_id)} onChange={(e) => setCollection(e.target.value)}>
              {collections.map((c) => (
                <option key={c.collection_id} value={c.collection_id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        ))}
      {kind === 'pattern' && (
        <label className="control wb-pattern">
          <span>{t.patternLabel}</span>
          <input
            type="text"
            dir="ltr"
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            value={pattern}
            placeholder={t.patternPlaceholder}
            onChange={(e) => setPattern(e.target.value)}
          />
        </label>
      )}
      {kind === 'only' && (
        <label className="control">
          <span>{t.kinds.only}</span>
          <select value={only} onChange={(e) => setOnly(e.target.value)}>
            {Object.entries(t.only).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      <button type="submit" disabled={!ready}>
        {t.add}
      </button>
    </form>
  )
}

function SetText({ name, spec, onApply }: { name: string; spec: string; onApply: (spec: string) => void }) {
  const t = useLocale().m.wb
  const [draft, setDraft] = useState(spec)
  return (
    <form
      className="search-form"
      onSubmit={(e) => {
        e.preventDefault()
        onApply(draft)
      }}
    >
      <input
        className="search-input query-input"
        dir="ltr"
        type="text"
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        aria-label={t.textLabel(name)}
      />
      <button type="submit">{t.apply}</button>
    </form>
  )
}
