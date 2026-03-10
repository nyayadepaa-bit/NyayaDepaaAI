import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/axios'
import toast from 'react-hot-toast'
import {
    BarChart, Bar, LineChart, Line, AreaChart, Area,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

/* ─── Color Palette (matching main website) ─── */
const COLORS = {
    purple: '#8b5cf6', purpleDark: '#7c3aed', purpleLight: '#f3e8ff',
    blue: '#3b82f6', blueLight: '#dbeafe',
    green: '#10b981', greenLight: '#d1fae5',
    amber: '#f59e0b', amberLight: '#fef3c7',
    red: '#ef4444', redLight: '#fee2e2',
    indigo: '#6366f1', indigoLight: '#e0e7ff',
    pink: '#ec4899', pinkLight: '#fce7f3',
    teal: '#14b8a6', cyan: '#06b6d4',
}
const CHART_COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1', '#14b8a6', '#06b6d4', '#f97316']

/* ─── Industrial SVG Icons (monochrome) ─── */
const IC = {
    chart: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18" /><path strokeLinecap="round" strokeLinejoin="round" d="M7 16v-5m4 5V8m4 8v-3m4 3V6" /></svg>,
    users: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" /></svg>,
    chat: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" /></svg>,
    clipboard: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>,
    download: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>,
    shield: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>,
    check: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    trending: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" /></svg>,
    clock: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    dots: <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" /></svg>,
    trash: <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>,
}

/* ─── Stat Card ─── */
function StatCard({ label, value, icon, color, subLabel }) {
    return (
        <div className="rounded-2xl p-4 border border-gray-100 bg-white shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-0.5">
            <div className="flex items-start justify-between mb-2">
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>{icon}</span>
                {subLabel && <span className="text-[10px] font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">{subLabel}</span>}
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-2">{value}</p>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mt-1">{label}</p>
        </div>
    )
}

/* ─── Chart Wrapper with PDF Export ─── */
function ChartCard({ title, children, id }) {
    const chartRef = useRef(null)
    const exportPDF = async () => {
        if (!chartRef.current) return
        try {
            const canvas = await html2canvas(chartRef.current, { backgroundColor: '#ffffff', scale: 2 })
            const pdf = new jsPDF('landscape', 'mm', 'a4')
            const W = 297, H = 210
            // Watermark
            pdf.saveGraphicsState()
            pdf.setTextColor(230, 230, 230)
            pdf.setFontSize(52)
            pdf.text('NyayaDepaaAI', W / 2, H / 2, { align: 'center', angle: 35 })
            pdf.restoreGraphicsState()
            pdf.setTextColor(0, 0, 0)
            // Chart image
            const imgWidth = 280
            const imgHeight = (canvas.height * imgWidth) / canvas.width
            pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 8, 10, imgWidth, imgHeight)
            // Footer
            pdf.setFontSize(7)
            pdf.setTextColor(180, 180, 180)
            pdf.text('NyayaDepaaAI \u00B7 Confidential', W / 2, H - 5, { align: 'center' })
            pdf.save(`${title.replace(/\s+/g, '_').toLowerCase()}_chart.pdf`)
            toast.success('Chart exported as PDF')
        } catch { toast.error('Export failed') }
    }
    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
                <button onClick={exportPDF}
                    className="text-[10px] font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 px-2.5 py-1 rounded-lg transition-all"
                    title="Export as PDF">
                    PDF
                </button>
            </div>
            <div ref={chartRef} id={id}>{children}</div>
        </div>
    )
}

