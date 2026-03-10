import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'
import toast from 'react-hot-toast'

/* ── status badge colours ── */
const STATUS_STYLES = {
    pending: 'bg-yellow-100 text-yellow-700',
    processing: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
}

export default function UserDashboard() {
    const { user, refreshUser, logout } = useAuth()

    /* profile */
    const [editMode, setEditMode] = useState(false)
    const [editForm, setEditForm] = useState({ name: '' })

    /* activity */
    const [activities, setActivities] = useState([])

    /* AI query */
    const [queryText, setQueryText] = useState('')
    const [queryBusy, setQueryBusy] = useState(false)
    const [aiQueries, setAiQueries] = useState([])
    const pollTimers = useRef({})           // queryId → intervalId

    /* ── data fetching ── */
    const fetchActivities = useCallback(() => {
        api.get('/user/activity').then(({ data }) => setActivities(data)).catch(() => { })
    }, [])

    const fetchAiQueries = useCallback(() => {
        api.get('/ai/queries').then(({ data }) => setAiQueries(data)).catch(() => { })
    }, [])

    useEffect(() => {
        fetchActivities()
        fetchAiQueries()
    }, [fetchActivities, fetchAiQueries])

    useEffect(() => {
        if (user) setEditForm({ name: user.name })
    }, [user])

    /* ── polling for pending / processing queries ── */
    const startPolling = useCallback((id) => {
        if (pollTimers.current[id]) return
        pollTimers.current[id] = setInterval(async () => {
            try {
                const { data } = await api.get(`/ai/query/${id}`)
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(pollTimers.current[id])
                    delete pollTimers.current[id]
                    setAiQueries(prev => prev.map(q => q.id === id ? data : q))
                    if (data.status === 'completed') toast.success('AI query completed!')
                    if (data.status === 'failed') toast.error('AI query failed')
                    fetchActivities()
                }
            } catch { /* ignore */ }
        }, 2000)
    }, [fetchActivities])

    /* auto-poll any in-flight queries on mount */
    useEffect(() => {
        aiQueries.forEach(q => {
            if ((q.status === 'pending' || q.status === 'processing') && !pollTimers.current[q.id]) {
                startPolling(q.id)
            }
        })
    }, [aiQueries, startPolling])

    /* cleanup intervals on unmount */
    useEffect(() => {
        return () => Object.values(pollTimers.current).forEach(clearInterval)
    }, [])

    /* ── handlers ── */
    const handleSubmitAiQuery = async (e) => {
        e.preventDefault()
        if (!queryText.trim()) return
        setQueryBusy(true)
        try {
            const { data } = await api.post('/ai/query', { input_text: queryText })
            toast.success('Query submitted — processing…')
            setQueryText('')
            setAiQueries(prev => [data, ...prev])
            startPolling(data.id)
            fetchActivities()
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to submit query')
        } finally {
            setQueryBusy(false)
        }
    }

    const handleUpdateProfile = async (e) => {
        e.preventDefault()
        try {
            await api.patch('/user/me', editForm)
            await refreshUser()
            setEditMode(false)
            toast.success('Profile updated')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Update failed')
        }
    }

    if (!user) return null

    return (
        <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">

            {/* ── Profile Card ── */}
            <div className="bg-white rounded-2xl shadow p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold text-gray-800">👤 My Profile</h2>
                    <button onClick={logout} className="text-sm text-red-500 hover:underline">Logout</button>
                </div>

                {!editMode ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 uppercase tracking-wide">Name</p>
                            <p className="text-lg font-semibold">{user.name}</p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 uppercase tracking-wide">Age</p>
                            <p className="text-lg font-semibold">{user.age || '—'}</p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 uppercase tracking-wide">Role</p>
                            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${user.role === 'admin' ? 'bg-indigo-100 text-indigo-700' : 'bg-green-100 text-green-700'}`}>
                                {user.role}
                            </span>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 uppercase tracking-wide">Member Since</p>
                            <p className="text-lg font-semibold">{new Date(user.created_at).toLocaleDateString()}</p>
                        </div>
                        <div className="flex items-end">
                            <button onClick={() => setEditMode(true)} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition text-sm font-medium">
                                Edit Profile
                            </button>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleUpdateProfile} className="flex gap-3 items-end">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                            <input
                                type="text" required
                                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                                value={editForm.name}
                                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                            />
                        </div>
                        <button type="submit" className="px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium">Save</button>
                        <button type="button" onClick={() => setEditMode(false)} className="px-4 py-2.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium">Cancel</button>
                    </form>
                )}
            </div>

            {/* ── AI Query ── */}
            <div className="bg-white rounded-2xl shadow p-6">
                <h2 className="text-xl font-bold text-gray-800 mb-4">🤖 AI Legal Query</h2>
                <form onSubmit={handleSubmitAiQuery} className="flex gap-3">
                    <input
                        type="text"
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                        placeholder="Ask a legal question…"
                        value={queryText}
                        onChange={(e) => setQueryText(e.target.value)}
                    />
                    <button
                        type="submit" disabled={queryBusy}
                        className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium disabled:opacity-50"
                    >
                        {queryBusy ? 'Sending…' : 'Ask AI'}
                    </button>
                </form>

                {/* query history */}
                {aiQueries.length > 0 && (
                    <div className="mt-6 space-y-4">
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Query History</h3>
                        {aiQueries.map(q => (
                            <div key={q.id} className="border border-gray-200 rounded-xl p-4">
                                <div className="flex items-start justify-between gap-4">
                                    <p className="text-sm font-medium text-gray-800">{q.input_text}</p>
                                    <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[q.status] || 'bg-gray-100 text-gray-600'}`}>
                                        {q.status}
                                    </span>
                                </div>
                                {q.response_text && (
                                    <p className="mt-2 text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">{q.response_text}</p>
                                )}
                                <div className="mt-2 flex gap-4 text-xs text-gray-400">
                                    <span>{new Date(q.created_at).toLocaleString()}</span>
                                    {q.tokens_used != null && <span>{q.tokens_used} tokens</span>}
                                    {q.latency_ms != null && <span>{q.latency_ms} ms</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ── Activity Log ── */}
            <div className="bg-white rounded-2xl shadow p-6">
                <h2 className="text-xl font-bold text-gray-800 mb-4">📋 My Activity</h2>
                {activities.length === 0 ? (
                    <p className="text-gray-400 text-center py-8">No activity yet</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-gray-200">
                                    <th className="text-left py-3 px-4 font-semibold text-gray-600">Input</th>
                                    <th className="text-left py-3 px-4 font-semibold text-gray-600">Action</th>
                                    <th className="text-left py-3 px-4 font-semibold text-gray-600">Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {activities.map((a) => (
                                    <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
                                        <td className="py-3 px-4 max-w-xs truncate">{a.input_text}</td>
                                        <td className="py-3 px-4">
                                            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">{a.action_type}</span>
                                        </td>
                                        <td className="py-3 px-4 text-gray-500">{new Date(a.timestamp).toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
