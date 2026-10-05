/** A lazy page chunk that no longer exists (the viewer was rebuilt while this tab was open). */
export function isChunkLoadError(error: unknown): boolean {
  const msg = error instanceof Error ? `${error.name} ${error.message}` : String(error)
  return /dynamically imported module|Importing a module script failed|ChunkLoadError|Unable to preload CSS/i.test(msg)
}
