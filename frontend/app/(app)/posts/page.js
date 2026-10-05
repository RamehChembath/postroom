"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

export default function PostsPage() {
  const { current } = useWorkspace();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!current) return;
    setLoading(true);
    const data = await api("/content/posts/?status=draft,pending_approval", { workspace: current.id });
    setPosts(data.results || data);
    setLoading(false);
  }
  useEffect(() => { load(); }, [current?.id]);

  async function approve(id) {
    await api(`/content/posts/${id}/approve/`, { method: "POST" });
    load();
  }

  return (
    <main className="page">
      <div className="hero"><h1>Approve posts — {current?.name}</h1><p>Review each draft before it goes to the Posting Room.</p></div>
      {loading && <p className="hint">Loading...</p>}
      {!loading && posts.length === 0 && <p className="hint">Nothing waiting on you. Generate drafts from Strategy &amp; Calendar.</p>}
      {posts.map((p) => (
        <div className="card" key={p.id}>
          <div className="card-row">
            <h3>{p.title || p.text.slice(0, 60)}</h3>
            <span className="tag">{p.type}</span>
          </div>
          {p.image && <img src={p.image} alt="" style={{ width: "100%", maxHeight: 220, objectFit: "cover", borderRadius: 8, margin: "8px 0" }} />}
          <p style={{ whiteSpace: "pre-line" }}>{p.text.slice(0, 280)}{p.text.length > 280 ? "..." : ""}</p>
          <p className="hint" style={{ color: "var(--accent)" }}>{p.hashtags}</p>
          {p.predicted_score && <span className={`potential ${p.predicted_score >= 7 ? "" : p.predicted_score >= 4 ? "mid" : "low"}`}>Potential {p.predicted_score}/10</span>}
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn small" href={`/posts/${p.id}`}>Edit</Link>
            <button className="btn small primary" onClick={() => approve(p.id)}>Approve</button>
          </div>
        </div>
      ))}
    </main>
  );
}
