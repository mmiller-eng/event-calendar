import { Route, Routes } from 'react-router-dom'
import GenerateView from './pages/GenerateView'
import SourcesView from './pages/SourcesView'

function App() {
  return (
    <Routes>
      <Route path="/" element={<GenerateView />} />
      <Route path="/sources" element={<SourcesView />} />
      <Route path="*" element={<p>Page not found.</p>} />
    </Routes>
  )
}

export default App
