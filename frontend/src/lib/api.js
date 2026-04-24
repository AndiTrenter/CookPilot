import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL || "";
export const API_BASE = `${BASE}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("cp_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err?.response?.status === 401) {
            const onAuthPage =
                window.location.pathname.startsWith("/login") ||
                window.location.pathname.startsWith("/invite/");
            if (!onAuthPage) {
                localStorage.removeItem("cp_token");
                localStorage.removeItem("cp_user");
                window.location.href = "/login";
            }
        }
        return Promise.reject(err);
    },
);
