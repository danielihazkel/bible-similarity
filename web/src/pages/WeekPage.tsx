import { Link } from 'react-router'
import { useDossier, useWeek } from '../api/hooks'
import type { WeekParasha, WeekResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { DossierBar } from '../components/DossierBar'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import type { WkPlace } from '../i18n/pages/week'
import { readLink, unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'
import { isIsoDate, localToday, longDate } from '../lib/week'

/** This week's parasha (§11.1): the coming Shabbat's reading in Israel or abroad (`?israel=1`),
 * any date's (`?date=`), each portion with its haftarah and what the analyses found in it. */
export function WeekPage() {
  const { m, locale } = useLocale()
  const t = m.wk
  const [params, update] = useQueryParams()
  const raw = params.get('date')
  const date = isIsoDate(raw) ? raw : localToday()
  const israel = params.get('israel') === '1'
  const res = useWeek(date, israel)
  const d = res.data
  return (
    <div className="page week-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <Segmented<WkPlace> label={t.place.label} value={israel ? 'israel' : 'abroad'} options={(['abroad', 'israel'] as const).map((v) => ({ value: v, label: t.place[v] }))} onChange={(v) => update({ israel: v === 'israel' ? '1' : null })} />
        <label className="wk-date">
          {t.dateLabel}{' '}
          <input type="date" value={date} onChange={(e) => update({ date: isIsoDate(e.target.value) ? e.target.value : null }, false)} />
        </label>
        {d && (
          <span className="wk-nav">
            <button type="button" onClick={() => update({ date: d.prev }, false)}>
              {locale === 'he' ? '→' : '←'} {t.prev}
            </button>
            <button type="button" onClick={() => update({ date: null }, false)} disabled={raw === null}>
              {t.today}
            </button>
            <button type="button" onClick={() => update({ date: d.next }, false)}>
              {t.next} {locale === 'he' ? '←' : '→'}
            </button>
          </span>
        )}
      </div>
      {res.isError ? <ErrorBox error={res.error} /> : !d ? <Loading /> : <Week d={d} />}
    </div>
  )
}

function Week({ d }: { d: WeekResponse }) {
  const { m, locale } = useLocale()
  const t = m.wk
  return (
    <>
      <h2 className="wk-shabbat">{t.shabbat(longDate(d.shabbat, locale), locale === 'he' ? d.hebrew_he : d.hebrew_en)}</h2>
      {d.festival && d.reading_shabbat && <p className="wk-festival">{t.festival(longDate(d.reading_shabbat, locale))}</p>}
      {d.parashot.length > 1 && <p className="muted">{t.together}</p>}
      {d.parashot.map((p) => (
        <Parasha key={p.unit.unit_id} p={p} />
      ))}
    </>
  )
}

function Parasha({ p }: { p: WeekParasha }) {
  const { m, locale } = useLocale()
  const t = m.wk
  const dossier = useDossier(p.unit.unit_id)
  const h = p.haftarah
  const id = `wk-${p.unit.unit_id.replace(/[^\w]/g, '')}`
  return (
    <section className="wk-parasha" aria-labelledby={id}>
      <h3 id={id}>
        <span className="he big" dir="rtl" lang="he">
          {p.unit.label_he}
        </span>
        {locale === 'en' && <span className="wk-en"> {p.unit.label_en}</span>}
      </h3>
      <p className="wk-links">
        <Link to={readLink(p.unit.unit_id)}>{t.read}</Link> · <Link to={unitLink(p.unit.unit_id)}>{t.unitPage}</Link>
      </p>
      <div className="wk-haftarah">
        <h4>{t.haftarah}</h4>
        {h ? (
          <>
            <p>
              {h.chapters.length > 0 ? <Link to={readLink(h.chapters[0])}>{t.haftarahOf(h.haft)}</Link> : t.haftarahOf(h.haft)}
              {h.seph && <span className="muted"> · {t.sephardi(h.seph)}</span>}
            </p>
            {h.theme ? <p className="muted small">{t.theme[h.theme] ?? h.theme}</p> : <p className="muted small">{t.rank(h.rank_fused)}</p>}
            <p className="small">
              <Link to={`/haftarot?p=${encodeURIComponent(p.unit.unit_id)}`}>{t.haftarotLink}</Link>
            </p>
          </>
        ) : (
          <p className="muted small">{t.noHaftarah}</p>
        )}
      </div>
      <h4>{t.foundTitle}</h4>
      <DossierBar unit={p.unit} dossier={dossier.data} error={dossier.error} />
    </section>
  )
}
