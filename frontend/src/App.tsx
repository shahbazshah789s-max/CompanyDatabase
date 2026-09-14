import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
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
import Approvals from "@/pages/Approvals";
import { Toaster } from "@/components/ui/sonner";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <><Toaster richColors /><Routes><Route path="/login" element={<Auth />} /><Route path="/signup" element={<Auth />} /><Route path="/forgot-password" element={<Auth />} /><Route path="/reset-password" element={<Auth />} /><Route element={<ProtectedLayout />}><Route element={<PortalLayout />}><Route path="/" element={<RoleHome />} /><Route path="/dashboard" element={<RoleGate roles={["owner", "pro_admin", "user"]}><Dashboard /></RoleGate>} /><Route path="/search" element={<RoleGate roles={["owner", "pro_admin", "user"]}><Search /></RoleGate>} /><Route path="/files" element={<RoleGate roles={["owner", "pro_admin"]}><Files /></RoleGate>} /><Route path="/departments" element={<RoleGate roles={["owner", "pro_admin"]}><Departments /></RoleGate>} /><Route path="/users" element={<RoleGate roles={["owner", "pro_admin"]}><Users /></RoleGate>} /><Route path="/approvals" element={<RoleGate roles={["owner", "pro_admin", "admin"]}><Approvals /></RoleGate>} /><Route path="/settings" element={<Settings />} /></Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes></>
  );
}

function RoleHome() {
  const { data } = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), staleTime: 60_000 });
  return <Navigate to={data?.role === "admin" ? "/approvals" : "/dashboard"} replace />;
}

function RoleGate({ roles, children }: { roles: UserPublic["role"][]; children: ReactNode }) {
  const { data } = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), staleTime: 60_000 });
  if (!data || !roles.includes(data.role)) return <Navigate to={data?.role === "admin" ? "/approvals" : "/dashboard"} replace />;
  return children;
}

function ProtectedLayout() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), retry: false, staleTime: 60_000 });
  if (isLoading) return <div data-testid="auth-session-loading" className="grid min-h-svh place-items-center bg-[#020617] text-sm text-slate-400">Checking workspace session…</div>;
  if (isError || !data) return <Navigate to="/login" replace />;
  return <Outlet />;
}
