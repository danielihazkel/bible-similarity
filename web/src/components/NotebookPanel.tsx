import { useState } from 'react'
import { Link } from 'react-router'
import { type NotebookChange, useNotebook, useNotebookChange } from '../api/hooks'
import type { NotebookCollection, NotebookEntry } from '../api/types'
import { useT } from '../context/localeContext'

const NEW = '__new__'

/**
 * The notebook on a unit page (DESIGN.md §16.47): keep the unit, write a note, put it in a
 * collection. Hidden while the notebook loads, and when the server keeps it read-only and the
 * unit is not in it.
 */
export function NotebookPanel({ unitId }: { unitId: string }) {
  const t = useT().nb
  const nb = useNotebook()
  const change = useNotebookChange()
  if (!nb.data) return null
  const entry = nb.data.entries.find((e) => e.unit.unit_id === unitId)
  const { writable } = nb.data
  if (!writable && !entry) return null
  return (
    <section className="notebook-panel" aria-label={t.panel}>
      {!entry ? (
        <button type="button" className="nb-keep" title={t.keepTitle} disabled={change.isPending} onClick={() => change.mutate({ kind: 'keep', unit: unitId })}>
          <span aria-hidden="true">☆</span> {t.keep}
        </button>
      ) : (
        <>
          <div className="nb-head">
            <span className="nb-kept">
              <span aria-hidden="true">★</span> {t.kept}
            </span>
            {writable && <DropButton onDrop={() => change.mutate({ kind: 'drop', unit: unitId })} />}
            <Link className="small" to="/notebook">
              {t.open}
            </Link>
          </div>
          <EntryEditor entry={entry} collections={nb.data.collections} writable={writable} />
        </>
      )}
      <ChangeError error={change.error} />
    </section>
  )
}

/** Remove, after a second click that says what goes. */
export function DropButton({ onDrop }: { onDrop: () => void }) {
  const t = useT().nb
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return (
      <button type="button" className="linkish small" title={t.dropTitle} onClick={() => setAsking(true)}>
        {t.drop}
      </button>
    )
  }
  return (
    <span className="nb-confirm small" role="group" aria-label={t.confirmDrop}>
      {t.confirmDrop}{' '}
      <button type="button" className="danger" onClick={onDrop}>
        {t.yes}
      </button>{' '}
      <button type="button" onClick={() => setAsking(false)}>
        {t.no}
      </button>
    </span>
  )
}

export function ChangeError({ error }: { error: Error | null }) {
  const t = useT().nb
  if (!error) return null
  return (
    <p role="alert" className="error small">
      {error.message.startsWith('409') ? t.conflict : t.saveFailed(error.message)}
    </p>
  )
}

/** An entry's note and collections; editable on a writable server. */
export function EntryEditor({ entry, collections, writable }: { entry: NotebookEntry; collections: NotebookCollection[]; writable: boolean }) {
  const t = useT().nb
  const change = useNotebookChange()
  const [draft, setDraft] = useState(entry.note)
  const [saved, setSaved] = useState(entry.note)
  if (saved !== entry.note) {
    // the note changed elsewhere (another tab, the notebook page): follow it
    setSaved(entry.note)
    setDraft(entry.note)
  }
  const unit = entry.unit.unit_id
  const mine = collections.filter((c) => entry.collections.includes(c.collection_id))
  const others = collections.filter((c) => !entry.collections.includes(c.collection_id))
  const [naming, setNaming] = useState(false)
  const [name, setName] = useState('')
  const run = (c: NotebookChange) => change.mutate(c)
  return (
    <div className="nb-entry-editor">
      {writable ? (
        <form
          className="nb-note"
          onSubmit={(e) => {
            e.preventDefault()
            run({ kind: 'keep', unit, note: draft })
          }}
        >
          <label>
            <span className="sr-only">{t.note}</span>
            <textarea dir="auto" rows={3} value={draft} placeholder={t.notePlaceholder} onChange={(e) => setDraft(e.target.value)} />
          </label>
          <button type="submit" disabled={draft === entry.note || change.isPending}>
            {t.save}
          </button>{' '}
          <span className="muted small" aria-live="polite">
            {draft === entry.note ? (entry.note ? t.saved : '') : t.unsaved}
          </span>
        </form>
      ) : (
        entry.note && (
          <p className="nb-note-text" dir="auto">
            {entry.note}
          </p>
        )
      )}
      {(mine.length > 0 || writable) && (
        <div className="nb-collections" role="group" aria-label={t.inCollections}>
          <span className="muted small">{t.inCollections}:</span>{' '}
          {mine.map((c) => (
            <span key={c.collection_id} className="chip nb-chip">
              {c.name}
              {writable && (
                <button type="button" className="nb-chip-x" aria-label={t.removeFrom(c.name)} title={t.removeFrom(c.name)} onClick={() => run({ kind: 'remove', id: c.collection_id, unit })}>
                  ×
                </button>
              )}
            </span>
          ))}
          {writable && !naming && (
            <select
              aria-label={t.addTo}
              value=""
              onChange={(e) => {
                if (e.target.value === NEW) setNaming(true)
                else if (e.target.value) run({ kind: 'add', id: Number(e.target.value), unit })
              }}
            >
              <option value="">{t.addTo}</option>
              {others.map((c) => (
                <option key={c.collection_id} value={c.collection_id}>
                  {c.name}
                </option>
              ))}
              <option value={NEW}>{t.newCollection}</option>
            </select>
          )}
          {writable && naming && (
            <form
              className="nb-new"
              onSubmit={(e) => {
                e.preventDefault()
                if (!name.trim()) return
                change.mutate({ kind: 'create', name: name.trim(), unit }, { onSuccess: () => { setNaming(false); setName('') } })
              }}
            >
              <input aria-label={t.newName} placeholder={t.newName} value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoFocus />{' '}
              <button type="submit" disabled={!name.trim()}>
                {t.createAndAdd}
              </button>{' '}
              <button type="button" className="linkish" onClick={() => setNaming(false)}>
                {t.cancel}
              </button>
            </form>
          )}
        </div>
      )}
      <ChangeError error={change.error} />
    </div>
  )
}
