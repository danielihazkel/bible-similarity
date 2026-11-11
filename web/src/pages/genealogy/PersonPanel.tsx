// The family tree's side panel: one person's family, each link with its verses.
import { useState } from 'react'
import { Link } from 'react-router'
import { useGenealogyPerson } from '../../api/hooks'
import type { FamilyLink, ProofVerse } from '../../api/types'
import { HebrewText } from '../../components/HebrewText'
import { ErrorBox, Loading } from '../../components/Status'
import { useLocale } from '../../context/localeContext'
import { type FamilyIndex } from '../../lib/familyTree'
import type { Highlight } from '../../lib/highlight'
import { unitLink } from '../../lib/links'
import { Name } from './Name'
import { MEMBERS_SHOWN } from './shared'
import type { Namer, T } from './shared'
import '../../styles/pages/genealogy-PersonPanel.css'

interface PanelProps {
  personId: number
  ix: FamilyIndex
  name: Namer
  t: T
  onPick: (id: number) => void
  onShow: (id: number) => void
  onOpenAll: (id: number, open: boolean) => void
  onPoster: (id: number) => void
  onClose: () => void
}

/** One person: where they stand, their family with the verses of each link, the readings where
 * the text disagrees. */
export function GenealogyPanel({ personId, ix, name, t, onPick, onShow, onOpenAll, onPoster, onClose }: PanelProps) {
  const { locale } = useLocale()
  const res = useGenealogyPerson(personId)
  const [allMembers, setAllMembers] = useState(false)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const p = d.person
  const host = ix.host.get(p.person_id)
  const tribe = d.attached && p.placement === 'tribe' ? name(d.attached.person.person_id) : undefined
  const below_ = ix.kids.get(p.person_id)?.length ?? 0
  const first = locale === 'he' ? d.first_label_he : d.first_label
  const who = (id: number) => (
    <button type="button" className="linkish" onClick={() => onPick(id)}>
      <Name n={name(id)} />
    </button>
  )
  const links = (ls: FamilyLink[], compact = false, roles = true) => (
    <ul className="gt-links">
      {ls.map((l) => (
        <LinkItem key={l.link_id} l={l} t={t} who={who} compact={compact} role={roles} />
      ))}
    </ul>
  )
  const members = allMembers ? d.members : d.members.slice(0, MEMBERS_SHOWN)
  return (
    <section className="gt-panel" aria-label={t.panel}>
      <div className="word-head">
        <h2>
          <Name n={name(p.person_id)} /> {p.kind !== 'person' && <span className={`type-tag gt-kind-${p.kind}`}>{t.kinds[p.kind as keyof T['kinds']]}</span>}
        </h2>
        <button type="button" className="linkish" onClick={onClose}>
          {t.close}
        </button>
      </div>
      {p.kind !== 'virtual' && (
        <p className="muted small">
          {first && p.first_vid !== null && (
            <>
              {t.firstNamed} <Link to={unitLink(`v:${p.first_vid}`)}>{first}</Link> ·{' '}
            </>
          )}
          {t.verseCount(p.n_verses)} · {p.reviewed ? t.reviewed : t.notReviewed}
        </p>
      )}
      {tribe && <p className="small">{t.placedTribe(tribe.text)}</p>}
      {p.placement === 'unattached' && <p className="small">{t.placedUnattached}</p>}
      {p.placement === 'spouse' && host !== undefined && <p className="small">{t.placedSpouse(name(host).text)}</p>}
      <p className="gt-actions">
        <button type="button" onClick={() => onShow(p.person_id)}>
          {t.showInTree}
        </button>
        {below_ > 0 && (
          <>
            <button type="button" onClick={() => onOpenAll(p.person_id, true)}>
              {t.openAll}
            </button>
            <button type="button" onClick={() => onOpenAll(p.person_id, false)}>
              {t.closeAll}
            </button>
            <button type="button" onClick={() => onPoster(p.person_id)} title={t.posterHint}>
              {t.poster}
            </button>
          </>
        )}
      </p>
      {d.conflicts.length > 0 && (
        <section className="gt-conflicts">
          <h3>
            <span className="gt-warn" aria-hidden="true">
              ⚠
            </span>{' '}
            {t.conflicts}
          </h3>
          {d.conflicts.map((c) => (
            <div key={c.conflict_id} className="gt-conflict">
              <p className="small">
                <strong>{t.conflictKinds[c.kind]}</strong>
                {(locale === 'he' ? c.note_he : c.note_en) && ` · ${locale === 'he' ? c.note_he : c.note_en}`}
              </p>
              <ul className="gt-links">
                {c.readings.map((l, i) => (
                  <LinkItem key={l.link_id} l={l} t={t} who={who} reading={i === 0 ? t.readingDrawn : t.readingOther} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
      {d.identities.length > 0 && (
        <section className="gt-identities">
          <h3>{t.identities}</h3>
          {d.identities.map((x) => {
            const note = locale === 'he' ? x.note_he : x.note_en
            return (
              <div key={x.identity_id} className="gt-identity">
                <p className="small">
                  {x.person ? (
                    <>
                      {x.status === 'rabbinic' ? t.rabbinicSame : t.maybeSame} {who(x.person.person_id)}
                    </>
                  ) : (
                    t.mergedFrom(x.n_keys)
                  )}
                  {note && ` · ${note}`}
                </p>
                {x.sources.length > 0 && (
                  <p className="small gt-sources">
                    {t.rabbinicSource}:{' '}
                    {x.sources.map((s, i) => (
                      <span key={s.cite}>
                        {i > 0 && ' · '}
                        <a href={s.url} target="_blank" rel="noreferrer">
                          <span lang="he" dir="rtl">
                            {s.cite_he}
                          </span>
                          <span className="sr-only"> {t.rabbinicLink}</span>
                        </a>
                        {locale === 'en' && (
                          <span className="muted" dir="ltr">
                            {' '}
                            ({s.cite})
                          </span>
                        )}
                      </span>
                    ))}
                  </p>
                )}
                <ol className="gt-proofs">
                  {x.proofs.map((v) => (
                    <Proof key={v.verse.verse_id} v={v} t={t} />
                  ))}
                </ol>
              </div>
            )
          })}
        </section>
      )}
      {d.parents.length > 0 && (
        <>
          <h3>{t.parents}</h3>
          {links(d.parents)}
        </>
      )}
      {d.spouses.length > 0 && (
        <>
          <h3>{t.spouses}</h3>
          {links(d.spouses, false, false)}
        </>
      )}
      {d.children.length > 0 && (
        <>
          <h3>{t.children}</h3>
          {d.children.map((g) => (
            <div key={g.adopted ? 'adopted' : (g.other?.person_id ?? 0)} className="gt-child-group">
              <h4 className="small">
                {g.adopted ? (
                  t.childrenAdopted
                ) : g.other ? (
                  <>
                    {g.other.sex === 'f' ? t.childrenBy : t.childrenOf} {who(g.other.person_id)}
                  </>
                ) : (
                  t.childrenUnnamed
                )}
              </h4>
              {links(g.children, true, false)}
            </div>
          ))}
        </>
      )}
      {d.siblings.length > 0 && (
        <>
          <h3>{t.siblings}</h3>
          <p className="gt-names">
            {d.siblings.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
        </>
      )}
      {d.members.length > 0 && (
        <>
          <h3>{t.members(d.members.length)}</h3>
          <p className="muted small">{t.membersLede}</p>
          <p className="gt-names">
            {members.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
          {d.members.length > MEMBERS_SHOWN && (
            <button type="button" className="linkish" onClick={() => setAllMembers((x) => !x)}>
              {allMembers ? t.showFewer : t.showAll(d.members.length)}
            </button>
          )}
        </>
      )}
    </section>
  )
}

interface LinkProps {
  l: FamilyLink
  t: T
  who: (id: number) => React.ReactNode
  compact?: boolean // the verses folded (a child's)
  role?: boolean // say father / mother
  reading?: string // a conflict's reading: which
}

function LinkItem({ l, t, who, compact = false, role = true, reading }: LinkProps) {
  const tags = [
    role && !reading ? t.roles[l.role] : undefined,
    reading,
    l.kind === 'descendant' ? t.descendant : undefined,
    l.kind === 'adopted' ? t.adopted : undefined,
    t.status[l.status],
    l.marker && t.markers[l.marker] ? t.markers[l.marker] : undefined,
    l.doubt ? t.doubt : undefined,
    (l.role === 'father' || l.role === 'mother') && !reading ? (l.drawn ? t.drawn : t.notDrawn) : undefined,
  ].filter(Boolean)
  const proved = l.proofs.filter((v) => v.cue !== 'nearby')
  const hint = l.proofs.filter((v) => v.cue === 'nearby')
  const verses = (
    <>
      {!proved.length && l.role !== 'unstated' && <p className="muted small">{t.noProof}</p>}
      {hint.length > 0 && <p className="muted small">{t.nearbyHint}</p>}
      <ol className="gt-proofs">
        {l.proofs.map((v) => (
          <Proof key={v.verse.verse_id} v={v} t={t} />
        ))}
      </ol>
    </>
  )
  return (
    <li className={`gt-link${l.kind === 'descendant' ? ' desc' : ''}${l.status === 'tipnr' ? ' unreviewed' : ''}`}>
      <span className="gt-link-head">
        {who(l.person.person_id)}{' '}
        {tags.map((x) => (
          <span key={x} className="gt-tag small">
            {x}
          </span>
        ))}
      </span>
      {compact ? (
        <details>
          <summary className="small">{l.proofs.length ? t.verses(proved.length || l.proofs.length) : t.noProof}</summary>
          {verses}
        </details>
      ) : (
        verses
      )}
    </li>
  )
}

function Proof({ v, t }: { v: ProofVerse; t: T }) {
  const { locale } = useLocale()
  const hl: Highlight = new Map(v.tokens.map((i) => [i, 'focus']))
  return (
    <li className="hit gt-proof">
      <Link className="verse-ref" to={unitLink(`v:${v.verse.verse_id}`)}>
        {locale === 'he' ? v.verse.ref_he : v.verse.ref}
      </Link>{' '}
      {v.cue && (
        <span className="type-tag gt-cue" title={t.cueTitle}>
          {t.cues[v.cue]}
        </span>
      )}{' '}
      {v.source === 'curated' && <span className="muted small">{t.curated}</span>}
      <p className="hit-text">
        <HebrewText verse={v.verse} highlight={hl} />
      </p>
    </li>
  )
}
