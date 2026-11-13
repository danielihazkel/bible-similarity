import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { changeNotebook, type NotebookChange, useNotebook, useNotebookChange } from '../api/hooks'
import type { NotebookCollection, NotebookEntry } from '../api/types'
import { useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { showToast } from '../lib/toast'
import '../i18n/pages/notebook'
import '../styles/components/NotebookPanel.css'

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
    </section>
  )
}

/** Keep a passage from a row of a list (a search result): one click, and from then on a link to
 * its page, where the note is written. Nothing while the notebook loads, on a server without one,
 * or on a read-only one that does not hold the passage. */
export function KeepButton({ unitId }: { unitId: string }) {
  const t = useT().nb
  const nb = useNotebook()
  const change = useNotebookChange()
  if (!nb.data) return null
  if (nb.data.entries.some((e) => e.unit.unit_id === unitId)) {
    return (
      <Link className="linkish" to={unitLink(unitId)}>
        <span aria-hidden="true">★</span> {t.kept}
      </Link>
    )
  }
  if (!nb.data.writable) return null
  return (
    <button type="button" className="linkish" title={t.keepTitle} disabled={change.isPending} onClick={() => change.mutate({ kind: 'keep', unit: unitId })}>
      <span aria-hidden="true">☆</span> {t.keep}
    </button>
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

/** Beside a form that names a collection: the name is taken. Every other failure of a save is
 * said by the toaster (`useNotebookChange`). */
export function ChangeError({ error }: { error: Error | null }) {
  const t = useT().nb
  if (!error?.message.startsWith('409')) return null
  return (
    <p role="alert" className="error small">
      {t.conflict}
    </p>
  )
}

/** How long after the last keystroke a note is saved (ms). */
export const AUTOSAVE_MS = 1200

/**
 * A note that saves itself (M177): a moment after the writing stops, when the box is left, on
 * Ctrl+Enter, and as the editor goes away with something unsaved. The line under it says where the
 * note stands (not saved yet, saving, saved, could not save with a way to try again), and the
 * browser asks before the page is left with a note unsaved or on its way.
 */
function NoteEditor({ unit, note }: { unit: string; note: string }) {
  const t = useT().nb
  const client = useQueryClient()
  const save = useNotebookChange()
  const [draft, setDraft] = useState(note)
  const [seen, setSeen] = useState(note)
  // the text of a save that failed: not sent again by itself, only when it changes or on "Try again"
  const [failed, setFailed] = useState<string>()
  if (seen !== note) {
    // the note changed on the server (this save, another tab, the notebook page): follow it,
    // unless there is writing here that it would wipe out
    setSeen(note)
    if (draft === seen) setDraft(note)
  }
  const dirty = draft !== note
  const send = (text: string) => {
    if (text === note || save.isPending) return
    setFailed(undefined)
    save.mutate({ kind: 'keep', unit, note: text }, { onError: () => setFailed(text) })
  }
  // a moment after the last change; again after a save, if the writing went on meanwhile
  useEffect(() => {
    if (!dirty || save.isPending || draft === failed) return
    const timer = window.setTimeout(() => send(draft), AUTOSAVE_MS)
    return () => window.clearTimeout(timer)
    // `send` reads what this effect depends on
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, dirty, save.isPending, failed])
  // leaving the page with a note unsaved or on its way: the browser asks first
  const open = dirty || save.isPending
  useEffect(() => {
    if (!open) return
    const ask = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', ask)
    return () => window.removeEventListener('beforeunload', ask)
  }, [open])
  // the editor goes (another page of the viewer) with something unsaved: saved on the way out
  const sending = save.isPending && save.variables?.kind === 'keep' ? save.variables.note : undefined
  const last = useRef({ draft, note, sending })
  useEffect(() => {
    last.current = { draft, note, sending }
  })
  useEffect(
    () => () => {
      const { draft, note, sending } = last.current
      if (draft !== note && draft !== sending) void changeNotebook(client, { kind: 'keep', unit, note: draft })
    },
    [client, unit],
  )
  const state = save.isPending ? t.saving : failed !== undefined && dirty ? t.notSaved : dirty ? t.unsaved : note ? t.saved : ''
  return (
    <div className="nb-note">
      <label>
        <span className="sr-only">{t.note}</span>
        <textarea
          dir="auto"
          rows={3}
          value={draft}
          placeholder={t.notePlaceholder}
          title={t.noteHint}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => send(draft)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send(draft)
          }}
        />
      </label>
      <span className="nb-note-state muted small" aria-live="polite">
        {state}
      </span>
      {failed !== undefined && dirty && !save.isPending && (
        <>
          {' '}
          <button type="button" className="linkish small" onClick={() => send(draft)}>
            {t.retry}
          </button>
        </>
      )}
    </div>
  )
}

/** An entry's note and collections; editable on a writable server. */
export function EntryEditor({ entry, collections, writable }: { entry: NotebookEntry; collections: NotebookCollection[]; writable: boolean }) {
  const m = useT()
  const t = m.nb
  const change = useNotebookChange()
  const client = useQueryClient()
  const unit = entry.unit.unit_id
  const mine = collections.filter((c) => entry.collections.includes(c.collection_id))
  const others = collections.filter((c) => !entry.collections.includes(c.collection_id))
  const [naming, setNaming] = useState(false)
  const [name, setName] = useState('')
  const run = (c: NotebookChange) => change.mutate(c)
  // taken out of a collection: it can be put back for a few seconds (the chip is gone by then)
  const takeOut = (c: NotebookCollection) =>
    void change
      .mutateAsync({ kind: 'remove', id: c.collection_id, unit })
      .then(() =>
        showToast(t.takenOut(c.name), {
          key: `nb:${c.collection_id}:${unit}`,
          action: { label: m.toast.undo, run: () => void changeNotebook(client, { kind: 'add', id: c.collection_id, unit }) },
        }),
      )
      .catch(() => {}) // said by the toaster
  return (
    <div className="nb-entry-editor">
      {writable ? (
        // a new editor for another passage: a note being written never moves to the next one
        <NoteEditor key={unit} unit={unit} note={entry.note} />
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
                <button type="button" className="nb-chip-x" aria-label={t.removeFrom(c.name)} title={t.removeFrom(c.name)} onClick={() => takeOut(c)}>
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
