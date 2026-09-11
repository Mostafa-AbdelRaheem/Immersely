import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { TopicsProvider } from './context/TopicsContext'
import Home from './pages/Home.jsx'
import LoginPage from './features/auth/LoginPage.jsx'
import RegisterPage from './features/auth/RegisterPage.jsx'
import ProtectedRoute from './features/auth/ProtectedRoute.jsx'
import RedirectIfAuthenticated from './features/auth/RedirectIfAuthenticated.jsx'
import SentencesPage from './features/sentences/SentencesPage.jsx'

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
            <Route path="/" element={<Home />} />
            <Route
              path="/sentences"
              element={
                <TopicsProvider>
                  <SentencesPage />
                </TopicsProvider>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App