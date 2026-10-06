"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../lib/api";

const NAV = [
  { href: "/platform", label: "Dashboard", icon: "▦" },
  { href: "/platform/tenants", label: "Tenants", icon: "🏢" },
  { href: "/platform/costs", label: "Costs & Billing", icon: "💳" },
  { href: "/platform/settings", label: "Settings", icon: "⚙" },
];

export default function PlatformLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState(null);
  const [status, setStatus] = useState("checking"); // checking | ok | denied

  useEffect(() => {
    api("/auth/me/").then((u) => {
      setMe(u);
      if (!u.is_staff) { setStatus("denied"); router.replace("/dashboard"); }
      else setStatus("ok");
    }).catch(() => { setStatus("denied"); router.replace("/login"); });
  }, [router]);

  if (status !== "ok") {
    return (
      <main className="page">
        <p className="hint">{status === "checking" ? "Loading..." : "Staff access only — redirecting..."}</p>
      </main>
    );
  }

  return (
    <div className="pf-shell">
      <aside className="pf-sidebar">
        <div className="pf-brand">
          <span className="pf-logo">P</span>
          <div><div className="pf-brand-name">Postroom</div><div className="pf-brand-sub">PLATFORM</div></div>
        </div>
        <nav className="pf-nav">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={pathname === item.href ? "active" : ""}>
              <span className="pf-nav-icon">{item.icon}</span>{item.label}
            </Link>
          ))}
        </nav>
        <div className="pf-foot">
          <div className="pf-foot-role">Admin <span className="pf-badge">PLATFORM</span></div>
          <div className="pf-foot-email">{me?.email}</div>
          <Link href="/dashboard" className="pf-foot-exit">← Back to app</Link>
        </div>
      </aside>
      <div className="pf-content">{children}</div>
    </div>
  );
}
