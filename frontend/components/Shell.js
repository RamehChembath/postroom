"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, logout as apiLogout } from "../lib/api";
import { useWorkspace } from "../lib/workspace";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

function VerifyBanner() {
  const [me, setMe] = useState(null);
  const [sent, setSent] = useState(false);
  useEffect(() => { api("/auth/me/").then(setMe).catch(() => {}); }, []);

  async function resend() {
    await api("/auth/resend-verification/", { method: "POST" });
    setSent(true);
  }

  if (!me || me.email_verified) return null;
  return (
    <div className="verify-banner">
      {sent ? "Verification email sent — check your inbox." : (
        <>Verify your email to secure your account. <button onClick={resend}>Resend email</button></>
      )}
    </div>
  );
}

function UsageBadge() {
  const { currentId } = useWorkspace();
  const [workspaceUsage, setWorkspaceUsage] = useState(null);
  useEffect(() => {
    if (!currentId) return;
    api("/billing/usage/").then((u) => setWorkspaceUsage(u.workspaces.find((w) => w.workspace_id === currentId) || null)).catch(() => {});
  }, [currentId]);
  if (!workspaceUsage) return null;
  if (!workspaceUsage.ai_enabled) {
    return <Link href="/billing" className="usage-badge">AI not available on this plan — upgrade</Link>;
  }
  const pct = Math.min(100, Math.round(workspaceUsage.pct_used));
  return (
    <Link href="/billing" className="usage-badge">
      <span>${workspaceUsage.spend_usd.toFixed(2)} / ${workspaceUsage.budget_usd} AI budget (this avatar)</span>
      <span className="usage-bar"><span className="usage-fill" style={{ width: `${pct}%`, background: pct >= 80 ? "var(--danger)" : "var(--accent)" }} /></span>
    </Link>
  );
}

const NAV = [
  { href: "/strategy", label: "Strategy" },
  { href: "/plan", label: "Strategy & Calendar" },
  { href: "/posts", label: "Approve Posts" },
  { href: "/posting-room", label: "Posting Room" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/goals", label: "Goals" },
  { href: "/billing", label: "Billing" },
];

export default function Shell({ children }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await apiLogout();
    router.push("/login");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="side-brand">
          <span className="side-logo">P</span>
          <span>Postroom</span>
        </div>
        <WorkspaceSwitcher />
        <nav className="side-nav">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={pathname.startsWith(item.href) ? "active" : ""}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="side-foot">
          <UsageBadge />
          <button onClick={logout}>Log out</button>
        </div>
      </aside>
      <div className="content-wrap">
        <VerifyBanner />
        {children}
      </div>
    </div>
  );
}
