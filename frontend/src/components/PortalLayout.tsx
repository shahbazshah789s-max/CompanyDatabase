import { Link, NavLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { endSession } from "@/lib/session";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { UserPublic } from "@/lib/types";
import { Activity, Database, FileUp, FolderKanban, LayoutDashboard, LogOut, Search, Settings, ShieldCheck, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

const nav = [
  ["/dashboard", "Dashboard", LayoutDashboard, "dashboard-nav-link"],
  ["/search", "Search", Search, "search-nav-link"],
  ["/files", "Files", FileUp, "files-nav-link"],
  ["/departments", "Departments", FolderKanban, "departments-nav-link"],
  ["/users", "Users", Users, "users-nav-link"],
] as const;

export default function PortalLayout() {
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), staleTime: 60_000 });
  return (
    <div data-testid="portal-shell" className="min-h-svh bg-[#020617] text-slate-200">
      <header data-testid="portal-header" className="sticky top-0 z-30 border-b border-slate-800/90 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1500px] items-center gap-4 px-4 sm:px-6">
          <Link to="/dashboard" data-testid="brand-home-link" className="group flex min-w-fit items-center gap-3">
            <span data-testid="brand-mark" className="grid size-9 place-items-center rounded-xl bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,.22)]"><Database className="size-5" /></span>
            <span data-testid="brand-name" className="hidden text-sm font-bold tracking-tight text-slate-100 sm:block">WINGMAN<span className="text-cyan-400">.</span></span>
          </Link>
          <nav data-testid="primary-navigation" className="ml-2 hidden items-center gap-1 overflow-x-auto md:flex">
            {nav.map(([href, label, Icon, testId]) => (
              <NavLink key={href} to={href} data-testid={testId} className={({ isActive }) => `flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${isActive ? "bg-cyan-400/10 text-cyan-300" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"}`}>
                <Icon className="size-4" /><span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <NavLink to="/settings" data-testid="settings-nav-link" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-cyan-300"><Settings className="size-4" /></NavLink>
            <div data-testid="user-summary" className="hidden border-l border-slate-800 pl-3 text-right sm:block"><p data-testid="user-name" className="text-xs font-semibold text-slate-100">{user?.name ?? "Loading user"}</p><p data-testid="user-role" className="text-[10px] uppercase tracking-wider text-cyan-400">{user?.role ?? "member"}</p></div>
            <Button data-testid="sign-out-button" variant="ghost" size="icon-sm" onClick={() => void endSession()} className="text-slate-400 hover:bg-red-500/10 hover:text-red-300"><LogOut className="size-4" /></Button>
          </div>
        </div>
        <div data-testid="mobile-navigation" className="flex gap-1 overflow-x-auto border-t border-slate-900 px-3 py-2 md:hidden">
          {nav.map(([href, label, Icon, testId]) => <NavLink key={href} to={href} data-testid={`mobile-${testId}`} className={({ isActive }) => `flex min-w-fit items-center gap-1 rounded-md px-3 py-1.5 text-[11px] ${isActive ? "bg-cyan-400/10 text-cyan-300" : "text-slate-400"}`}><Icon className="size-3.5" />{label}</NavLink>)}
        </div>
      </header>
      <main data-testid="portal-main" className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8"><Outlet /></main>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div data-testid={`${title.toLowerCase().replaceAll(" ", "-")}-page-header`} className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><div data-testid={`${title.toLowerCase().replaceAll(" ", "-")}-eyebrow`} className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.22em] text-cyan-400"><Activity className="size-3" />{eyebrow}</div><h1 data-testid={`${title.toLowerCase().replaceAll(" ", "-")}-title`} className="font-heading text-2xl font-bold tracking-tight text-slate-100 sm:text-3xl">{title}</h1><p data-testid={`${title.toLowerCase().replaceAll(" ", "-")}-description`} className="mt-2 max-w-2xl text-sm text-slate-400">{description}</p></div>{action}</div>;
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) { return <section className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-2xl shadow-slate-950/20 ${className}`}>{children}</section>; }