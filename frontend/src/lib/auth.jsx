import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        const raw = localStorage.getItem("cp_user");
        return raw ? JSON.parse(raw) : null;
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("cp_token");
        if (!token) {
            setLoading(false);
            return;
        }
        api.get("/auth/me")
            .then((res) => {
                setUser(res.data);
                localStorage.setItem("cp_user", JSON.stringify(res.data));
            })
            .catch(() => {
                localStorage.removeItem("cp_token");
                localStorage.removeItem("cp_user");
                setUser(null);
            })
            .finally(() => setLoading(false));
    }, []);

    const login = async (email, password) => {
        const { data } = await api.post("/auth/login", { email, password });
        localStorage.setItem("cp_token", data.token);
        localStorage.setItem("cp_user", JSON.stringify(data.user));
        setUser(data.user);
        return data.user;
    };

    const logout = () => {
        localStorage.removeItem("cp_token");
        localStorage.removeItem("cp_user");
        setUser(null);
    };

    const refreshMe = async () => {
        const { data } = await api.get("/auth/me");
        setUser(data);
        localStorage.setItem("cp_user", JSON.stringify(data));
        return data;
    };

    return (
        <AuthCtx.Provider value={{ user, loading, login, logout, refreshMe, setUser }}>
            {children}
        </AuthCtx.Provider>
    );
}

export const useAuth = () => useContext(AuthCtx);