/* ─── Analytics Tab ─── */
function AnalyticsTab({ data }) {
    if (!data) return <div className="text-center py-12 text-gray-400">Loading analytics...</div>

    const cards = [
        { label: 'Total Users', value: data.total_users, icon: IC.users, color: 'bg-blue-50 text-blue-600', subLabel: `+${data.users_today || 0} today` },
        { label: 'Active Users', value: data.active_users, icon: IC.check, color: 'bg-emerald-50 text-emerald-600' },
        { label: 'Total Queries', value: data.total_inputs, icon: IC.chart, color: 'bg-purple-50 text-purple-600' },
        { label: 'Queries Today', value: data.queries_today, icon: IC.chat, color: 'bg-amber-50 text-amber-600', subLabel: `+${data.inputs_today || 0} inputs` },
        { label: 'Admins', value: data.admin_count, icon: IC.shield, color: 'bg-indigo-50 text-indigo-600' },
        { label: 'Avg Q/User', value: data.avg_queries_per_user || '\u2014', icon: IC.trending, color: 'bg-pink-50 text-pink-600' },
        { label: 'Uptime', value: data.server_uptime, icon: IC.clock, color: 'bg-gray-50 text-gray-600' },
    ]

    const radarData = (data.top_action_types || []).map(a => ({
        subject: a.name.replace(/_/g, ' '),
        count: a.count,
        fullMark: Math.max(...(data.top_action_types || []).map(x => x.count), 1)
    }))
    const cityData = (data.users_by_city || []).slice(0, 8)
    const hourlyData = (data.hourly_activity || []).map(h => ({ hour: h.name, count: h.count }))
    const statusData = (data.ai_query_status_breakdown || [])

    return (
        <div className="space-y-6 animate-fade-up">
            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
                {cards.map(c => <StatCard key={c.label} {...c} />)}
            </div>

            {/* Row 1: Area + Bar charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="New Users (30 days)" id="chart-users">
                    <ResponsiveContainer width="100%" height={240}>
                        <AreaChart data={data.users_per_day || []}>
                            <defs>
                                <linearGradient id="gradUsers" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={COLORS.blue} stopOpacity={0.2} />
                                    <stop offset="95%" stopColor={COLORS.blue} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={d => d.slice(5)} />
                            <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} allowDecimals={false} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                            <Area type="monotone" dataKey="count" stroke={COLORS.blue} fill="url(#gradUsers)" strokeWidth={2} />
                        </AreaChart>
                    </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Activity (30 days)" id="chart-queries">
                    <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={data.queries_per_day || []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={d => d.slice(5)} />
                            <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} allowDecimals={false} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                            <Bar dataKey="count" fill={COLORS.purple} radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </ChartCard>
            </div>

            {/* Row 2: Active Users Line + Hourly Bar */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Active Users per Day" id="chart-active-users">
                    <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={data.active_users_per_day || []}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={d => d.slice(5)} />
                            <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} allowDecimals={false} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                            <Line type="monotone" dataKey="count" stroke={COLORS.green} strokeWidth={2} dot={{ r: 3, fill: COLORS.green }} />
                        </LineChart>
                    </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Hourly Activity Distribution" id="chart-hourly">
                    <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={hourlyData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="hour" tick={{ fontSize: 9, fill: '#9ca3af' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} allowDecimals={false} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                            <Bar dataKey="count" fill={COLORS.amber} radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </ChartCard>
            </div>

            {/* Row 3: Radar + Pie + City */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <ChartCard title="Action Type Distribution" id="chart-radar">
                    <ResponsiveContainer width="100%" height={260}>
                        <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                            <PolarGrid stroke="#e5e7eb" />
                            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#6b7280' }} />
                            <PolarRadiusAxis tick={{ fontSize: 9, fill: '#9ca3af' }} />
                            <Radar dataKey="count" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.25} strokeWidth={2} />
                        </RadarChart>
                    </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Query Status Breakdown" id="chart-status">
                    <ResponsiveContainer width="100%" height={260}>
                        <PieChart>
                            <Pie data={statusData} dataKey="count" nameKey="name" cx="50%" cy="50%"
                                outerRadius={80} innerRadius={40} paddingAngle={3}
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                labelLine={false} style={{ fontSize: '10px' }}>
                                {statusData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Users by City" id="chart-city">
                    <ResponsiveContainer width="100%" height={260}>
                        <BarChart data={cityData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }} allowDecimals={false} />
                            <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }} width={80} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                            <Bar dataKey="count" fill={COLORS.teal} radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </ChartCard>
            </div>
        </div>
    )
}

