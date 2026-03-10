import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <nav className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
                <Link to="/" className="text-xl font-bold text-primary-600 flex items-center gap-2">
                    <img src="/logo.png" alt="NyayaDepaaAI" className="w-6 h-6" /> NyayaDepaaAI
                </Link>

                <div className="flex items-center gap-4 text-sm">
                    {user ? (
                        <>
                            <span className="text-gray-500 hidden sm:inline">
                                {user.name} ({user.role})
                            </span>
                            {user.role === 'admin' && (
                                <Link to="/admin" className="text-indigo-600 hover:text-indigo-700 font-medium">
                                    Admin Panel
                                </Link>
                            )}
                            <Link to="/dashboard" className="text-primary-600 hover:text-primary-700 font-medium">
                                Dashboard
                            </Link>
                            <button onClick={handleLogout} className="text-red-500 hover:text-red-600 font-medium">
                                Logout
                            </button>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium">
                                Get Started
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    )
}
