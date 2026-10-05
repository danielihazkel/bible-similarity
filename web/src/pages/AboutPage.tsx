import { Link } from 'react-router'
import { useMeta } from '../api/hooks'
import { ErrorBox, Loading } from '../components/Status'

const show = (v: unknown) => (typeof v === 'string' ? v : JSON.stringify(v))

export function AboutPage() {
  const meta = useMeta()
  return (
    <div className="page about-page">
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
      {meta.isPending ? (
        <Loading />
      ) : meta.error ? (
        <ErrorBox error={meta.error} />
      ) : (
        <table className="meta-table">
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
