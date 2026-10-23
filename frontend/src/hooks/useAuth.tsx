import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User } from '../types';
import api from '../services/api';

interface AuthContextValue {
    user: User | null;
    token: string | null;
    login: (token: string, user: User) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const storedToken = localStorage.getItem('access_token');
        if (!storedToken) {
            setIsLoading(false);
            return;
        }
        setToken(storedToken);
        api.get<User>('/auth/me')
            .then((r) => {
                setUser(r.data);
                localStorage.setItem('current_user', JSON.stringify(r.data));
            })
            .catch(() => {
                localStorage.removeItem('access_token');
                localStorage.removeItem('current_user');
                setToken(null);
                setUser(null);
            })
            .finally(() => setIsLoading(false));
    }, []);

    const login = (newToken: string, newUser: User) => {
        localStorage.setItem('access_token', newToken);
        localStorage.setItem('current_user', JSON.stringify(newUser));
        setToken(newToken);
        setUser(newUser);
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('current_user');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
