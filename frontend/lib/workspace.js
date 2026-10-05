"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const WorkspaceContext = createContext(null);
const LS_KEY = "postroom_current_workspace";

export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/brand/workspaces/");
    const list = data.results || data;
    setWorkspaces(list);
    const saved = typeof window !== "undefined" ? localStorage.getItem(LS_KEY) : null;
    const savedValid = list.find((w) => String(w.id) === saved);
    const fallback = list.find((w) => w.is_default) || list[0];
    setCurrentId(savedValid ? savedValid.id : fallback ? fallback.id : null);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  function switchWorkspace(id) {
    setCurrentId(id);
    localStorage.setItem(LS_KEY, String(id));
  }

  async function createWorkspace(name, personaType) {
    const ws = await api("/brand/workspaces/", { method: "POST", body: { name, persona_type: personaType } });
    await load();
    switchWorkspace(ws.id);
    return ws;
  }

  async function removeWorkspace(id) {
    await api(`/brand/workspaces/${id}/`, { method: "DELETE" });
    await load();
  }

  const current = workspaces.find((w) => w.id === currentId) || null;

  return (
    <WorkspaceContext.Provider value={{ workspaces, current, currentId, loading, switchWorkspace, createWorkspace, removeWorkspace, reload: load }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}
