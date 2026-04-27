import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./lib/auth";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import AcceptInvite from "./pages/AcceptInvite";
import Dashboard from "./pages/Dashboard";
import Recipes from "./pages/Recipes";
import RecipeForm from "./pages/RecipeForm";
import RecipeDetail from "./pages/RecipeDetail";
import CookingMode from "./pages/CookingMode";
import Shopping from "./pages/Shopping";
import Pantry from "./pages/Pantry";
import Chat from "./pages/Chat";
import Tablet from "./pages/Tablet";
import Admin from "./pages/Admin";
import Scan from "./pages/Scan";
import ReceiptScan from "./pages/ReceiptScan";
import MealPlan from "./pages/MealPlan";
import AmbientBackground from "./components/AmbientBackground";

function Shell({ children }) {
    return (
        <ProtectedRoute>
            <Layout>{children}</Layout>
        </ProtectedRoute>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <AmbientBackground />
                <Toaster position="top-right" richColors />
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/invite/:token" element={<AcceptInvite />} />
                    <Route path="/" element={<Shell><Dashboard /></Shell>} />
                    <Route path="/recipes" element={<Shell><Recipes /></Shell>} />
                    <Route path="/recipes/new" element={<Shell><RecipeForm /></Shell>} />
                    <Route path="/recipes/:id" element={<Shell><RecipeDetail /></Shell>} />
                    <Route path="/recipes/:id/edit" element={<Shell><RecipeForm /></Shell>} />
                    <Route path="/recipes/:id/cook" element={<Shell><CookingMode /></Shell>} />
                    <Route path="/shopping" element={<Shell><Shopping /></Shell>} />
                    <Route path="/scan" element={<Shell><Scan /></Shell>} />
                    <Route path="/receipt-scan" element={<Shell><ReceiptScan /></Shell>} />
                    <Route path="/pantry" element={<Shell><Pantry /></Shell>} />
                    <Route path="/plan" element={<Shell><MealPlan /></Shell>} />
                    <Route path="/chat" element={<Shell><Chat /></Shell>} />
                    <Route path="/tablet" element={<Shell><Tablet /></Shell>} />
                    <Route path="/admin" element={
                        <ProtectedRoute adminOnly>
                            <Layout><Admin /></Layout>
                        </ProtectedRoute>
                    } />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}
