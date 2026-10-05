import { lazy } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { BooksPage } from './pages/BooksPage'

// pages load on first visit (the landing page ships with the app)
const AboutPage = lazy(() => import('./pages/AboutPage').then((m) => ({ default: m.AboutPage })))
const BookPage = lazy(() => import('./pages/BookPage').then((m) => ({ default: m.BookPage })))
const ChangesPage = lazy(() => import('./pages/ChangesPage').then((m) => ({ default: m.ChangesPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((m) => ({ default: m.ComparePage })))
const ConcordancePage = lazy(() => import('./pages/ConcordancePage').then((m) => ({ default: m.ConcordancePage })))
const DiscoveriesPage = lazy(() => import('./pages/DiscoveriesPage').then((m) => ({ default: m.DiscoveriesPage })))
const MapPage = lazy(() => import('./pages/MapPage').then((m) => ({ default: m.MapPage })))
const NamesPage = lazy(() => import('./pages/NamesPage').then((m) => ({ default: m.NamesPage })))
const PhrasesPage = lazy(() => import('./pages/PhrasesPage').then((m) => ({ default: m.PhrasesPage })))
const PoetryPage = lazy(() => import('./pages/PoetryPage').then((m) => ({ default: m.PoetryPage })))
const SequencePage = lazy(() => import('./pages/SequencePage').then((m) => ({ default: m.SequencePage })))
const SequencesPage = lazy(() => import('./pages/SequencesPage').then((m) => ({ default: m.SequencesPage })))
const StructurePage = lazy(() => import('./pages/StructurePage').then((m) => ({ default: m.StructurePage })))
const StylometryPage = lazy(() => import('./pages/StylometryPage').then((m) => ({ default: m.StylometryPage })))
const SearchPage = lazy(() => import('./pages/SearchPage').then((m) => ({ default: m.SearchPage })))
const UnitPage = lazy(() => import('./pages/UnitPage').then((m) => ({ default: m.UnitPage })))
const WordplayPage = lazy(() => import('./pages/WordplayPage').then((m) => ({ default: m.WordplayPage })))

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<BooksPage />} />
          <Route path="browse/:bookId" element={<BookPage />} />
          <Route path="unit/:unitId" element={<UnitPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="discoveries" element={<DiscoveriesPage />} />
          <Route path="lemma/:lemma" element={<ConcordancePage />} />
          <Route path="phrases" element={<PhrasesPage />} />
          <Route path="sequences" element={<SequencesPage />} />
          <Route path="sequences/:seqId" element={<SequencePage />} />
          <Route path="changes" element={<ChangesPage />} />
          <Route path="poetry" element={<PoetryPage />} />
          <Route path="wordplay" element={<WordplayPage />} />
          <Route path="names" element={<NamesPage />} />
          <Route path="structure" element={<StructurePage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="style" element={<StylometryPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route
            path="*"
            element={
              <p className="status">
                Page not found. <Link to="/">Back to the books</Link>.
              </p>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
