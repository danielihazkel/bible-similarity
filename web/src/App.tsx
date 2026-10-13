import { lazy } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { useT } from './context/localeContext'
import { BooksPage } from './pages/BooksPage'

// pages load on first visit (the landing page ships with the app)
const FindingsPage = lazy(() => import('./pages/FindingsPage').then((m) => ({ default: m.FindingsPage })))
const CitationsPage = lazy(() => import('./pages/CitationsPage').then((m) => ({ default: m.CitationsPage })))
const KetivPage = lazy(() => import('./pages/KetivPage').then((m) => ({ default: m.KetivPage })))
const RootsPage = lazy(() => import('./pages/RootsPage').then((m) => ({ default: m.RootsPage })))
const RootPage = lazy(() => import('./pages/RootPage').then((m) => ({ default: m.RootPage })))
const ReaderPage = lazy(() => import('./pages/ReaderPage').then((m) => ({ default: m.ReaderPage })))
const RefrainsPage = lazy(() => import('./pages/RefrainsPage').then((m) => ({ default: m.RefrainsPage })))
const NotebookPage = lazy(() => import('./pages/NotebookPage').then((m) => ({ default: m.NotebookPage })))
const QueryPage = lazy(() => import('./pages/QueryPage').then((m) => ({ default: m.QueryPage })))
const FormsPage = lazy(() => import('./pages/FormsPage').then((m) => ({ default: m.FormsPage })))
const PsalmsPage = lazy(() => import('./pages/PsalmsPage').then((m) => ({ default: m.PsalmsPage })))
const PentateuchPage = lazy(() => import('./pages/PentateuchPage').then((m) => ({ default: m.PentateuchPage })))
const DivisionsPage = lazy(() => import('./pages/DivisionsPage').then((m) => ({ default: m.DivisionsPage })))
const AcrosticsPage = lazy(() => import('./pages/AcrosticsPage').then((m) => ({ default: m.AcrosticsPage })))
const AboutPage = lazy(() => import('./pages/AboutPage').then((m) => ({ default: m.AboutPage })))
const BookPage = lazy(() => import('./pages/BookPage').then((m) => ({ default: m.BookPage })))
const ChangesPage = lazy(() => import('./pages/ChangesPage').then((m) => ({ default: m.ChangesPage })))
const ComparePage = lazy(() => import('./pages/ComparePage').then((m) => ({ default: m.ComparePage })))
const ConcordancePage = lazy(() => import('./pages/ConcordancePage').then((m) => ({ default: m.ConcordancePage })))
const LanguagePage = lazy(() => import('./pages/LanguagePage').then((m) => ({ default: m.LanguagePage })))
const ShiftsPage = lazy(() => import('./pages/ShiftsPage').then((m) => ({ default: m.ShiftsPage })))
const DomainsPage = lazy(() => import('./pages/DomainsPage').then((m) => ({ default: m.DomainsPage })))
const DiscoveriesPage = lazy(() => import('./pages/DiscoveriesPage').then((m) => ({ default: m.DiscoveriesPage })))
const BorrowingPage = lazy(() => import('./pages/BorrowingPage').then((m) => ({ default: m.BorrowingPage })))
const SpeechPage = lazy(() => import('./pages/SpeechPage').then((m) => ({ default: m.SpeechPage })))
const LabelsPage = lazy(() => import('./pages/LabelsPage').then((m) => ({ default: m.LabelsPage })))
const EvalPage = lazy(() => import('./pages/EvalPage').then((m) => ({ default: m.EvalPage })))
const NetworkPage = lazy(() => import('./pages/NetworkPage').then((m) => ({ default: m.NetworkPage })))
const MapPage = lazy(() => import('./pages/MapPage').then((m) => ({ default: m.MapPage })))
const NamesPage = lazy(() => import('./pages/NamesPage').then((m) => ({ default: m.NamesPage })))
const PhrasesPage = lazy(() => import('./pages/PhrasesPage').then((m) => ({ default: m.PhrasesPage })))
const PoetryPage = lazy(() => import('./pages/PoetryPage').then((m) => ({ default: m.PoetryPage })))
const SequencePage = lazy(() => import('./pages/SequencePage').then((m) => ({ default: m.SequencePage })))
const SequencesPage = lazy(() => import('./pages/SequencesPage').then((m) => ({ default: m.SequencesPage })))
const StructurePage = lazy(() => import('./pages/StructurePage').then((m) => ({ default: m.StructurePage })))
const StylometryPage = lazy(() => import('./pages/StylometryPage').then((m) => ({ default: m.StylometryPage })))
const SearchPage = lazy(() => import('./pages/SearchPage').then((m) => ({ default: m.SearchPage })))
const TypeScenesPage = lazy(() => import('./pages/TypeScenesPage').then((m) => ({ default: m.TypeScenesPage })))
const UnitPage = lazy(() => import('./pages/UnitPage').then((m) => ({ default: m.UnitPage })))
const WordplayPage = lazy(() => import('./pages/WordplayPage').then((m) => ({ default: m.WordplayPage })))

function NotFound() {
  const m = useT()
  return (
    <p className="status">
      {m.site.notFound} <Link to="/">{m.site.backToBooks}</Link>.
    </p>
  )
}

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
          <Route path="labels" element={<LabelsPage />} />
          <Route path="lemma/:lemma" element={<ConcordancePage />} />
          <Route path="phrases" element={<PhrasesPage />} />
          <Route path="sequences" element={<SequencesPage />} />
          <Route path="sequences/:seqId" element={<SequencePage />} />
          <Route path="changes" element={<ChangesPage />} />
          <Route path="borrowing" element={<BorrowingPage />} />
          <Route path="typescenes" element={<TypeScenesPage />} />
          <Route path="poetry" element={<PoetryPage />} />
          <Route path="wordplay" element={<WordplayPage />} />
          <Route path="names" element={<NamesPage />} />
          <Route path="domains" element={<DomainsPage />} />
          <Route path="domains/:code" element={<DomainsPage />} />
          <Route path="structure" element={<StructurePage />} />
          <Route path="acrostics" element={<AcrosticsPage />} />
          <Route path="divisions" element={<DivisionsPage />} />
          <Route path="ketiv" element={<KetivPage />} />
          <Route path="roots" element={<RootsPage />} />
          <Route path="root/:root" element={<RootPage />} />
          <Route path="read/:unitId" element={<ReaderPage />} />
          <Route path="refrains" element={<RefrainsPage />} />
          <Route path="forms" element={<FormsPage />} />
          <Route path="query" element={<QueryPage />} />
          <Route path="notebook" element={<NotebookPage />} />
          <Route path="psalms" element={<PsalmsPage />} />
          <Route path="pentateuch" element={<PentateuchPage />} />
          <Route path="citations" element={<CitationsPage />} />
          <Route path="findings" element={<FindingsPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="network" element={<NetworkPage />} />
          <Route path="style" element={<StylometryPage />} />
          <Route path="shifts" element={<ShiftsPage />} />
          <Route path="language" element={<LanguagePage />} />
          <Route path="speech" element={<SpeechPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="eval" element={<EvalPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
