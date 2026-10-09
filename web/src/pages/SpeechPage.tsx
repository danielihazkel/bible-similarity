import { Link } from 'react-router'
import { useBooks, useSpeech, useSpeechBook } from '../api/hooks'
import type { SpeakerInfo, SpeechShares } from '../api/types'
import { Segmented } from '../components/Controls'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { hebrewNumeral } from '../lib/hebrew'
import { lemmaLink, unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { useQueryParams } from '../lib/urlState'
import { VoicesView } from './VoicesView'

const PARTS = ['narration', 'divine', 'other', 'unattributed', 'discourse'] as const
type Part = (typeof PARTS)[number]

function parts(s: SpeechShares): Record<Part, number> {
  return {
    narration: s.narration,
    divine: s.divine,
    other: Math.max(0, s.attributed - s.divine),
    unattributed: Math.max(0, s.speech - s.attributed),
    discourse: s.discourse,
  }
}

const pct = (x: number) => Math.round(x * 100)

type View = 'books' | 'voices'

/** Who speaks: narration, direct speech and its speakers per book and chapter (DESIGN.md §16.26),
 * and the speakers' voices (§16.28). */
export function SpeechPage() {
  const t = useLocale().m.syn
  const [params, update] = useQueryParams()
  const view: View = params.get('view') === 'voices' ? 'voices' : 'books'
  return (
    <div className="page speech-page">
      <h1>{t.title}</h1>
      <Segmented<View>
        label={t.view}
        value={view}
        onChange={(v) => update({ view: v === 'books' ? null : v, voice: null, book: null })}
        options={(['books', 'voices'] as const).map((v) => ({ value: v, label: t.tabs[v] }))}
      />
      {view === 'voices' ? <VoicesView /> : <SpeechBooks />}
    </div>
  )
}

function SpeechBooks() {
  const { m, locale } = useLocale()
  const t = m.syn
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  const res = useSpeech()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const names = new Map(books.data?.map((b) => [b.book_id, bookName(b, locale)]) ?? [])
  const sp = (res.data.meta.speaker ?? null) as Record<string, number> | null
  return (
    <>
      <p className="lede">{t.lede}</p>
      {sp && <p className="muted small">{t.caveat(sp.explicit ?? 0, sp.carried ?? 0, sp.enclosing ?? 0, sp.unknown ?? 0)}</p>}
      {res.data.books.length === 0 ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Legend />
          <section aria-label={t.books}>
            <h2>{t.books}</h2>
            <ul className="speech-bars">
              {res.data.books.map((b) => {
                const name = names.get(b.book_id) ?? String(b.book_id)
                const on = book === b.book_id
                return (
                  <li key={b.book_id}>
                    <button
                      type="button"
                      className={on ? 'on' : undefined}
                      aria-pressed={on}
                      onClick={() => update({ book: on ? null : String(b.book_id) }, false)}
                    >
                      <span className="bar-label">{name}</span>
                      <Stack s={b} />
                      <span className="small speakers-top">{b.speakers.map((s) => s.he).join(' · ')}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
          {book !== undefined && <BookSpeech bookId={book} name={names.get(book) ?? String(book)} />}
        </>
      )}
    </>
  )
}

function Legend() {
  const t = useLocale().m.syn
  return (
    <ul className="speech-legend small">
      {PARTS.map((p) => (
        <li key={p}>
          <span className={`swatch sp-${p}`} aria-hidden="true" />
          {t.legend[p]}
        </li>
      ))}
    </ul>
  )
}

function Stack({ s }: { s: SpeechShares }) {
  const t = useLocale().m.syn
  const p = parts(s)
  const label = PARTS.map((k) => t.share(t.legend[k], pct(p[k]))).join(', ')
  return (
    <span className="speech-stack" role="img" aria-label={label} title={label}>
      {PARTS.map((k) => (
        <span key={k} className={`sp-${k}`} style={{ width: `${p[k] * 100}%` }} />
      ))}
    </span>
  )
}

function BookSpeech({ bookId, name }: { bookId: number; name: string }) {
  const { m, locale } = useLocale()
  const t = m.syn
  const res = useSpeechBook(bookId)
  if (res.error) return <PanelError what={t.chapters(name)} error={res.error} />
  if (!res.data) return <Loading />
  return (
    <>
      <section aria-label={t.speakersOf(name)}>
        <h2>{t.speakersOf(name)}</h2>
        <ul className="speaker-list">
          {res.data.speakers.map((s) => (
            <Speaker key={s.lemma} s={s} />
          ))}
        </ul>
      </section>
      <section aria-label={t.chapters(name)}>
        <h2>{t.chapters(name)}</h2>
        <ul className="speech-bars">
          {res.data.chapters.map((c) => (
            <li key={c.unit_id}>
              <span className="speech-row">
                <Link to={unitLink(c.unit_id, '?syntax=1')}>
                  {locale === 'he' ? `${name} ${hebrewNumeral(c.chapter)}` : `${name} ${c.chapter}`}
                </Link>
                <Stack s={c} />
                <span className="muted small">{t.words(c.n_words)}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}

function Speaker({ s }: { s: SpeakerInfo }) {
  const t = useLocale().m.syn
  return (
    <li>
      <Link to={lemmaLink(s.lemma)} lang="he" dir="rtl">
        {s.he}
      </Link>{' '}
      <span className="muted small" title={t.explicitShare(s.n_explicit, s.n_words)}>
        {t.words(s.n_words)}
      </span>
    </li>
  )
}
