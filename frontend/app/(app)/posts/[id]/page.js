"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "../../../../lib/api";

export default function PostDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState({ person_name: "", person_title: "", text: "" });
  const [busy, setBusy] = useState({});
  const [error, setError] = useState("");

  async function load() {
    const p = await api(`/content/posts/${id}/`);
    setPost(p);
    const c = await api(`/engagement/comments/?post=${id}`);
    setComments(c.results || c);
  }
  useEffect(() => { load(); }, [id]);

  async function saveText() {
    setBusy((b) => ({ ...b, save: true }));
    try { await api(`/content/posts/${id}/`, { method: "PATCH", body: { title: post.title, text: post.text, hashtags: post.hashtags } }); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, save: false }));
  }

  async function approve() {
    setBusy((b) => ({ ...b, approve: true }));
    try { await saveText(); setPost(await api(`/content/posts/${id}/approve/`, { method: "POST" })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, approve: false }));
  }

  async function markPosted() {
    setBusy((b) => ({ ...b, posted: true }));
    try { setPost(await api(`/content/posts/${id}/mark_posted/`, { method: "POST" })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, posted: false }));
  }

  async function saveLikes(val) {
    const likes = Math.max(0, Number(val) || 0);
    setPost({ ...post, likes });
    try { await api(`/content/posts/${id}/`, { method: "PATCH", body: { likes } }); } catch (e) { setError(e.message); }
  }

  async function predict() {
    setBusy((b) => ({ ...b, predict: true })); setError("");
    try { setPost(await api(`/content/posts/${id}/predict/`, { method: "POST" })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, predict: false }));
  }

  async function suggestNext() {
    setBusy((b) => ({ ...b, next: true })); setError("");
    try { setPost(await api(`/content/posts/${id}/suggest-next/`, { method: "POST" })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, next: false }));
  }

  async function generateImage() {
    setBusy((b) => ({ ...b, image: true })); setError("");
    try { setPost(await api(`/content/posts/${id}/generate-image/`, { method: "POST" })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, image: false }));
  }

  async function addComment(e) {
    e.preventDefault();
    if (!newComment.text.trim()) return;
    setBusy((b) => ({ ...b, comment: true }));
    try {
      const c = await api("/engagement/comments/", { method: "POST", body: { post: id, ...newComment } });
      setComments((cs) => [c, ...cs]);
      setNewComment({ person_name: "", person_title: "", text: "" });
      suggestReply(c.id);
    } catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, comment: false }));
  }

  async function suggestReply(commentId) {
    setBusy((b) => ({ ...b, [`reply-${commentId}`]: true }));
    try {
      const updated = await api(`/engagement/comments/${commentId}/suggest-reply/`, { method: "POST" });
      setComments((cs) => cs.map((c) => (c.id === commentId ? updated : c)));
    } catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, [`reply-${commentId}`]: false }));
  }

  if (!post) return <main className="page"><p className="hint">Loading...</p></main>;

  const scoreClass = post.predicted_score >= 7 ? "" : post.predicted_score >= 4 ? "mid" : "low";

  return (
    <main className="page">
      <button className="btn small" onClick={() => router.back()} style={{ marginBottom: 14 }}>&larr; Back</button>
      <div className="grid-2" style={{ alignItems: "start" }}>
        <div>
          <div className="card">
            <div className="row" style={{ marginBottom: 8 }}>
              <span className={`tag ${post.status === "posted" ? "success" : ""}`}>{post.status.replace("_", " ")}</span>
              <span className="tag">{post.type}</span>
            </div>
            {post.images?.length > 0 && <img src={post.images[0].image} alt="" style={{ width: "100%", maxHeight: 320, objectFit: "cover", borderRadius: 10, marginBottom: 10 }} />}
            <label htmlFor="title">Label</label>
            <input id="title" value={post.title} onChange={(e) => setPost({ ...post, title: e.target.value })} />
            <label htmlFor="text">Content</label>
            <textarea id="text" rows={10} value={post.text} onChange={(e) => setPost({ ...post, text: e.target.value })} />
            <label htmlFor="hashtags">Hashtags</label>
            <input id="hashtags" value={post.hashtags} onChange={(e) => setPost({ ...post, hashtags: e.target.value })} />
            <div className="row" style={{ marginTop: 14 }}>
              <button className="btn small" onClick={saveText} disabled={busy.save}>{busy.save ? <span className="spin" /> : "Save"}</button>
              <button className="btn small" onClick={generateImage} disabled={busy.image}>{busy.image ? <span className="spin" /> : post.images?.length ? "Regenerate image" : "Generate image"}</button>
              {post.status !== "approved" && post.status !== "posted" && (
                <button className="btn primary small" onClick={approve} disabled={busy.approve}>{busy.approve ? <span className="spin" /> : "Approve"}</button>
              )}
              {post.status === "approved" && (
                <button className="btn primary small" onClick={markPosted} disabled={busy.posted}>{busy.posted ? <span className="spin" /> : "Mark as posted"}</button>
              )}
            </div>
            {error && <p className="error">{error}</p>}
          </div>

          <h2 className="section-title">Comments ({comments.length})</h2>
          <div className="card">
            <form onSubmit={addComment}>
              <label htmlFor="cname">Who commented</label>
              <input id="cname" value={newComment.person_name} onChange={(e) => setNewComment({ ...newComment, person_name: e.target.value })} />
              <label htmlFor="ctext">What they said</label>
              <textarea id="ctext" rows={3} value={newComment.text} onChange={(e) => setNewComment({ ...newComment, text: e.target.value })} />
              <button className="btn small" style={{ marginTop: 10 }} disabled={busy.comment} type="submit">
                {busy.comment ? <span className="spin" /> : "Add comment"}
              </button>
            </form>
          </div>
          {comments.map((c) => (
            <div className="card" key={c.id}>
              <strong>{c.person_name || "Someone"}</strong>
              <p style={{ whiteSpace: "pre-line" }}>{c.text}</p>
              {c.reply ? (
                <div className="card" style={{ background: "var(--paper)" }}>
                  <p className="hint" style={{ margin: "0 0 4px" }}>Suggested reply</p>
                  <p style={{ margin: 0, whiteSpace: "pre-line" }}>{c.reply}</p>
                </div>
              ) : (
                <button className="btn small" onClick={() => suggestReply(c.id)} disabled={busy[`reply-${c.id}`]}>
                  {busy[`reply-${c.id}`] ? <span className="spin" /> : "Suggest a reply"}
                </button>
              )}
            </div>
          ))}
        </div>

        <div>
          <div className="card">
            <h3 style={{ fontSize: "0.9rem", color: "var(--muted)", fontFamily: "var(--body)" }}>Predicted potential</h3>
            {post.predicted_score ? (
              <>
                <span className={`potential ${scoreClass}`}>Potential {post.predicted_score}/10</span>
                <p className="hint">{post.predicted_reason}</p>
                {post.predicted_tip && <p className="hint"><strong>Tip:</strong> {post.predicted_tip}</p>}
              </>
            ) : <p className="hint" style={{ marginTop: 0 }}>Estimate how likely this is to land.</p>}
            <button className="btn small" onClick={predict} disabled={busy.predict}>{busy.predict ? <span className="spin" /> : post.predicted_score ? "Re-predict" : "Predict potential"}</button>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "0.9rem", color: "var(--muted)", fontFamily: "var(--body)" }}>Engagement</h3>
            <label htmlFor="likes">Likes</label>
            <input id="likes" type="number" min="0" value={post.likes} onChange={(e) => saveLikes(e.target.value)} />
            <p className="hint">{comments.length} comments logged</p>
          </div>

          <div className="card">
            <h3 style={{ fontSize: "0.9rem", color: "var(--muted)", fontFamily: "var(--body)" }}>What to do next</h3>
            {post.next_step_suggestion ? <p>{post.next_step_suggestion}</p> : <p className="hint" style={{ marginTop: 0 }}>Get a suggestion based on this post's actual performance.</p>}
            <button className="btn small" onClick={suggestNext} disabled={busy.next}>{busy.next ? <span className="spin" /> : post.next_step_suggestion ? "Regenerate" : "Get a suggestion"}</button>
          </div>
        </div>
      </div>
    </main>
  );
}
