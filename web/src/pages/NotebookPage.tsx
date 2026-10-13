import { useState } from 'react'
import { Link } from 'react-router'
import { useNotebook, useNotebookChange } from '../api/hooks'
import type { NotebookCollection, NotebookEntry } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { ChangeError, DropButton, EntryEditor } from '../components/NotebookPanel'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { downloadCsv, downloadText } from '../lib/csv'
import { unitLink } from '../lib/links'
import { filterEntries, notebookMarkdown } from '../lib/notebook'
import { useQueryParams } from '../lib/urlState'

const today = () => new Date().toISOString().slice(0, 10)

/** Your notebook (DESIGN.md §16.47): kept units with notes, collections, export. */
export function NotebookPage() {
  const { m, locale } = useLocale()
  const t = m.nb
  const [params, update] = useQueryParams()
  const nb = useNotebook()
  const [filter, setFilter] = useState('')
  if (nb.isPending) return <Loading />
  if (nb.error) return <ErrorBox error={nb.error} />
  const { entries, collections, writable, hidden } = nb.data
  const raw = params.get('c')
  const current = collections.find((c) => String(c.collection_id) === raw)
  const inCollection = current ? entries.filter((e) => e.collections.includes(current.collection_id)) : entries
  const shown = filterEntries(inCollection, filter)
  const name = new Map(collections.map((c) => [c.collection_id, c.name]))
  // the file name and the Markdown carry the day of the download
  const file = (stamp: string) => `notebook${current ? `-${current.collection_id}` : ''}-${stamp}`
  return (
    <div className="page notebook-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {!writable && <p className="status">{t.readOnly}</p>}
      {hidden > 0 && <p className="muted small">{t.hidden(hidden)}</p>}
      <Collections collections={collections} total={entries.length} current={current} writable={writable} onPick={(id) => update({ c: id === undefined ? null : String(id) })} />
      {entries.length === 0 ? (
        <p className="status">{t.none}</p>
      ) : (
        <section aria-label={current ? current.name : t.all(entries.length)}>
          <div className="toolbar">
            <label className="control">
              <span>{t.filter}</span>
              <input type="search" dir="auto" value={filter} placeholder={t.filterPlaceholder} onChange={(e) => setFilter(e.target.value)} />
            </label>
            <span className="muted small">{t.count(shown.length, inCollection.length)}</span>
            <button
              type="button"
              className="linkish export-md"
              onClick={() => {
                const stamp = today()
                downloadText(`${file(stamp)}.md`, [notebookMarkdown(shown, collections, current?.name ?? null, t.md, locale, stamp)], 'text/markdown;charset=utf-8')
              }}
            >
              {t.exportMd}
            </button>
            <button
              type="button"
              className="linkish export-csv"
              onClick={() =>
                downloadCsv(
                  `${file(today())}.csv`,
                  shown.map((e) => ({
                    [t.csvCols.unit]: e.unit.label_en,
                    [t.csvCols.unit_he]: e.unit.label_he,
                    [t.csvCols.type]: e.unit.unit_type,
                    [t.csvCols.note]: e.note,
                    [t.csvCols.collections]: e.collections.map((c) => name.get(c) ?? '').join('; '),
                    [t.csvCols.updated]: e.updated_at,
                  })),
                )
              }
            >
              {t.exportCsv}
            </button>
          </div>
          {shown.length === 0 ? (
            <p className="status">{t.noMatch}</p>
          ) : (
            <ol className="hits notebook-entries">
              {shown.map((e) => (
                <Entry key={e.unit.unit_id} e={e} collections={collections} writable={writable} />
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  )
}

function Entry({ e, collections, writable }: { e: NotebookEntry; collections: NotebookCollection[]; writable: boolean }) {
  const { m } = useLocale()
  const t = m.nb
  const change = useNotebookChange()
  return (
    <li className="hit notebook-entry">
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(e.unit.unit_id)}>
          <UnitName en={e.unit.label_en} he={e.unit.label_he} />
        </Link>{' '}
        <span className="type-tag">{m.units.type(e.unit.unit_type)}</span>{' '}
        {writable && <DropButton onDrop={() => change.mutate({ kind: 'drop', unit: e.unit.unit_id })} />}
      </div>
      {e.verse && (
        <p className="hit-text">
          <HebrewText verse={e.verse} />
        </p>
      )}
      {!writable && !e.note && <p className="muted small">{t.emptyNote}</p>}
      <EntryEditor entry={e} collections={collections} writable={writable} />
      <ChangeError error={change.error} />
    </li>
  )
}

function Collections({
  collections,
  total,
  current,
  writable,
  onPick,
}: {
  collections: NotebookCollection[]
  total: number
  current: NotebookCollection | undefined
  writable: boolean
  onPick: (id: number | undefined) => void
}) {
  const t = useLocale().m.nb
  const change = useNotebookChange()
  const [name, setName] = useState('')
  return (
    <section aria-label={t.collections} className="nb-collections-bar">
      <h2>{t.collections}</h2>
      <div className="chips">
        <button type="button" className={`chip${current ? '' : ' on'}`} aria-pressed={!current} onClick={() => onPick(undefined)}>
          {t.all(total)}
        </button>
        {collections.map((c) => (
          <button
            key={c.collection_id}
            type="button"
            className={`chip${current?.collection_id === c.collection_id ? ' on' : ''}`}
            aria-pressed={current?.collection_id === c.collection_id}
            onClick={() => onPick(c.collection_id)}
          >
            {t.collectionChip(c.name, c.n_entries)}
          </button>
        ))}
      </div>
      {collections.length === 0 && <p className="muted small">{t.noCollections}</p>}
      {current && <CollectionEditor key={current.collection_id} c={current} writable={writable} onDeleted={() => onPick(undefined)} />}
      {writable && (
        <form
          className="nb-new"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) change.mutate({ kind: 'create', name: name.trim() }, { onSuccess: () => setName('') })
          }}
        >
          <label className="control">
            <span>{t.newCollection}</span>
            <input value={name} maxLength={80} placeholder={t.newName} onChange={(e) => setName(e.target.value)} />
          </label>{' '}
          <button type="submit" disabled={!name.trim()}>
            {t.create}
          </button>
        </form>
      )}
      <ChangeError error={change.error} />
    </section>
  )
}

function CollectionEditor({ c, writable, onDeleted }: { c: NotebookCollection; writable: boolean; onDeleted: () => void }) {
  const t = useLocale().m.nb
  const change = useNotebookChange()
  const [editing, setEditing] = useState(false)
  const [asking, setAsking] = useState(false)
  const [name, setName] = useState(c.name)
  const [description, setDescription] = useState(c.description)
  if (editing) {
    return (
      <form
        className="nb-collection-edit"
        onSubmit={(e) => {
          e.preventDefault()
          change.mutate({ kind: 'rename', id: c.collection_id, name: name.trim(), description }, { onSuccess: () => setEditing(false) })
        }}
      >
        <label className="control">
          <span>{t.rename}</span>
          <input value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="control">
          <span>{t.description}</span>
          <textarea dir="auto" rows={2} value={description} placeholder={t.descriptionPlaceholder} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <button type="submit" disabled={!name.trim()}>
          {t.saveCollection}
        </button>{' '}
        <button type="button" className="linkish" onClick={() => setEditing(false)}>
          {t.cancel}
        </button>
        <ChangeError error={change.error} />
      </form>
    )
  }
  return (
    <div className="nb-collection">
      {c.description && (
        <p className="small" dir="auto">
          {c.description}
        </p>
      )}
      {writable && (
        <p className="small">
          <button type="button" className="linkish" onClick={() => setEditing(true)}>
            {t.edit}
          </button>
          {' · '}
          {asking ? (
            <span role="group" aria-label={t.confirmDelete(c.name)}>
              {t.confirmDelete(c.name)}{' '}
              <button type="button" className="danger" onClick={() => change.mutate({ kind: 'delete', id: c.collection_id }, { onSuccess: onDeleted })}>
                {t.confirmYes}
              </button>{' '}
              <button type="button" onClick={() => setAsking(false)}>
                {t.cancel}
              </button>
            </span>
          ) : (
            <button type="button" className="linkish" onClick={() => setAsking(true)}>
              {t.deleteCollection}
            </button>
          )}
        </p>
      )}
      <ChangeError error={change.error} />
    </div>
  )
}
