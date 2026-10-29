import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { TopicsProvider } from './context/TopicsContext'
import Layout from './components/Layout'
import LoginPage from './features/auth/LoginPage.jsx'
import RegisterPage from './features/auth/RegisterPage.jsx'
import ProtectedRoute from './features/auth/ProtectedRoute.jsx'
import RedirectIfAuthenticated from './features/auth/RedirectIfAuthenticated.jsx'
import SentencesPage from './features/sentences/SentencesPage.jsx'
import SessionPage from './features/session/SessionPage.jsx'
import DashboardPage from './features/stats/DashboardPage.jsx'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<RedirectIfAuthenticated />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <TopicsProvider>
                  <Layout />
                </TopicsProvider>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/sentences" element={<SentencesPage />} />
              <Route path="/review" element={<SessionPage />} />
              <Route path="/stats" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App