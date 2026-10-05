import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { AboutPage } from './pages/AboutPage'
import { BookPage } from './pages/BookPage'
import { BooksPage } from './pages/BooksPage'
import { ComparePage } from './pages/ComparePage'
import { ConcordancePage } from './pages/ConcordancePage'
import { DiscoveriesPage } from './pages/DiscoveriesPage'
import { MapPage } from './pages/MapPage'
import { PhrasesPage } from './pages/PhrasesPage'
import { SequencePage } from './pages/SequencePage'
import { SequencesPage } from './pages/SequencesPage'
import { StructurePage } from './pages/StructurePage'
import { StylometryPage } from './pages/StylometryPage'
import { SearchPage } from './pages/SearchPage'
import { UnitPage } from './pages/UnitPage'

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