/* ─── 3-Dot Bulk Action Menu ─── */
function BulkMenu({ count, onDelete, onClear }) {
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    useEffect(() => {
        const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    if (count === 0) return null

    return (
        <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">{count} selected</span>
            <div className="relative" ref={ref}>
                <button onClick={() => setOpen(o => !o)}
                    className="w-8 h-8 flex items-center justify-center rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 transition-all">
                    {IC.dots}
                </button>
                {open && (
                    <div className="absolute right-0 top-10 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50 min-w-[160px] animate-fade-up">
                        <button onClick={() => { onDelete(); setOpen(false) }}
                            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-all">
                            {IC.trash} Delete Selected
                        </button>
                        <button onClick={() => { onClear(); setOpen(false) }}
                            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-500 hover:bg-gray-50 transition-all">
                            Deselect All
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}

/* ─── User Table (with multi-select) ─── */
function UserTable({ users, selectedIds, onSelect, onSelectAll, onToggle, onDelete, onViewConversation }) {
    const nonAdmins = users.filter(u => u.role !== 'admin')
    const allSelected = nonAdmins.length > 0 && nonAdmins.every(u => selectedIds.has(u.id))
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-200 text-gray-500">
                        <th className="py-3 px-2 w-10">
                            <input type="checkbox" checked={allSelected}
                                onChange={() => onSelectAll(nonAdmins.map(u => u.id))}
                                className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-200 cursor-pointer" />
                        </th>
                        <th className="text-left py-3 px-3 font-semibold">Name</th>
                        <th className="text-left py-3 px-3 font-semibold">Email</th>
                        <th className="text-left py-3 px-3 font-semibold">City</th>
                        <th className="text-left py-3 px-3 font-semibold">Role</th>
                        <th className="text-left py-3 px-3 font-semibold">Active</th>
                        <th className="text-left py-3 px-3 font-semibold">Activities</th>
                        <th className="text-left py-3 px-3 font-semibold">Joined</th>
                        <th className="text-left py-3 px-3 font-semibold">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users.map((u) => (
                        <tr key={u.id} className={`border-b border-gray-100 transition-colors ${selectedIds.has(u.id) ? 'bg-purple-50/60' : 'hover:bg-purple-50/30'}`}>
                            <td className="py-3 px-2">
                                {u.role !== 'admin' ? (
                                    <input type="checkbox" checked={selectedIds.has(u.id)}
                                        onChange={() => onSelect(u.id)}
                                        className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-200 cursor-pointer" />
                                ) : <span className="w-4 h-4 block" />}
                            </td>
                            <td className="py-3 px-3 font-medium text-gray-900">{u.name}</td>
                            <td className="py-3 px-3 text-gray-500 text-xs">{u.email || '\u2014'}</td>
                            <td className="py-3 px-3 text-gray-500 text-xs">{u.city || '\u2014'}</td>
                            <td className="py-3 px-3">
                                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                                    {u.role}
                                </span>
                            </td>
                            <td className="py-3 px-3">
                                {u.is_active
                                    ? <span className="text-emerald-500">{'\u25CF'}</span>
                                    : <span className="text-red-400">{'\u25CF'}</span>}
                            </td>
                            <td className="py-3 px-3 text-center">
                                <button onClick={() => onViewConversation(u.id, u.name)}
                                    className="text-purple-600 hover:text-purple-800 font-medium hover:underline transition-all"
                                    title="View conversations">
                                    {u.activity_count}
                                </button>
                            </td>
                            <td className="py-3 px-3 text-gray-400 text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                            <td className="py-3 px-3 space-x-2">
                                <button onClick={() => onToggle(u.id, !u.is_active)}
                                    className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${u.is_active ? 'bg-amber-50 text-amber-700 hover:bg-amber-100' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`}>
                                    {u.is_active ? 'Disable' : 'Enable'}
                                </button>
                                {u.role !== 'admin' && (
                                    <button onClick={() => onDelete(u.id, u.name)}
                                        className="px-2.5 py-1 text-xs rounded-lg font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-all">
                                        Delete
                                    </button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/* ─── Conversation Drill-Down Modal ─── */
function ConversationModal({ userId, userName, onClose }) {
    const [messages, setMessages] = useState([])
    const [loading, setLoading] = useState(true)
    const [dlBusy, setDlBusy] = useState(null) // 'json' | 'txt' | 'pdf' | null

    useEffect(() => {
        if (!userId) return
        setLoading(true)
        api.get(`/admin/conversations/${userId}`)
            .then(({ data }) => setMessages(data))
            .catch(() => toast.error('Failed to load conversations'))
            .finally(() => setLoading(false))
    }, [userId])

    /* ── Per-user download (JSON / TXT from backend) ── */
    const downloadFile = async (format) => {
        setDlBusy(format)
        try {
            const res = await api.get(`/admin/export/user/${userId}?format=${format}`, { responseType: 'blob' })
            const url = window.URL.createObjectURL(res.data)
            const a = document.createElement('a')
            a.href = url
            a.download = res.headers['content-disposition']?.split('filename=')[1] || `user_export.${format}`
            document.body.appendChild(a); a.click(); a.remove()
            window.URL.revokeObjectURL(url)
            toast.success(`Downloaded ${format.toUpperCase()}`)
        } catch { toast.error(`${format.toUpperCase()} download failed`) }
        finally { setDlBusy(null) }
    }

    /* ── Per-user PDF (client-side with watermark) ── */
    const downloadPDF = async () => {
        setDlBusy('pdf')
        try {
            const pdf = new jsPDF('p', 'mm', 'a4')
            const W = 210, H = 297, margin = 15
            let y = margin

            // Watermark on every page
            const addWatermark = () => {
                pdf.saveGraphicsState()
                pdf.setTextColor(220, 220, 220)
                pdf.setFontSize(48)
                const cx = W / 2, cy = H / 2
                pdf.text('NyayaDepaaAI', cx, cy, { align: 'center', angle: 45 })
                pdf.restoreGraphicsState()
                pdf.setTextColor(0, 0, 0)
            }

            addWatermark()

            // Title
            pdf.setFontSize(16)
            pdf.setFont(undefined, 'bold')
            pdf.text(`NyayaDepaaAI — ${userName}'s Conversations`, margin, y)
            y += 8
            pdf.setFontSize(9)
            pdf.setFont(undefined, 'normal')
            pdf.setTextColor(120, 120, 120)
            pdf.text(`Generated: ${new Date().toLocaleString()}  |  Messages: ${messages.length}`, margin, y)
            y += 10
            pdf.setTextColor(0, 0, 0)

            // Messages
            messages.forEach((m, i) => {
                if (y > H - 40) { pdf.addPage(); addWatermark(); y = margin }
                pdf.setFontSize(10)
                pdf.setFont(undefined, 'bold')
                pdf.text(`[${i + 1}]  ${new Date(m.timestamp).toLocaleString()}`, margin, y)
                y += 5
                pdf.setFont(undefined, 'normal')
                pdf.setFontSize(9)

                const qLines = pdf.splitTextToSize(`User: ${m.input_text}`, W - 2 * margin)
                qLines.forEach(l => { if (y > H - 20) { pdf.addPage(); addWatermark(); y = margin }; pdf.text(l, margin + 2, y); y += 4.5 })

                if (m.response_text) {
                    const rLines = pdf.splitTextToSize(`AI: ${m.response_text}`, W - 2 * margin)
                    pdf.setTextColor(80, 80, 80)
                    rLines.forEach(l => { if (y > H - 20) { pdf.addPage(); addWatermark(); y = margin }; pdf.text(l, margin + 2, y); y += 4.5 })
                    pdf.setTextColor(0, 0, 0)
                }
                y += 4
            })

            pdf.save(`nyayadepaaai_${userName.replace(/\s+/g, '_').toLowerCase()}_conversations.pdf`)
            toast.success('Downloaded PDF')
        } catch { toast.error('PDF generation failed') }
        finally { setDlBusy(null) }
    }

    return (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-up"
            onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col"
                onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div>
                        <h3 className="font-bold text-gray-900">{userName}&apos;s Conversations</h3>
                        <p className="text-xs text-gray-400 mt-0.5">{messages.length} messages</p>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Download buttons */}
                        {!loading && messages.length > 0 && (
                            <>
                                <button onClick={() => downloadFile('json')} disabled={!!dlBusy}
                                    className="px-2.5 py-1.5 text-[11px] font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all disabled:opacity-40" title="Download JSON">
                                    {dlBusy === 'json' ? '...' : 'JSON'}
                                </button>
                                <button onClick={() => downloadFile('txt')} disabled={!!dlBusy}
                                    className="px-2.5 py-1.5 text-[11px] font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all disabled:opacity-40" title="Download TXT">
                                    {dlBusy === 'txt' ? '...' : 'TXT'}
                                </button>
                                <button onClick={downloadPDF} disabled={!!dlBusy}
                                    className="px-2.5 py-1.5 text-[11px] font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg transition-all disabled:opacity-40" title="Download PDF">
                                    {dlBusy === 'pdf' ? '...' : 'PDF'}
                                </button>
                            </>
                        )}
                        <button onClick={onClose}
                            className="w-8 h-8 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-500 transition-all ml-1">
                            {'\u2715'}
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <span className="w-6 h-6 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
                        </div>
                    ) : messages.length === 0 ? (
                        <p className="text-center text-gray-400 py-8">No conversations found</p>
                    ) : (
                        messages.map((m, i) => (
                            <div key={m.id} className="group">
                                <div className="flex items-start gap-3">
                                    <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                                        {i + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="bg-purple-50 rounded-xl px-4 py-3 mb-1">
                                            <p className="text-xs font-medium text-purple-600 mb-1">User Query</p>
                                            <p className="text-sm text-gray-800 whitespace-pre-wrap">{m.input_text}</p>
                                        </div>
                                        {m.response_text && (
                                            <div className="bg-gray-50 rounded-xl px-4 py-3 ml-4 border-l-2 border-purple-200">
                                                <p className="text-xs font-medium text-gray-500 mb-1">AI Response</p>
                                                <p className="text-sm text-gray-700 whitespace-pre-wrap">{m.response_text}</p>
                                            </div>
                                        )}
                                        <p className="text-[10px] text-gray-300 mt-1 ml-1">{new Date(m.timestamp).toLocaleString()}</p>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}

/* ─── Activity Table ─── */
function ActivityTable({ activities }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-200 text-gray-500">
                        <th className="text-left py-3 px-3 font-semibold">User</th>
                        <th className="text-left py-3 px-3 font-semibold">Email</th>
                        <th className="text-left py-3 px-3 font-semibold">Input</th>
                        <th className="text-left py-3 px-3 font-semibold">Action</th>
                        <th className="text-left py-3 px-3 font-semibold">IP</th>
                        <th className="text-left py-3 px-3 font-semibold">Time</th>
                    </tr>
                </thead>
                <tbody>
                    {activities.map((a) => (
                        <tr key={a.id} className="border-b border-gray-100 hover:bg-purple-50/30 transition-colors">
                            <td className="py-3 px-3 font-medium text-gray-900">{a.user_name || '\u2014'}</td>
                            <td className="py-3 px-3 text-gray-500 text-xs">{a.user_email || '\u2014'}</td>
                            <td className="py-3 px-3 max-w-xs truncate text-gray-700">{a.input_text}</td>
                            <td className="py-3 px-3">
                                <span className="px-2.5 py-0.5 bg-blue-50 text-blue-600 rounded-full text-xs font-medium">{a.action_type}</span>
                            </td>
                            <td className="py-3 px-3 text-gray-400 text-xs font-mono">{a.ip_address || '\u2014'}</td>
                            <td className="py-3 px-3 text-gray-400 text-xs">{new Date(a.timestamp).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/* ─── Conversations Tab (with multi-select) ─── */
function ConversationsTab({ onViewUser, selectedIds, onSelect, onSelectAll, onBulkDelete }) {
    const [convos, setConvos] = useState({ items: [], total: 0, page: 1, pages: 1 })
    const [search, setSearch] = useState('')
    const [page, setPage] = useState(1)

    const fetchConvos = useCallback(() => {
        const params = { page, page_size: 20 }
        if (search) params.search = search
        api.get('/admin/conversations', { params }).then(({ data }) => setConvos(data)).catch(() => { })
    }, [search, page])

    useEffect(() => { fetchConvos() }, [fetchConvos])

    const allIds = convos.items.map(c => c.user_id)
    const allSelected = allIds.length > 0 && allIds.every(id => selectedIds.has(id))

    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-fade-up">
            <div className="flex items-center gap-3 mb-4">
                <input type="checkbox" checked={allSelected}
                    onChange={() => onSelectAll(allIds)}
                    className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-200 cursor-pointer"
                    title="Select all on page" />
                <input type="text" placeholder="Search by name or email..."
                    className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-purple-200 focus:border-purple-300 outline-none text-sm transition-all"
                    value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
                <BulkMenu count={selectedIds.size}
                    onDelete={() => { onBulkDelete(); setTimeout(fetchConvos, 500) }}
                    onClear={() => onSelectAll([])} />
                <span className="text-xs text-gray-400">{convos.total} users</span>
            </div>

            {convos.items.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No conversations found</p>
            ) : (
                <div className="space-y-2">
                    {convos.items.map(c => (
                        <div key={c.user_id}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${selectedIds.has(c.user_id)
                                ? 'bg-purple-50/60 border-purple-200'
                                : 'bg-gray-50 hover:bg-purple-50 border-transparent hover:border-purple-200'
                                }`}>
                            <input type="checkbox" checked={selectedIds.has(c.user_id)}
                                onChange={() => onSelect(c.user_id)}
                                className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-200 cursor-pointer flex-shrink-0" />
                            <button onClick={() => onViewUser(c.user_id, c.user_name || 'User')}
                                className="flex-1 flex items-center justify-between text-left group">
                                <div className="flex items-center gap-3">
                                    <div className="w-9 h-9 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold">
                                        {(c.user_name || '?')[0].toUpperCase()}
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-900 text-sm">{c.user_name || 'Unknown'}</p>
                                        <p className="text-xs text-gray-400">{c.user_email || 'Guest'}{c.city ? ` \u00B7 ${c.city}` : ''}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs font-medium text-purple-600 bg-purple-50 group-hover:bg-purple-100 px-2.5 py-1 rounded-full transition-all">
                                        {c.message_count} messages
                                    </span>
                                    {c.last_active && (
                                        <p className="text-[10px] text-gray-300 mt-1">{new Date(c.last_active).toLocaleDateString()}</p>
                                    )}
                                </div>
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {convos.pages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-4">
                    <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                        className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-200 transition-all">{'\u2190'} Prev</button>
                    <span className="text-xs text-gray-400">Page {convos.page} of {convos.pages}</span>
                    <button disabled={page >= convos.pages} onClick={() => setPage(p => p + 1)}
                        className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-200 transition-all">Next {'\u2192'}</button>
                </div>
            )}
        </div>
    )
}

/* ─── Pagination ─── */
function Pagination({ page, pages, onPageChange }) {
    if (pages <= 1) return null
    return (
        <div className="flex items-center justify-center gap-2 mt-4">
            <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}
                className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-200 transition-all">{'\u2190'} Prev</button>
            <span className="text-xs text-gray-400">Page {page} of {pages}</span>
            <button disabled={page >= pages} onClick={() => onPageChange(page + 1)}
                className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg disabled:opacity-30 hover:bg-gray-200 transition-all">Next {'\u2192'}</button>
        </div>
    )
}

/* ─── Audit Log Table ─── */
function AuditLogTable({ logs }) {
    if (logs.length === 0) return <p className="text-gray-400 text-center py-8">No audit records</p>
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-200 text-gray-500">
                        <th className="text-left py-3 px-3 font-semibold">Admin</th>
                        <th className="text-left py-3 px-3 font-semibold">Action</th>
                        <th className="text-left py-3 px-3 font-semibold">Target</th>
                        <th className="text-left py-3 px-3 font-semibold">Details</th>
                        <th className="text-left py-3 px-3 font-semibold">IP</th>
                        <th className="text-left py-3 px-3 font-semibold">Time</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((l) => (
                        <tr key={l.id} className="border-b border-gray-100 hover:bg-purple-50/30 transition-colors">
                            <td className="py-3 px-3 text-xs text-gray-700">{l.admin_email || '\u2014'}</td>
                            <td className="py-3 px-3">
                                <span className="px-2.5 py-0.5 bg-amber-50 text-amber-700 rounded-full text-xs font-medium">{l.action}</span>
                            </td>
                            <td className="py-3 px-3 text-xs text-gray-500">{l.target_email || '\u2014'}</td>
                            <td className="py-3 px-3 text-xs max-w-xs truncate text-gray-500">{l.details || '\u2014'}</td>
                            <td className="py-3 px-3 text-gray-400 text-xs font-mono">{l.ip_address || '\u2014'}</td>
                            <td className="py-3 px-3 text-gray-400 text-xs">{new Date(l.timestamp).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/* ─── Export Tab (conversation-centric, industrial) ─── */
function ExportTab() {
    const [meta, setMeta] = useState(null)
    const [lastDownload, setLastDownload] = useState(() => localStorage.getItem('admin_last_export'))
    const [downloading, setDownloading] = useState(false)

    useEffect(() => {
        api.get('/admin/export/meta').then(({ data }) => setMeta(data)).catch(() => { })
    }, [])

    const doExport = async (format) => {
        if (lastDownload && meta) {
            const lastTime = new Date(lastDownload).getTime()
            const latestTime = new Date(meta.latest_timestamp).getTime()
            if (latestTime <= lastTime) {
                const ok = window.confirm('No new data since your last download. Download again?')
                if (!ok) return
            }
        }
        setDownloading(true)
        try {
            const response = await api.get(`/admin/export?format=${format}`, { responseType: 'blob' })
            const url = window.URL.createObjectURL(response.data)
            const a = document.createElement('a')
            a.href = url
            a.download = response.headers['content-disposition']?.split('filename=')[1] || `export.${format}`
            document.body.appendChild(a)
            a.click()
            a.remove()
            window.URL.revokeObjectURL(url)
            const now = new Date().toISOString()
            localStorage.setItem('admin_last_export', now)
            setLastDownload(now)
            toast.success(`Exported as ${format.toUpperCase()}`)
        } catch {
            toast.error('Export failed')
        } finally {
            setDownloading(false)
        }
    }

    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 animate-fade-up">
            <div className="max-w-xl mx-auto">
                {/* Header */}
                <div className="flex items-center gap-4 mb-6 pb-4 border-b border-gray-100">
                    <span className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600">
                        {IC.download}
                    </span>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Export Conversations</h3>
                        <p className="text-sm text-gray-400">Full user-bot conversation history with all metadata</p>
                    </div>
                </div>

                {/* Stats */}
                {meta && (
                    <div className="grid grid-cols-2 gap-3 mb-6">
                        <div className="rounded-xl bg-gray-50 border border-gray-100 p-4">
                            <p className="text-xl font-bold text-gray-900 font-mono">{meta.total_users_with_convos || 0}</p>
                            <p className="text-[11px] text-gray-400 uppercase tracking-wider mt-1">Users with conversations</p>
                        </div>
                        <div className="rounded-xl bg-gray-50 border border-gray-100 p-4">
                            <p className="text-xl font-bold text-gray-900 font-mono">{meta.total_messages || 0}</p>
                            <p className="text-[11px] text-gray-400 uppercase tracking-wider mt-1">Total messages</p>
                        </div>
                    </div>
                )}

                {/* Info */}
                <div className="bg-gray-50 rounded-xl border border-gray-100 p-4 mb-6 text-xs text-gray-500 space-y-1">
                    <p>Export includes for each user: name, email, age, city, role, status, join date, last login</p>
                    <p>Each conversation: user query, AI response, tokens, latency, status, timestamp</p>
                    <p>Conversations are grouped by user and sorted by message count</p>
                </div>

                {lastDownload && (
                    <p className="text-xs text-gray-300 mb-4">Last downloaded: {new Date(lastDownload).toLocaleString()}</p>
                )}

                {/* Buttons */}
                <div className="flex gap-3">
                    <button onClick={() => doExport('json')} disabled={downloading}
                        className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-50 shadow-sm hover:shadow">
                        {downloading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : IC.download}
                        JSON
                    </button>
                    <button onClick={() => doExport('txt')} disabled={downloading}
                        className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-white hover:bg-gray-50 text-gray-900 text-sm font-semibold rounded-xl transition-all disabled:opacity-50 border border-gray-200 shadow-sm hover:shadow">
                        {downloading ? <span className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" /> : IC.download}
                        TXT
                    </button>
                </div>
            </div>
        </div>
    )
}

/* ============================================================
   Admin Dashboard - Main Component
   ============================================================ */
export default function AdminDashboard() {
    const { user, logout: authLogout } = useAuth()
    const [tab, setTab] = useState('analytics')
    const [analytics, setAnalytics] = useState(null)
    const [users, setUsers] = useState([])
    const [activityData, setActivityData] = useState({ items: [], total: 0, page: 1, pages: 1 })
    const [auditLogs, setAuditLogs] = useState([])
    const [userSearch, setUserSearch] = useState('')
    const [roleFilter, setRoleFilter] = useState('')
    // Activity filters
    const [actSearch, setActSearch] = useState('')
    const [actEmail, setActEmail] = useState('')
    const [actActionType, setActActionType] = useState('')
    const [actDateFrom, setActDateFrom] = useState('')
    const [actDateTo, setActDateTo] = useState('')
    const [actPage, setActPage] = useState(1)
    // Conversation modal
    const [convoModal, setConvoModal] = useState(null)
    // Multi-select
    const [selectedUsers, setSelectedUsers] = useState(new Set())
    const [selectedConvos, setSelectedConvos] = useState(new Set())

    const fetchAnalytics = useCallback(() => {
        api.get('/admin/analytics/enhanced').then(({ data }) => setAnalytics(data)).catch(() => {
            api.get('/admin/analytics').then(({ data }) => setAnalytics(data)).catch(() => { })
        })
    }, [])

    const fetchUsers = useCallback(() => {
        const params = {}
        if (userSearch) params.search = userSearch
        if (roleFilter) params.role = roleFilter
        api.get('/admin/users', { params }).then(({ data }) => setUsers(data)).catch(() => { })
    }, [userSearch, roleFilter])

    const fetchActivities = useCallback(() => {
        const params = { page: actPage, page_size: 50 }
        if (actSearch) params.search = actSearch
        if (actEmail) params.email = actEmail
        if (actActionType) params.action_type = actActionType
        if (actDateFrom) params.date_from = actDateFrom
        if (actDateTo) params.date_to = actDateTo
        api.get('/admin/activity', { params }).then(({ data }) => setActivityData(data)).catch(() => { })
    }, [actSearch, actEmail, actActionType, actDateFrom, actDateTo, actPage])

    const fetchAuditLogs = useCallback(() => {
        api.get('/admin/audit-log').then(({ data }) => setAuditLogs(data)).catch(() => { })
    }, [])

    useEffect(() => { fetchAnalytics() }, [fetchAnalytics])
    useEffect(() => { fetchUsers() }, [fetchUsers])
    useEffect(() => { fetchActivities() }, [fetchActivities])
    useEffect(() => { if (tab === 'audit') fetchAuditLogs() }, [tab, fetchAuditLogs])

    const handleToggle = async (id, active) => {
        try {
            await api.patch(`/admin/users/${id}/toggle`, { is_active: active })
            toast.success(`User ${active ? 'enabled' : 'disabled'}`)
            fetchUsers(); fetchAnalytics()
        } catch (err) { toast.error(err.response?.data?.detail || 'Action failed') }
    }

    const handleDelete = async (id, name) => {
        if (!window.confirm(`Delete user "${name}"? This cannot be undone.`)) return
        try {
            await api.delete(`/admin/users/${id}`)
            toast.success('User deleted')
            setSelectedUsers(prev => { const s = new Set(prev); s.delete(id); return s })
            fetchUsers(); fetchAnalytics()
        } catch (err) { toast.error(err.response?.data?.detail || 'Delete failed') }
    }

    /* ── Bulk delete: users ── */
    const handleBulkDeleteUsers = async () => {
        if (selectedUsers.size === 0) return
        if (!window.confirm(`Delete ${selectedUsers.size} selected user(s)? This cannot be undone.`)) return
        try {
            await api.post('/admin/users/bulk-delete', { user_ids: [...selectedUsers] })
            toast.success(`${selectedUsers.size} user(s) deleted`)
            setSelectedUsers(new Set())
            fetchUsers(); fetchAnalytics()
        } catch (err) { toast.error(err.response?.data?.detail || 'Bulk delete failed') }
    }

    /* ── Bulk delete: conversations ── */
    const handleBulkDeleteConvos = async () => {
        if (selectedConvos.size === 0) return
        if (!window.confirm(`Delete conversations for ${selectedConvos.size} user(s)? This removes all conversations AND activity records. This cannot be undone.`)) return
        try {
            const { data } = await api.post('/admin/conversations/bulk-delete', { user_ids: [...selectedConvos] })
            toast.success(data.message || 'Conversations deleted')
            setSelectedConvos(new Set())
            // Refresh all dashboard data since activity + analytics are also affected
            fetchUsers(); fetchAnalytics()
        } catch (err) { toast.error(err.response?.data?.detail || 'Bulk delete failed') }
    }

    /* ── Selection helpers ── */
    const toggleSelection = (set, setter) => (id) => {
        setter(prev => {
            const s = new Set(prev)
            s.has(id) ? s.delete(id) : s.add(id)
            return s
        })
    }

    const toggleAllSelection = (set, setter) => (ids) => {
        setter(prev => {
            const allIn = ids.length > 0 && ids.every(id => prev.has(id))
            return allIn ? new Set() : new Set(ids)
        })
    }

    const openConvoModal = (userId, userName) => setConvoModal({ userId, userName })

    const navTo = useNavigate()
    const logout = () => { authLogout(); navTo('/admin/login') }

    const tabs = [
        { key: 'analytics', label: 'Analytics', icon: IC.chart },
        { key: 'users', label: 'Users', icon: IC.users },
        { key: 'conversations', label: 'Conversations', icon: IC.chat },
        { key: 'activity', label: 'Activity', icon: IC.clipboard },
        { key: 'export', label: 'Export', icon: IC.download },
        { key: 'audit', label: 'Audit Log', icon: IC.shield },
    ]

    return (
        <div className="min-h-screen" style={{ background: '#fafaf9', fontFamily: "'Inter', system-ui, sans-serif" }}>
            {/* Top Bar */}
            <div className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <img src="/logo.png" alt="NyayaDepaaAI" className="w-8 h-8" />
                        <div>
                            <h1 className="text-base font-bold text-gray-900">NyayaDepaaAI</h1>
                            <p className="text-[10px] text-gray-400 -mt-0.5">Admin Dashboard</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                        <a href="/"
                            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 hover:bg-gray-100 rounded-lg transition-all border border-gray-200">
                            {'\u2190'} Home
                        </a>
                        <span className="text-xs text-gray-400 hidden sm:inline">{user?.email}</span>
                        <button onClick={logout}
                            className="px-3 py-1.5 text-xs font-medium text-red-500 bg-red-50 hover:bg-red-100 rounded-lg transition-all">
                            Logout
                        </button>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
                {/* Tabs */}
                <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1">
                    {tabs.map(t => (
                        <button key={t.key} onClick={() => setTab(t.key)}
                            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${tab === t.key
                                ? 'bg-purple-600 text-white shadow-sm shadow-purple-200'
                                : 'bg-white text-gray-500 hover:bg-gray-50 border border-gray-100'
                                }`}>
                            <span className="w-4 h-4 flex-shrink-0">{t.icon}</span> {t.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                {tab === 'analytics' && <AnalyticsTab data={analytics} />}

                {tab === 'users' && (
                    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-fade-up">
                        <div className="flex flex-wrap gap-3 mb-4">
                            <input type="text" placeholder="Search by name or email..."
                                className="flex-1 min-w-[200px] px-4 py-2.5 bg-gray-50 border border-gray-200 text-gray-900 rounded-xl focus:ring-2 focus:ring-purple-200 focus:border-purple-300 outline-none text-sm transition-all"
                                value={userSearch} onChange={e => setUserSearch(e.target.value)} />
                            <select
                                className="px-4 py-2.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200"
                                value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
                                <option value="">All Roles</option>
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                            </select>
                            <BulkMenu count={selectedUsers.size}
                                onDelete={handleBulkDeleteUsers}
                                onClear={() => setSelectedUsers(new Set())} />
                        </div>
                        {users.length === 0 ? (
                            <p className="text-gray-400 text-center py-8">No users found</p>
                        ) : (
                            <UserTable
                                users={users}
                                selectedIds={selectedUsers}
                                onSelect={toggleSelection(selectedUsers, setSelectedUsers)}
                                onSelectAll={toggleAllSelection(selectedUsers, setSelectedUsers)}
                                onToggle={handleToggle}
                                onDelete={handleDelete}
                                onViewConversation={openConvoModal}
                            />
                        )}
                    </div>
                )}

                {tab === 'conversations' && (
                    <ConversationsTab
                        onViewUser={openConvoModal}
                        selectedIds={selectedConvos}
                        onSelect={toggleSelection(selectedConvos, setSelectedConvos)}
                        onSelectAll={toggleAllSelection(selectedConvos, setSelectedConvos)}
                        onBulkDelete={handleBulkDeleteConvos}
                    />
                )}

                {tab === 'activity' && (
                    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-fade-up">
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                            <input type="text" placeholder="Search text..."
                                className="px-3 py-2.5 bg-gray-50 border border-gray-200 text-gray-900 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200 transition-all"
                                value={actSearch} onChange={e => { setActSearch(e.target.value); setActPage(1) }} />
                            <input type="text" placeholder="Filter by email..."
                                className="px-3 py-2.5 bg-gray-50 border border-gray-200 text-gray-900 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200 transition-all"
                                value={actEmail} onChange={e => { setActEmail(e.target.value); setActPage(1) }} />
                            <select
                                className="px-3 py-2.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200"
                                value={actActionType} onChange={e => { setActActionType(e.target.value); setActPage(1) }}>
                                <option value="">All Actions</option>
                                <option value="chat_query">Chat Query</option>
                                <option value="chatbot_query">Chatbot Query</option>
                                <option value="ai_query">AI Query</option>
                                <option value="login">Login</option>
                            </select>
                            <input type="date"
                                className="px-3 py-2.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200"
                                value={actDateFrom} onChange={e => { setActDateFrom(e.target.value); setActPage(1) }} />
                            <input type="date"
                                className="px-3 py-2.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-sm outline-none focus:ring-2 focus:ring-purple-200"
                                value={actDateTo} onChange={e => { setActDateTo(e.target.value); setActPage(1) }} />
                        </div>
                        <div className="text-xs text-gray-400 mb-3">{activityData.total} results {'\u2014'} page {activityData.page} of {activityData.pages}</div>
                        {activityData.items.length === 0 ? (
                            <p className="text-gray-400 text-center py-8">No activity recorded</p>
                        ) : (
                            <>
                                <ActivityTable activities={activityData.items} />
                                <Pagination page={activityData.page} pages={activityData.pages} onPageChange={setActPage} />
                            </>
                        )}
                    </div>
                )}

                {tab === 'export' && <ExportTab />}

                {tab === 'audit' && (
                    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-fade-up">
                        <h3 className="text-base font-semibold text-gray-800 mb-4">Admin Action Audit Trail</h3>
                        <AuditLogTable logs={auditLogs} />
                    </div>
                )}
            </div>

            {/* Conversation Modal */}
            {convoModal && (
                <ConversationModal
                    userId={convoModal.userId}
                    userName={convoModal.userName}
                    onClose={() => setConvoModal(null)}
                />
            )}
        </div>
    )
}
