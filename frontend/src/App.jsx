import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import FaqPage from './pages/FaqPage'
import DocumentPage from './pages/DocumentPage'
import ComplaintsPage from './pages/ComplaintsPage'
import ModerationPage from './pages/ModerationPage'
import SimulatorPage from './pages/SimulatorPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/faq" element={<FaqPage />} />
                    <Route path="/docs" element={<DocumentPage />} />
                    <Route path="/complaints" element={<ComplaintsPage />} />
                    <Route path="/moderation" element={<ModerationPage />} />
                    <Route path="/simulator" element={<SimulatorPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
