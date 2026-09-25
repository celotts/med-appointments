import { Routes, Route } from 'react-router-dom'
import AppRoutes from './routes/AppRoutes'
import { AuthProvider } from './contexts/AuthContext'
import { UnsavedChangesProvider } from './contexts/UnsavedChangesContext'
import ErrorBoundary from './components/common/ErrorBoundary'
// @ts-ignore CSS is bundled by the frontend toolchain and has no TypeScript declarations.
import './styles/index.css'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <UnsavedChangesProvider>
          <Routes>
            <Route path="/*" element={<AppRoutes />} />
          </Routes>
        </UnsavedChangesProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App