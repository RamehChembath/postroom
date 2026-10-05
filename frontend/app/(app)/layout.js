"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "../../lib/api";
import { WorkspaceProvider } from "../../lib/workspace";
import Shell from "../../components/Shell";

export default function AppLayout({ children }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    isLoggedIn().then((ok) => { if (!ok) router.replace("/login"); else setReady(true); });
  }, [router]);

  if (!ready) return null;
  return (
    <WorkspaceProvider>
      <Shell>{children}</Shell>
    </WorkspaceProvider>
  );
}
