import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

export default function Login() {
    const { guestLogin } = useAuth()
    const navigate = useNavigate()
    const [form, setForm] = useState({ name: '', age: '', city: '' })
    const [busy, setBusy] = useState(false)

    const handle = async (e) => {
        e.preventDefault()
        const age = parseInt(form.age)
        if (!age || age < 1 || age > 150) return toast.error('Please enter a valid age')
        if (!form.city || form.city.trim().length < 2) return toast.error('Please enter your city')
        setBusy(true)
        try {
            await guestLogin(form.name, age, form.city.trim())
            toast.success('Welcome to NyayaDepaaAI!')
            navigate('/chat')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Login failed')
        } finally {
            setBusy(false)
        }
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
                <h1 className="text-center text-xl font-bold text-gray-900 mb-1">NyayaDepaaAI</h1>
                <p className="text-center text-sm text-gray-400 mb-7">Confidential legal guidance for women</p>

                <form onSubmit={handle} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Name</label>
                        <input
                            type="text" required minLength={2}
                            className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 bg-white outline-none transition-all focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                            placeholder="Your full name"
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                        />
                    </div>
                    <div className="flex gap-3">
                        <div className="flex-1">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Age</label>
                            <input
                                type="number" required min={1} max={150}
                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 bg-white outline-none transition-all focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                                placeholder="Age"
                                value={form.age}
                                onChange={(e) => setForm({ ...form, age: e.target.value })}
                            />
                        </div>
                        <div className="flex-1">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">City</label>
                            <input
                                type="text" required minLength={2} maxLength={120}
                                className="w-full px-3.5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-900 bg-white outline-none transition-all focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                                placeholder="Your city"
                                value={form.city}
                                onChange={(e) => setForm({ ...form, city: e.target.value })}
                            />
                        </div>
                    </div>
                    <button
                        type="submit" disabled={busy}
                        className="w-full py-2.5 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {busy ? (
                            <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Starting…</>
                        ) : (
                            <>Begin Consultation <span className="text-base">→</span></>
                        )}
                    </button>
                </form>

                <p className="mt-5 text-center text-xs text-gray-300">
                    🔒 Completely confidential · Personalized to you
                </p>

                <div className="mt-4 text-center">
                    <Link to="/" className="text-xs text-gray-300 hover:text-gray-500 transition-colors">
                        ← Back to Home
                    </Link>
                </div>
            </div>
        </div>
    )
}
