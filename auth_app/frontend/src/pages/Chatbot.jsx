import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'
import toast from 'react-hot-toast'

/* ── status colours ── */
const SB = {
    pending: 'bg-yellow-100 text-yellow-700',
    processing: 'bg-blue-100 text-blue-700',
    completed: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
}

export default function Chatbot() {
    const { user, logout: authLogout } = useAuth()
    const navigate = useNavigate()
    const [queryText, setQueryText] = useState('')
    const [busy, setBusy] = useState(false)
    const [messages, setMessages] = useState([])
    const bottomRef = useRef(null)
    const pollTimers = useRef({})

    /* fetch past queries on mount */
    const fetchHistory = useCallback(() => {
        api.get('/ai/queries').then(({ data }) => setMessages(data)).catch(() => { })
    }, [])

    useEffect(() => { fetchHistory() }, [fetchHistory])

    /* auto-scroll to latest */
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    /* polling for in-flight queries */
    const startPolling = useCallback((id) => {
        if (pollTimers.current[id]) return
        pollTimers.current[id] = setInterval(async () => {
            try {
                const { data } = await api.get(`/ai/query/${id}`)
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(pollTimers.current[id])
                    delete pollTimers.current[id]
                    setMessages(prev => prev.map(q => q.id === id ? data : q))
                    if (data.status === 'completed') toast.success('Response received!')
                    if (data.status === 'failed') toast.error('Query failed')
                }
            } catch { /* ignore */ }
        }, 2000)
    }, [])

    useEffect(() => {
        messages.forEach(q => {
            if ((q.status === 'pending' || q.status === 'processing') && !pollTimers.current[q.id]) {
                startPolling(q.id)
            }
        })
    }, [messages, startPolling])

    useEffect(() => {
        return () => Object.values(pollTimers.current).forEach(clearInterval)
    }, [])

    /* submit */
    const handleSend = async (e) => {
        e.preventDefault()
        if (!queryText.trim()) return
        setBusy(true)
        try {
            const { data } = await api.post('/ai/query', { input_text: queryText })
            setQueryText('')
            setMessages(prev => [...prev, data])
            startPolling(data.id)
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to send query')
        } finally {
            setBusy(false)
        }
    }

    const handleLogout = () => { authLogout(); navigate('/') }

    if (!user) return null

    return (
        <div className="flex flex-col h-screen" style={{ background: '#fafaf9' }}>
            {/* ── Top bar ── */}
            <header className="bg-white border-b border-gray-100 shadow-sm flex-shrink-0 z-30">
                <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-2.5">
                        <img src="/logo.png" alt="NyayaDepaaAI" className="w-7 h-7" />
                        <div>
                            <span className="text-base font-bold text-gray-900">NyayaDepaaAI</span>
                            <p className="text-[10px] text-gray-400 -mt-0.5 leading-none">AI Legal Advisor</p>
                        </div>
                    </Link>
                    <div className="flex items-center gap-3 text-sm">
                        <span className="text-xs text-gray-400 hidden sm:inline">{user.name}</span>
                        <Link to="/"
                            className="px-3 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 hover:bg-gray-100 rounded-lg transition-all border border-gray-200">
                            ← Home
                        </Link>
                        <button onClick={handleLogout}
                            className="px-3 py-1.5 text-xs font-medium text-red-500 bg-red-50 hover:bg-red-100 rounded-lg transition-all">
                            Logout
                        </button>
                    </div>
                </div>
            </header>

            {/* ── Chat area ── */}
            <main className="flex-1 overflow-y-auto">
                <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
                    {messages.length === 0 && (
                        <div className="text-center py-20 animate-fade-up">
                            <div className="w-16 h-16 rounded-2xl bg-purple-50 flex items-center justify-center mx-auto mb-4">
                                <img src="/logo.png" alt="" className="w-9 h-9" />
                            </div>
                            <h2 className="text-lg font-bold text-gray-800 mb-1">Welcome, {user.name}!</h2>
                            <p className="text-sm text-gray-400 max-w-md mx-auto">
                                Ask any legal question below. Your conversations are private and confidential.
                            </p>
                        </div>
                    )}

                    {messages.map((m) => (
                        <div key={m.id} className="animate-fade-up">
                            {/* User bubble */}
                            <div className="flex justify-end mb-2">
                                <div className="max-w-[80%] bg-purple-600 text-white rounded-2xl rounded-tr-md px-4 py-3 shadow-sm">
                                    <p className="text-sm whitespace-pre-wrap">{m.input_text}</p>
                                    <p className="text-[10px] text-purple-200 mt-1.5 text-right">
                                        {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                </div>
                            </div>

                            {/* AI bubble */}
                            <div className="flex justify-start mb-1">
                                <div className="max-w-[85%] flex gap-2.5">
                                    <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0 mt-1">
                                        <img src="/logo.png" alt="" className="w-4 h-4" />
                                    </div>
                                    <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm flex-1">
                                        {m.status === 'completed' && m.response_text ? (
                                            <p className="text-sm text-gray-700 whitespace-pre-wrap">{m.response_text}</p>
                                        ) : m.status === 'failed' ? (
                                            <p className="text-sm text-red-500">Failed to generate response. Please try again.</p>
                                        ) : (
                                            <div className="flex items-center gap-2">
                                                <span className="w-4 h-4 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
                                                <span className="text-xs text-gray-400">Thinking…</span>
                                            </div>
                                        )}
                                        <div className="flex items-center gap-3 mt-2">
                                            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${SB[m.status] || 'bg-gray-100 text-gray-500'}`}>
                                                {m.status}
                                            </span>
                                            {m.tokens_used != null && (
                                                <span className="text-[10px] text-gray-300">{m.tokens_used} tokens</span>
                                            )}
                                            {m.latency_ms != null && (
                                                <span className="text-[10px] text-gray-300">{Math.round(m.latency_ms)} ms</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={bottomRef} />
                </div>
            </main>

            {/* ── Input bar ── */}
            <footer className="bg-white border-t border-gray-100 flex-shrink-0">
                <form onSubmit={handleSend} className="max-w-3xl mx-auto px-4 py-3 flex gap-3">
                    <input
                        type="text"
                        className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 outline-none focus:ring-2 focus:ring-purple-200 focus:border-purple-300 transition-all"
                        placeholder="Ask a legal question…"
                        value={queryText}
                        onChange={(e) => setQueryText(e.target.value)}
                        disabled={busy}
                    />
                    <button
                        type="submit" disabled={busy || !queryText.trim()}
                        className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-40 flex items-center gap-2 shadow-sm hover:shadow"
                    >
                        {busy ? (
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                            </svg>
                        )}
                        Send
                    </button>
                </form>
            </footer>
        </div>
    )
}
