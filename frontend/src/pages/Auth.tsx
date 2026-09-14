import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiPost } from "@/lib/api";
import { beginSession } from "@/lib/session";
import type { ActionResponse, AuthResponse } from "@/lib/types";
import { ArrowRight, Database, KeyRound, LockKeyhole, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Auth() {
  const location = useLocation(); const navigate = useNavigate();
  const mode = location.pathname.slice(1) || "login";
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [token, setToken] = useState(""); const [resetToken, setResetToken] = useState("");
  const mutation = useMutation({ mutationFn: async () => {
    if (mode === "login") return apiPost<AuthResponse>("/auth/login", { email, password });
    if (mode === "signup") return apiPost<ActionResponse>("/auth/signup", { name, email, password });
    if (mode === "forgot-password") return apiPost<{ message: string; reset_token?: string | null }>("/auth/forgot-password", { email });
    if (mode === "reset-password") return apiPost<ActionResponse>("/auth/reset-password", { token, new_password: newPassword });
    return apiPost<ActionResponse>("/auth/login", { email, password });
  }, onSuccess: (result) => {
    if (mode === "login" && "user" in result) { beginSession(); toast.success(result.message); navigate("/dashboard"); return; }
    if (mode === "forgot-password" && "reset_token" in result) { setResetToken(result.reset_token ?? ""); toast.success(result.message); return; }
    toast.success(result.message); navigate(mode === "reset-password" ? "/login" : "/login");
  }, onError: (error: Error & { body?: { detail?: string } }) => toast.error(error.body?.detail ?? error.message ?? "Request failed") });
  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate(); };
  const isLogin = mode === "login"; const isSignup = mode === "signup"; const isForgot = mode === "forgot-password"; const isReset = mode === "reset-password";
  const title = isLogin ? "Welcome back" : isSignup ? "Create your workspace access" : isForgot ? "Recover your account" : "Set a new password";
  return <div data-testid="auth-page" className="grid min-h-svh bg-[#020617] text-slate-200 lg:grid-cols-[1.05fr_.95fr]">
    <div data-testid="auth-visual-panel" className="relative hidden overflow-hidden border-r border-slate-800 lg:block"><div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(6,182,212,.18),transparent_34%),radial-gradient(circle_at_80%_75%,rgba(59,130,246,.13),transparent_34%)]" /><div className="relative flex h-full flex-col justify-between p-12"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-cyan-400 text-slate-950"><Database className="size-5" /></span><span className="font-heading text-sm font-bold tracking-[.2em] text-white">COMPANY DATABASE</span></div><div className="max-w-lg"><div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-300"><ShieldCheck className="size-7" /></div><h1 data-testid="auth-hero-title" className="font-heading text-5xl font-bold leading-[1.05] tracking-tight text-white">Your company data, organized and searchable.</h1><p data-testid="auth-hero-copy" className="mt-6 max-w-md text-base leading-7 text-slate-400">Search millions of rows, protect every department, and keep your team moving with one focused database portal.</p></div><div data-testid="auth-security-note" className="flex items-center gap-3 text-xs text-slate-500"><LockKeyhole className="size-4 text-emerald-400" />Scoped access · Indexed search · Audit-ready storage</div></div></div>
    <div className="flex items-center justify-center p-6 sm:p-10"><div className="w-full max-w-md"><div className="mb-10 flex items-center gap-3 lg:hidden"><span className="grid size-9 place-items-center rounded-lg bg-cyan-400 text-slate-950"><Database className="size-5" /></span><span className="font-bold tracking-[.15em] text-white">COMPANY DATABASE</span></div><div data-testid="auth-form-header" className="mb-8"><p className="mb-3 text-[10px] font-bold uppercase tracking-[.2em] text-cyan-400">Secure workspace</p><h2 data-testid="auth-form-title" className="font-heading text-3xl font-bold text-slate-100">{title}</h2><p data-testid="auth-form-description" className="mt-2 text-sm text-slate-400">{isLogin ? "Sign in to your scoped data workspace." : isSignup ? "Request access from your workspace owner." : isForgot ? "Generate a demo-safe reset code for your account." : "Use the reset code and choose a strong password."}</p></div>
      <form data-testid={`${mode}-form`} onSubmit={submit} className="space-y-4">
        {isSignup && <Field label="Full name" testId="full-name-input" value={name} onChange={setName} placeholder="Jordan Lee" />}
        {!isReset && <Field label="Email address" testId="email-input" value={email} onChange={setEmail} placeholder="you@company.com" type="email" />}
        {isReset && <Field label="Reset code" testId="reset-token-input" value={token} onChange={setToken} placeholder="Paste your reset code" />}
        {(isLogin || isSignup) && <Field label="Password" testId="password-input" value={password} onChange={setPassword} placeholder="At least 8 characters" type="password" />}
        {isReset && <Field label="New password" testId="new-password-input" value={newPassword} onChange={setNewPassword} placeholder="At least 8 characters" type="password" />}
        <Button data-testid={`${mode}-submit-button`} type="submit" disabled={mutation.isPending} className="mt-3 h-11 w-full bg-cyan-400 font-semibold text-slate-950 hover:bg-cyan-300">{mutation.isPending ? "Working…" : isLogin ? "Sign in" : isSignup ? "Request access" : isForgot ? "Generate reset code" : "Reset password"}<ArrowRight className="ml-2 size-4" /></Button>
      </form>
      {resetToken && <div data-testid="generated-reset-token" className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-xs text-amber-200"><p className="font-semibold">Demo reset code</p><code data-testid="reset-token-value" className="mt-2 block break-all font-mono">{resetToken}</code><Link to="/reset-password" className="mt-3 inline-block underline">Continue to reset password</Link></div>}
      <div data-testid="auth-secondary-links" className="mt-6 flex flex-wrap justify-between gap-3 text-xs text-slate-400">{isLogin ? <><Link data-testid="forgot-password-link" to="/forgot-password" className="hover:text-cyan-300">Forgot password?</Link><Link data-testid="signup-link" to="/signup" className="hover:text-cyan-300">Request an account</Link></> : <Link data-testid="back-to-login-link" to="/login" className="hover:text-cyan-300">Back to sign in</Link>}{isForgot && <span data-testid="demo-reset-note" className="text-slate-500">No email service required in demo mode</span>}</div>
    </div></div>
  </div>;
}

function Field({ label, testId, value, onChange, placeholder, type = "text" }: { label: string; testId: string; value: string; onChange: (value: string) => void; placeholder: string; type?: string }) { return <label data-testid={`${testId}-field`} className="block text-sm text-slate-300"><span className="mb-2 block text-xs font-medium text-slate-400">{label}</span><Input data-testid={testId} type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} required className="h-11 border-slate-700 bg-slate-900/80 text-slate-100 placeholder:text-slate-600 focus-visible:border-cyan-400 focus-visible:ring-cyan-400/20" /></label>; }