import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

export default function AdminLogin() {
    const { user, loading, adminLogin } = useAuth()
    const navigate = useNavigate()
    const [form, setForm] = useState({ email: '', password: '' })
    const [busy, setBusy] = useState(false)
    const [showPw, setShowPw] = useState(false)

    // If already logged in as admin, go straight to dashboard
    if (!loading && user?.role === 'admin') return <Navigate to="/admin" replace />

    const handle = async (e) => {
        e.preventDefault()
        setBusy(true)
        try {
            await adminLogin(form.email, form.password)
            toast.success('Welcome, Admin!')
            navigate('/admin')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Admin login failed')
        } finally {
            setBusy(false)
        }
    }

    // Show a friendly redirect for non-admin users who land here
    if (!loading && user && user.role !== 'admin') {
        return (
            <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#fafaf9' }}>
                <div className="w-full max-w-sm text-center animate-fade-up">
                    <div className="flex justify-center mb-5">
                        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: '#f5f3ff', padding: '8px' }}>
                            <img src="/logo.png" alt="NyayaDepaaAI" className="w-7 h-7" />
                        </div>
                    </div>
                    <h1 className="text-xl font-bold text-gray-900 mb-2">Admin Access Only</h1>
                    <p className="text-sm text-gray-400 mb-6">You are logged in as <span className="font-medium text-gray-600">{user.name}</span>, but this area is restricted to administrators.</p>
                    <a href="/"
                        className="w-full block py-2.5 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-lg transition-all mb-3 text-center">
                        Go to Chatbot
                    </a>
                    <a href="/"
                        className="block w-full py-2.5 text-center text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-700 transition-all">
                        ← Back to Home
                    </a>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#fafaf9' }}>
            <div className="w-full max-w-sm animate-fade-up">
                {/* Icon */}
                <div className="flex justify-center mb-5">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ background: '#f5f3ff', padding: '8px' }}>
                        <img src="/logo.png" alt="NyayaDepaaAI" className="w-7 h-7" />
                    </div>
                </div>

                {/* Title */}
                <h1 className="text-center text-xl font-bold text-gray-900 mb-1">Admin Portal</h1>
                <p className="text-center text-sm text-gray-400 mb-7">NyayaDepaaAI Administration</p>

                <form onSubmit={handle} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Email</label>
                        <input
                            type="email" required
                            className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 bg-white outline-none transition-all focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                            placeholder="admin@NyayaDepaaAI.com"
                            value={form.email}
                            onChange={(e) => setForm({ ...form, email: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Password</label>
                        <div className="relative">
                            <input
                                type={showPw ? 'text' : 'password'} required
                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 bg-white outline-none transition-all focus:border-violet-300 focus:ring-2 focus:ring-violet-100 pr-10"
                                placeholder="••••••••"
                                value={form.password}
                                onChange={(e) => setForm({ ...form, password: e.target.value })}
                            />
                            <button type="button" onClick={() => setShowPw(!showPw)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs">
                                {showPw ? 'Hide' : 'Show'}
                            </button>
                        </div>
                    </div>
                    <button
                        type="submit" disabled={busy}
                        className="w-full py-2.5 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {busy ? (
                            <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Signing in…</>
                        ) : (
                            <>Sign In <span className="text-base">→</span></>
                        )}
                    </button>
                </form>

                {/* Divider */}
                <div className="flex items-center gap-3 my-6">
                    <div className="flex-1 h-px bg-gray-200" />
                    <span className="text-xs text-gray-300 uppercase tracking-wider">or</span>
                    <div className="flex-1 h-px bg-gray-200" />
                </div>

                <Link to="/"
                    className="block w-full py-2.5 text-center text-sm font-medium text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-700 transition-all">
                    ← Back to Home
                </Link>

                <p className="mt-5 text-center text-xs text-gray-300">
                    🔒 Restricted access · Authorized admins only
                </p>
            </div>
        </div>
    )
}
