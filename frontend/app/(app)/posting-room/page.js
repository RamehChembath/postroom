"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

function fmt(iso) {
  if (!iso) return "No date";
  return new Date(iso).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export default function PostingRoomPage() {
  const { current } = useWorkspace();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  async function load() {
    if (!current) return;
    setLoading(true);
    const data = await api("/content/posts/?status=approved", { workspace: current.id });
    const list = (data.results || data).sort((a, b) => (a.scheduled_at || "").localeCompare(b.scheduled_at || ""));
    setPosts(list);
    setLoading(false);
  }
  useEffect(() => { load(); }, [current?.id]);

  async function markPosted(id) {
    await api(`/content/posts/${id}/mark_posted/`, { method: "POST" });
    load();
  }

  async function copyText(p) {
    const final = p.hashtags ? `${p.text}\n\n${p.hashtags}` : p.text;
    try { await navigator.clipboard.writeText(final); setCopiedId(p.id); setTimeout(() => setCopiedId(null), 2000); } catch {}
  }

  const today = new Date().toDateString();

  return (
    <main className="page">
      <div className="hero"><h1>Posting room — {current?.name}</h1><p>Approved posts, queued by date. You'll get an email reminder on the day.</p></div>
      {loading && <p className="hint">Loading...</p>}
      {!loading && posts.length === 0 && <p className="hint">Nothing queued. Approve a draft from "Approve Posts" to send it here.</p>}
      {posts.map((p) => {
        const isToday = p.scheduled_at && new Date(p.scheduled_at).toDateString() === today;
        return (
          <div className="card" key={p.id} style={isToday ? { borderLeft: "3px solid var(--signal)" } : undefined}>
            <div className="card-row">
              <h3>{p.title || p.text.slice(0, 60)}</h3>
              <span className="tag">{fmt(p.scheduled_at)}{isToday ? " — today" : ""}</span>
            </div>
            {p.image && <img src={p.image} alt="" style={{ width: "100%", maxHeight: 200, objectFit: "cover", borderRadius: 8, margin: "8px 0" }} />}
            <p style={{ whiteSpace: "pre-line" }}>{p.text.slice(0, 220)}{p.text.length > 220 ? "..." : ""}</p>
            <div className="row" style={{ marginTop: 10 }}>
              <button className="btn primary small" onClick={() => copyText(p)}>{copiedId === p.id ? "Copied" : "Copy final post"}</button>
              <Link className="btn small" href={`/posts/${p.id}`}>Open</Link>
              <button className="btn small" onClick={() => markPosted(p.id)}>Mark as posted</button>
            </div>
          </div>
        );
      })}
    </main>
  );
}
