import { useState, useEffect, useCallback } from 'react';
import api from '../utils/api';
import { getToken, setToken, getUser, setUser, clearAuth } from '../utils/tokenStorage';

export function useAuth() {
    const [user, setUserState] = useState(getUser());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const login = useCallback(async (email, password) => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.post('/auth/login', { email, password });
            setToken(data.token);
            setUser(data.user);
            setUserState(data.user);
            return data;
        } catch (err) {
            const msg = err.response?.data?.message || 'Login failed';
            setError(msg);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const register = useCallback(async (name, email, password) => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.post('/auth/register', { name, email, password });
            setToken(data.token);
            setUser(data.user);
            setUserState(data.user);
            return data;
        } catch (err) {
            const msg = err.response?.data?.message || 'Registration failed';
            setError(msg);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const logout = useCallback(() => {
        clearAuth();
        setUserState(null);
    }, []);

    return { user, loading, error, login, register, logout };
}