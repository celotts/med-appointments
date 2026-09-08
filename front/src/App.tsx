import React from 'react'
import { Routes, Route } from 'react-router-dom'
import AppRoutes from './routes/AppRoutes'
import { AuthProvider } from './contexts/AuthContext'
import './styles/index.css'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/*" element={<AppRoutes />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
