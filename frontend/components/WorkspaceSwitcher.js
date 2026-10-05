"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useWorkspace } from "../lib/workspace";

const PERSONA_LABEL = { individual: "Myself", company: "Company page" };

export default function WorkspaceSwitcher() {
  const { workspaces, current, currentId, switchWorkspace, loading } = useWorkspace();
  const [open, setOpen] = useState(false);
  const router = useRouter();

  if (loading) return <div className="ws-switcher"><div className="ws-current skeleton">Loading...</div></div>;
  if (!current) return null;

  function pick(id) {
    switchWorkspace(id);
    setOpen(false);
    router.push("/strategy");
  }

  return (
    <div className="ws-switcher">
      <button className="ws-current" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="ws-avatar">{current.name.slice(0, 1).toUpperCase()}</span>
        <span className="ws-info">
          <span className="ws-name">{current.name}</span>
          <span className="ws-persona">{PERSONA_LABEL[current.persona_type]}</span>
        </span>
        <svg viewBox="0 0 24 24" width="16" height="16"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div className="ws-menu">
          {workspaces.map((w) => (
            <button key={w.id} className={`ws-item ${w.id === currentId ? "on" : ""}`} onClick={() => pick(w.id)}>
              <span className="ws-avatar small">{w.name.slice(0, 1).toUpperCase()}</span>
              <span>
                <span className="ws-name">{w.name}</span>
                <span className="ws-persona">{PERSONA_LABEL[w.persona_type]}</span>
              </span>
            </button>
          ))}
          <button className="ws-item ws-add" onClick={() => { setOpen(false); router.push("/workspaces/new"); }}>
            <span className="ws-avatar small plus">+</span>
            <span>Add an avatar</span>
          </button>
        </div>
      )}
    </div>
  );
}
