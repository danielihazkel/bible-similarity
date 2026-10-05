import { Link } from 'react-router'
import { useMeta } from '../api/hooks'
import { ErrorBox, Loading } from '../components/Status'
import { useT } from '../context/localeContext'

const show = (v: unknown) => (typeof v === 'string' ? v : JSON.stringify(v))

// Prose is written per language (a component each) rather than pieced together from catalog strings.
function AboutEn() {
  return (
    <>
      <h1>About</h1>
      <p>
        For every verse, chapter, parasha and Masoretic pericope of the Hebrew Bible, this viewer lists the most
        similar units of the same type under three modes:
      </p>
      <ul>
        <li>
          <b>Lexical</b>: shared wording (BM25 / TF-IDF over OSHB lemmas, with repeated formulas down-weighted).
        </li>
        <li>
          <b>Semantic</b>: shared meaning (BEREL 3.0 fine-tuned on Sefaria cross-references, CSLS-scored).
        </li>
        <li>
          <b>Fused</b>: both, combined by weighted reciprocal rank fusion.
        </li>
      </ul>
      <p>
        Hebrew versification and Jewish canon order throughout. Try <Link to="/unit/v:15291">Psalms 14:1</Link> or{' '}
        <Link to="/compare?a=c:8:22&b=c:26:18">II Samuel 22 ↔ Psalms 18</Link>. How well each system finds known
        cross-references: <Link to="/eval">Evaluation</Link>.
      </p>
      <h2>Sources and licenses</h2>
      <ul>
        <li>
          Display text: Sefaria, <i>Miqra according to the Masorah</i>, CC-BY-SA.
        </li>
        <li>Lemmas and morphology: Open Scriptures Hebrew Bible (WLC public domain; morphology CC BY 4.0).</li>
        <li>Parasha boundaries and cross-references: Sefaria-Export.</li>
        <li>Models: BEREL 3.0 (Apache-2.0). Fonts: Noto Serif Hebrew / Ezra SIL (OFL).</li>
      </ul>
      <h2>Build</h2>
    </>
  )
}

function AboutHe() {
  return (
    <>
      <h1>אודות</h1>
      <p>
        לכל פסוק, פרק, פרשה ופיסקה (פתוחה או סתומה) בתנ״ך מציג הממשק את היחידות הדומות לה ביותר מאותו סוג, בשלושה
        אופנים:
      </p>
      <ul>
        <li>
          <b>מילולי</b>: ניסוח משותף (BM25 / TF-IDF על ערכי OSHB, ונוסחאות חוזרות במשקל מופחת).
        </li>
        <li>
          <b>סמנטי</b>: משמעות משותפת (BEREL 3.0 שכוונן על ההפניות של ספריא, בציון CSLS).
        </li>
        <li>
          <b>משולב</b>: שניהם יחד, במיזוג דירוגים הדדי משוקלל.
        </li>
      </ul>
      <p>
        חלוקת הפסוקים העברית וסדר הספרים של התנ״ך לאורך כל הדרך. נסו את <Link to="/unit/v:15291">תהלים יד:א</Link> או
        את <Link to="/compare?a=c:8:22&b=c:26:18">שמואל ב כב ↔ תהלים יח</Link>. עד כמה כל שיטה מוצאת הפניות ידועות:{' '}
        <Link to="/eval">הערכה</Link>.
      </p>
      <h2>מקורות ורישיונות</h2>
      <ul>
        <li>
          טקסט התצוגה: ספריא, <i>מקרא על פי המסורה</i>, CC-BY-SA.
        </li>
        <li>ערכים ומורפולוגיה: Open Scriptures Hebrew Bible ‏(WLC בנחלת הכלל; מורפולוגיה CC BY 4.0).</li>
        <li>גבולות הפרשות וההפניות: Sefaria-Export.</li>
        <li>מודלים: BEREL 3.0 ‏(Apache-2.0). גופנים: Noto Serif Hebrew / Ezra SIL ‏(OFL).</li>
      </ul>
      <h2>בנייה</h2>
    </>
  )
}

export function AboutPage() {
  const m = useT()
  const meta = useMeta()
  return (
    <div className="page about-page">
      {m.locale === 'he' ? <AboutHe /> : <AboutEn />}
      {meta.isPending ? (
        <Loading />
      ) : meta.error ? (
        <ErrorBox error={meta.error} />
      ) : (
        // build keys and values are technical: left to right in either language
        <table className="meta-table" dir="ltr">
          <tbody>
            {Object.entries({ ...meta.data.build, ...meta.data.runtime }).map(([key, v]) => (
              <tr key={key}>
                <th scope="row">{key}</th>
                <td>
                  <code>{show(v)}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
