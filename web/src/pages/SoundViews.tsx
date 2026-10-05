import { Link } from 'react-router'
import { useAlliteration, useRhymes } from '../api/hooks'
import type { Highlight } from '../lib/highlight'
import { HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const SOUND_NAMES: Record<string, string> = { sh: 'שׁ', s: 'שׂ' }
const soundName = (s: string) => SOUND_NAMES[s] ?? s

/** Cola whose content words share an initial sound, least likely first (candidates). */
export function AlliterationView({ book }: { book?: number }) {
  const { m, locale } = useLocale()
  const t = m.pat.sound
  const [params, update] = useQueryParams()
  const page = parsePage(params.get('page'))
  const res = useAlliteration({ book, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  return (
    <>
      <p className="lede">{t.alliterationLede}</p>
      <p className="muted small">{t.alliterationNote}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{t.empty}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.pat.cola(res.data.total)} · {m.pat.pageOf(page, pages)}
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((a) => {
              const marks: Highlight = new Map(a.words.map((i) => [i, 'focus']))
              return (
                <li key={`${a.verse.verse_id}:${a.colon}`} className="disc">
                  <div className="hit-head">
                    <span className="pun he" dir="rtl" lang="he">
                      {soundName(a.sound)} ×{a.count}
                    </span>
                    <span className="muted small">
                      {t.ofWords(a.n_words, a.p < 0.001 ? a.p.toExponential(1) : a.p.toFixed(3))}
                    </span>
                  </div>
                  <div className="disc-side">
                    <Link className="hit-ref" to={unitLink(`v:${a.verse.verse_id}`, '?halves=1')}>
                      {locale === 'he' ? a.label_he : a.label}
                    </Link>
                    <p className="hit-text">
                      <HebrewText verse={a.verse} highlight={marks} />
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}

/** Runs of consecutive cola whose last words end alike. */
export function RhymeView({ book }: { book?: number }) {
  const { m, locale } = useLocale()
  const t = m.pat.sound
  const [params, update] = useQueryParams()
  const page = parsePage(params.get('page'))
  const all = params.get('rq') === 'all'
  const res = useRhymes({ book, maxQ: all ? undefined : 0.05, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  return (
    <>
      <p className="lede">{t.rhymeLede}</p>
      <div className="toolbar">
        <label className="check">
          <input
            type="checkbox"
            checked={all}
            onChange={(e) => update({ rq: e.target.checked ? 'all' : null, page: null })}
          />
          {m.pat.includeQ}
        </label>
      </div>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>{t.rhymeEmpty}</EmptyList>
      ) : (
        <>
          <p className="muted small">
            {m.pat.runs(res.data.total)} · {m.pat.pageOf(page, pages)}
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((r) => (
              <li key={`${r.start_vid}:${r.ending}`} className="disc">
                <div className="hit-head">
                  <span className="pun he" dir="rtl" lang="he">
                    ‑{r.ending} ×{r.n_cola}
                  </span>
                  <span className={`small ${r.q <= 0.05 ? 'q-strong' : 'muted'}`}>{m.q(r.q)}</span>
                  <Link className="hit-ref" to={unitLink(`v:${r.start_vid}`, '?halves=1')}>
                    {locale === 'he' ? r.label_he : r.label}
                  </Link>
                </div>
                {r.verses.map((v) => {
                  const marks: Highlight = new Map(
                    r.members.filter(([vid]) => vid === v.verse_id).map(([, i]) => [i, 'focus']),
                  )
                  return (
                    <p key={v.verse_id} className="hit-text">
                      <span className="verse-num">{v.verse}</span> <HebrewText verse={v} highlight={marks} />
                    </p>
                  )
                })}
              </li>
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}
