import React from "react";
import { NavLink, useNavigate, useLocation, Link } from "react-router-dom";
import {
    LayoutDashboard,
    BookOpen,
    ShoppingCart,
    Archive,
    MessageSquare,
    Settings,
    LogOut,
    ChefHat,
    Tablet,
    Calendar,
} from "lucide-react";
import { useAuth } from "../lib/auth";

const nav = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/recipes", label: "Rezepte", icon: BookOpen },
    { to: "/plan", label: "Wochenplan", icon: Calendar },
    { to: "/shopping", label: "Einkaufsliste", icon: ShoppingCart },
    { to: "/pantry", label: "Vorrat", icon: Archive },
    { to: "/chat", label: "Koch-Chat", icon: MessageSquare },
];

export default function Layout({ children }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const loc = useLocation();

    // Tablet mode is a completely different chromeless layout.
    if (loc.pathname.startsWith("/tablet")) return children;

    return (
        <div className="min-h-screen flex flex-col md:flex-row">
            {/* Desktop sidebar */}
            <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-[color:var(--border)] md:bg-white">
                <div className="flex items-center gap-3 px-6 py-6">
                    <div className="h-10 w-10 rounded-2xl flex items-center justify-center bg-[color:var(--primary)] text-white">
                        <ChefHat className="h-5 w-5" strokeWidth={2.5} />
                    </div>
                    <div>
                        <div className="font-display text-xl font-bold tracking-tight">CookPilot</div>
                        <div className="cp-kicker text-[10px]">Küchen-Assistent</div>
                    </div>
                </div>
                <nav className="flex-1 px-3 space-y-1">
                    {nav.map((n) => {
                        const Icon = n.icon;
                        return (
                            <NavLink
                                key={n.to}
                                to={n.to}
                                end={n.end}
                                data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                                        isActive
                                            ? "bg-[color:var(--surface-2)] text-[color:var(--primary)]"
                                            : "text-[color:var(--text)] hover:bg-[color:var(--surface-2)]"
                                    }`
                                }
                            >
                                <Icon className="h-5 w-5" strokeWidth={2.25} />
                                {n.label}
                            </NavLink>
                        );
                    })}
                    <div className="my-4 h-px bg-[color:var(--border)]" />
                    <Link
                        to="/tablet"
                        data-testid="nav-tablet"
                        className="flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold text-[color:var(--text)] hover:bg-[color:var(--surface-2)]"
                    >
                        <Tablet className="h-5 w-5" strokeWidth={2.25} />
                        Küchen-Tablet
                    </Link>
                    {user?.role === "admin" && (
                        <NavLink
                            to="/admin"
                            data-testid="nav-admin"
                            className={({ isActive }) =>
                                `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                                    isActive
                                        ? "bg-[color:var(--surface-2)] text-[color:var(--primary)]"
                                        : "text-[color:var(--text)] hover:bg-[color:var(--surface-2)]"
                                }`
                            }
                        >
                            <Settings className="h-5 w-5" strokeWidth={2.25} />
                            Admin
                        </NavLink>
                    )}
                </nav>
                <div className="px-6 py-4 border-t border-[color:var(--border)]">
                    <div className="text-sm font-semibold">{user?.name}</div>
                    <div className="text-xs text-[color:var(--muted)] mb-3">{user?.email}</div>
                    <button
                        onClick={() => {
                            logout();
                            navigate("/login");
                        }}
                        data-testid="logout-btn"
                        className="cp-btn-ghost w-full justify-start"
                    >
                        <LogOut className="h-4 w-4" /> Abmelden
                    </button>
                </div>
            </aside>

            {/* Mobile header */}
            <header className="md:hidden flex items-center justify-between bg-white border-b border-[color:var(--border)] px-5 py-4">
                <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-xl flex items-center justify-center bg-[color:var(--primary)] text-white">
                        <ChefHat className="h-4 w-4" strokeWidth={2.5} />
                    </div>
                    <span className="font-display text-lg font-bold">CookPilot</span>
                </div>
                <button
                    onClick={() => {
                        logout();
                        navigate("/login");
                    }}
                    data-testid="logout-btn-mobile"
                    className="cp-btn-ghost"
                >
                    <LogOut className="h-4 w-4" />
                </button>
            </header>

            <main className="flex-1 min-w-0 pb-24 md:pb-0">{children}</main>

            {/* Mobile bottom nav */}
            <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-[color:var(--border)] flex justify-around z-30">
                {nav.map((n) => {
                    const Icon = n.icon;
                    return (
                        <NavLink
                            key={n.to}
                            to={n.to}
                            end={n.end}
                            data-testid={`mobile-nav-${n.label.toLowerCase()}`}
                            className={({ isActive }) =>
                                `flex-1 flex flex-col items-center gap-1 py-3 text-[11px] font-semibold ${
                                    isActive ? "text-[color:var(--primary)]" : "text-[color:var(--muted)]"
                                }`
                            }
                        >
                            <Icon className="h-5 w-5" strokeWidth={2.25} />
                            {n.label}
                        </NavLink>
                    );
                })}
            </nav>
        </div>
    );
}
