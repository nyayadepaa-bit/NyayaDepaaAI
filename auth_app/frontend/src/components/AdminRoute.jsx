import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AdminRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
            </div>
        )
    }

    if (!user) return <Navigate to="/admin/login" replace />
    if (user.role !== 'admin') {
        window.location.href = '/'
        return null
    }
    return children
}
