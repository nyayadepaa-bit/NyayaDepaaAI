import { Routes, Route, Navigate } from 'react-router-dom'
import AdminRoute from './components/AdminRoute'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'

/*
 * React app serves ADMIN routes only.
 * The main website (landing page + chatbot widget) is the original
 * frontend/index.html served by the FastAPI main app on port 8000.
 */

export default function App() {
    return (
        <Routes>
            {/* Admin flow */}
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />

            {/* Everything else → redirect to main site */}
            <Route path="*" element={<RedirectToMainSite />} />
        </Routes>
    )
}

/* Redirect non-admin routes back to the original main site */
function RedirectToMainSite() {
    window.location.href = '/'
    return null
}
