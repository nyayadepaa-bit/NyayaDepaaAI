import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../api/axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    // Restore session on mount
    useEffect(() => {
        api.get('/health').catch(() => {})

        const token = localStorage.getItem('access_token')
        if (token) {
            api.get('/user/me')
                .then(({ data }) => setUser(data))
                .catch(() => { localStorage.clear(); setUser(null) })
                .finally(() => setLoading(false))
        } else {
            setLoading(false)
        }
    }, [])

    const guestLogin = useCallback(async (name, age, city) => {
        const { data } = await api.post('/auth/guest-login', { name, age, city })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        setUser(data.user)
        return data
    }, [])

    const adminLogin = useCallback(async (email, password) => {
        const { data } = await api.post('/auth/admin/login', { email, password })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        setUser(data.user)
        return data
    }, [])

    const logout = useCallback(() => {
        localStorage.clear()
        setUser(null)
    }, [])

    const refreshUser = useCallback(async () => {
        const { data } = await api.get('/user/me')
        setUser(data)
    }, [])

    return (
        <AuthContext.Provider value={{ user, loading, guestLogin, adminLogin, logout, refreshUser }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
}
