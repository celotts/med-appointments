import { Routes, Route } from 'react-router-dom'
import AppRoutes from './routes/AppRoutes'
import { AuthProvider } from './contexts/AuthContext'
import ErrorBoundary from './components/common/ErrorBoundary'
// @ts-ignore CSS is bundled by the frontend toolchain and has no TypeScript declarations.
import './styles/index.css'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Routes>
          <Route path="/*" element={<AppRoutes />} />
        </Routes>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App