import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { UserPublic } from "@/lib/types";
import PortalLayout from "@/components/PortalLayout";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Search from "@/pages/Search";
import Files from "@/pages/Files";
import Departments from "@/pages/Departments";
import Users from "@/pages/Users";
import Settings from "@/pages/SettingsV2";
import { Toaster } from "@/components/ui/sonner";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <><Toaster richColors /><Routes><Route path="/login" element={<Auth />} /><Route path="/signup" element={<Auth />} /><Route path="/forgot-password" element={<Auth />} /><Route path="/reset-password" element={<Auth />} /><Route element={<ProtectedLayout />}><Route element={<PortalLayout />}><Route path="/" element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/search" element={<Search />} /><Route path="/files" element={<Files />} /><Route path="/departments" element={<Departments />} /><Route path="/users" element={<Users />} /><Route path="/settings" element={<Settings />} /></Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes></>
  );
}

function ProtectedLayout() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), retry: false, staleTime: 60_000 });
  if (isLoading) return <div data-testid="auth-session-loading" className="grid min-h-svh place-items-center bg-[#020617] text-sm text-slate-400">Checking workspace session…</div>;
  if (isError || !data) return <Navigate to="/login" replace />;
  return <Outlet />;
}
