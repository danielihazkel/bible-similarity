import { useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useVoice, useVoices } from '../api/hooks'
import type { AuthorCheck, Book, VoiceSpeaker } from '../api/types'
import { Heatmap } from '../components/BookHeatmap'
import { FeatureBars } from '../components/FeatureBars'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { hebrewNumeral } from '../lib/hebrew'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const fmtQ = (q: number) => (q < 0.001 ? '< 0.001' : q.toFixed(3))

/** Do speakers have a style of their own? Speech profiled per speaker (DESIGN.md §16.28). */
export function VoicesView() {
  const { m, locale } = useLocale()
  const t = m.syn.voices
  const [params, update] = useQueryParams()
  const voice = params.get('voice') ?? undefined
  const books = useBooks()
  const res = useVoices()
  const [pair, setPair] = useState<string | null>(null)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { meta, speakers, pairs } = res.data
  if (speakers.length === 0) return <p className="status">{t.noData}</p>
  const byOsis = new Map(books.data?.map((b) => [b.osis, b]) ?? [])
  const byId = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const bookOf = (b: Book | undefined, fallback: string) => (b ? bookName(b, locale) : fallback)
  const names = new Map<string, string>([['divine', t.divine], ['narrator', t.narrator], ['unattributed', t.unattributed]])
  for (const s of speakers) if (s.he) names.set(s.key, s.he)
  const name = (k: string) => names.get(k) ?? k
  const deltas = new Map<string, number>()
  for (const p of pairs) {
    deltas.set(`${p.a}-${p.b}`, p.delta)
    deltas.set(`${p.b}-${p.a}`, p.delta)
  }
  const values = pairs.map((p) => p.delta)
  const [lo, hi] = [Math.min(...values), Math.max(...values)]
  const order = meta.order ?? [...speakers.map((s) => s.key), 'narrator', 'unattributed']
  const cal = meta.calibration
  const sens = meta.sensitivity
  return (
    <div className="voices-view">
      <p className="lede">{t.lede}</p>
      <p className="small">
        {t.summary(speakers.length, meta.significant ?? 0)}
        {cal && ` ${t.calibration(cal.significant, cal.of)}`}
        {sens?.rho != null && ` ${t.rho(sens.rho.toFixed(2), sens.speakers)}`}
      </p>
      <p className="muted small">{t.reliability}</p>

      {meta.checks && (
        <section aria-label={t.checks} className="voice-checks">
          <h2>{t.checks}</h2>
          <ul>
            {meta.checks.author.map((c) => (
              <AuthorLine
                key={`${c.speaker}-${c.a.join()}`}
                c={c}
                who={name(c.speaker)}
                books={(osis) => osis.map((o) => bookOf(byOsis.get(o), o)).join(locale === 'he' ? ' ו' : ' + ')}
              />
            ))}
            {meta.checks.distinct.map((c) => (
              <li key={`${c.book}-${c.speaker}`}>
                {t.distinct(name(c.speaker), bookOf(byOsis.get(c.book), c.book), c.rank, c.of)}
                <span className="muted small">
                  {' '}
                  · {c.ranking.map((r) => `${name(r.key)} ${r.effect.toFixed(1)}`).join(' · ')}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-label={t.speakers}>
        <h2>{t.speakers}</h2>
        <div className="table-wrap">
          <table className="change-table voice-table">
            <thead>
              <tr>
                <th>{t.cols.speaker}</th>
                <th>{t.cols.book}</th>
                <th className="num">{t.cols.words}</th>
                <th className="num">{t.cols.delta}</th>
                <th className="num" title={t.effectTitle}>
                  {t.cols.effect}
                </th>
                <th className="num">{t.cols.q}</th>
              </tr>
            </thead>
            <tbody>
              {speakers.map((s) => (
                <SpeakerRow
                  key={s.key}
                  s={s}
                  name={name(s.key)}
                  book={bookOf(byId.get(s.main_book), String(s.main_book))}
                  on={voice === s.key}
                  onPick={() => update({ voice: voice === s.key ? null : s.key }, false)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {voice ? <VoiceProfile voiceKey={voice} name={name} /> : <p className="muted small">{t.select}</p>}

      <section aria-label={t.matrix}>
        <h2>{t.matrix}</h2>
        <p className="muted small">{t.matrixLede}</p>
        <Heatmap
          names={names}
          order={order}
          value={(a, b) => {
            const d = deltas.get(`${a}-${b}`)
            return d === undefined || hi === lo ? undefined : 1 - (d - lo) / (hi - lo)
          }}
          title={(a, b) => t.pair(name(a), name(b), (deltas.get(`${a}-${b}`) ?? 0).toFixed(2))}
          selected={pair}
          onSelect={(k) => {
            setPair(k)
            const a = k?.split('-')[0]
            if (a && speakers.some((s) => s.key === a)) update({ voice: a }, false)
          }}
          label={t.matrix}
        />
      </section>
    </div>
  )
}

function AuthorLine({ c, who, books }: { c: AuthorCheck; who: string; books: (osis: string[]) => string }) {
  const t = useLocale().m.syn.voices
  return (
    <li>
      <strong>{t.author(who, books(c.a), books(c.b))}</strong>: {t.verdicts[c.verdict] ?? c.verdict}
      <span className="muted small">
        {' '}
        · {t.authorNums(c.cross.toFixed(3), fmtQ(c.p_cross), c.d_ab.toFixed(2), fmtQ(c.p_ab), c.words_a, c.words_b)}
      </span>
    </li>
  )
}

function SpeakerRow({ s, name, book, on, onPick }: { s: VoiceSpeaker; name: string; book: string; on: boolean; onPick: () => void }) {
  const t = useLocale().m.syn.voices
  return (
    <tr className={on ? 'on' : undefined}>
      <td>
        <button type="button" className="linkish" aria-pressed={on} onClick={onPick}>
          <span lang="he" dir="rtl">
            {name}
          </span>
        </button>
      </td>
      <td>{book}</td>
      <td className="num" title={t.explicit(s.n_explicit, s.n_words)}>
        {s.n_words.toLocaleString()}
      </td>
      <td className="num" title={t.deltaTitle(s.delta.toFixed(3), s.null_mean.toFixed(3))}>
        {s.delta.toFixed(2)}
      </td>
      <td className="num">{s.effect.toFixed(1)}</td>
      <td className="num">{fmtQ(s.q)}</td>
    </tr>
  )
}

function VoiceProfile({ voiceKey, name }: { voiceKey: string; name: (k: string) => string }) {
  const { m, locale } = useLocale()
  const t = m.syn.voices
  const books = useBooks()
  const res = useVoice(voiceKey)
  const who = name(voiceKey)
  if (res.error) return <PanelError what={t.profile(who)} error={res.error} />
  if (!res.data) return <Loading />
  const d = res.data
  const byId = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  return (
    <section className="book-profile voice-profile" aria-label={t.profile(who)}>
      <h2>{t.profile(who)}</h2>
      <FeatureBars title={t.more} items={d.features.filter((f) => f.side === 'over')} />
      <FeatureBars title={t.less} items={d.features.filter((f) => f.side === 'under')} />
      <p className="small">
        <span className="muted">{t.nearest}</span>{' '}
        {d.nearest
          .slice(0, 5)
          .map((p) => `${name(p.b)} (${p.delta.toFixed(2)})`)
          .join(', ')}
      </p>
      <h3>{t.chapters}</h3>
      <ul className="inline-list small">
        {d.chapters.map((c) => {
          const b = byId.get(c.book_id)
          const bn = b ? bookName(b, locale) : String(c.book_id)
          return (
            <li key={c.unit_id}>
              <Link to={unitLink(c.unit_id, '?syntax=1')}>
                {locale === 'he' ? `${bn} ${hebrewNumeral(c.chapter)}` : `${bn} ${c.chapter}`}
              </Link>{' '}
              <span className="muted">({t.clauses(c.n_clauses)})</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
