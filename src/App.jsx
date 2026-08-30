import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  Home as HomeIcon,
  Library,
  Compass,
  MessageSquare,
  GraduationCap,
  Settings as SettingsIcon,
  Search,
  ArrowUpRight,
  X,
  Send,
  FileText,
  Upload,
  ZoomIn,
  ZoomOut,
  Check,
} from "lucide-react";
import "./App.css";

/* ------------------------------------------------------------------ */
/* Mock data                                                           */
/* ------------------------------------------------------------------ */

const STATS = { memories: 1284, documents: 47, topics: 62, streak: 14 };

const TOPIC_FILTERS = [
  "All",
  "AI & ML",
  "Operating Systems",
  "Databases",
  "Distributed Systems",
  "Mathematics",
];

const DOCUMENTS = [
  { id: 1, title: "Operating Systems Notes", type: "PDF", pages: 212, topics: ["Operating Systems"], uploaded: "Aug 14", lastAccessed: "2 days ago", concepts: 38 },
  { id: 2, title: "OS Lecture 07 — Scheduling", type: "PDF", pages: 24, topics: ["Operating Systems"], uploaded: "Aug 20", lastAccessed: "Today", concepts: 12 },
  { id: 3, title: "RAG Systems — Deep Dive", type: "MD", pages: 18, topics: ["AI & ML"], uploaded: "Aug 22", lastAccessed: "Yesterday", concepts: 21 },
  { id: 4, title: "Database Normalization", type: "TXT", pages: 9, topics: ["Databases"], uploaded: "Jul 30", lastAccessed: "5 days ago", concepts: 14 },
  { id: 5, title: "Vector Databases Explained", type: "PDF", pages: 31, topics: ["AI & ML", "Databases"], uploaded: "Aug 10", lastAccessed: "3 days ago", concepts: 19 },
  { id: 6, title: "IPC & Threads", type: "PDF", pages: 16, topics: ["Operating Systems"], uploaded: "Aug 5", lastAccessed: "1 week ago", concepts: 10 },
  { id: 7, title: "Consensus & Paxos", type: "PDF", pages: 27, topics: ["Distributed Systems"], uploaded: "Jul 22", lastAccessed: "2 weeks ago", concepts: 16 },
  { id: 8, title: "Linear Algebra for ML", type: "PDF", pages: 44, topics: ["Mathematics", "AI & ML"], uploaded: "Jun 30", lastAccessed: "3 weeks ago", concepts: 25 },
];

const NODES = [
  { id: "ai", label: "AI", x: 70, y: 60, group: "ml" },
  { id: "rag", label: "RAG", x: 165, y: 32, group: "ml" },
  { id: "emb", label: "Embeddings", x: 258, y: 70, group: "ml" },
  { id: "vdb", label: "Vector DB", x: 340, y: 40, group: "ml" },
  { id: "os", label: "Operating Systems", x: 80, y: 175, group: "os" },
  { id: "proc", label: "Processes", x: 178, y: 205, group: "os" },
  { id: "thr", label: "Threads", x: 268, y: 182, group: "os" },
  { id: "ipc", label: "IPC", x: 350, y: 210, group: "os" },
  { id: "db", label: "Database", x: 100, y: 280, group: "db" },
  { id: "sql", label: "SQL", x: 200, y: 300, group: "db" },
  { id: "norm", label: "Normalization", x: 300, y: 278, group: "db" },
];

const EDGES = [
  ["ai", "rag"], ["rag", "emb"], ["emb", "vdb"],
  ["os", "proc"], ["proc", "thr"], ["thr", "ipc"],
  ["db", "sql"], ["sql", "norm"],
  ["emb", "vdb"], ["ai", "db"],
];

const NODE_DETAIL = {
  ai: { related: ["RAG", "Embeddings", "Fine-tuning"], sources: ["RAG Systems — Deep Dive · p.2", "Linear Algebra for ML · p.14"] },
  rag: { related: ["AI", "Embeddings", "Vector DB"], sources: ["RAG Systems — Deep Dive · p.6", "Vector Databases Explained · p.11"] },
  emb: { related: ["RAG", "Vector DB", "Linear Algebra"], sources: ["Vector Databases Explained · p.4"] },
  vdb: { related: ["Embeddings", "RAG"], sources: ["Vector Databases Explained · p.9"] },
  os: { related: ["Processes", "Threads", "IPC"], sources: ["Operating Systems Notes · p.3"] },
  proc: { related: ["Threads", "Scheduling"], sources: ["OS Lecture 07 · p.12"] },
  thr: { related: ["Processes", "IPC"], sources: ["IPC & Threads · p.2"] },
  ipc: { related: ["Threads", "Processes"], sources: ["IPC & Threads · p.15"] },
  db: { related: ["SQL", "Normalization"], sources: ["Database Normalization · p.1"] },
  sql: { related: ["Database", "Normalization"], sources: ["Database Normalization · p.5"] },
  norm: { related: ["SQL", "Transactions"], sources: ["Database Normalization · p.8"] },
};

const CHAT_SEED = [
  { role: "user", text: "How does RAG reduce hallucination compared to a plain LLM?" },
  {
    role: "assistant",
    text: "By grounding generation in retrieved passages rather than relying only on parametric memory, RAG lets the model cite specific evidence instead of guessing. The retrieval step narrows the answer space to what your own documents actually say, which is why the citations below trace directly back to your notes.",
    sources: [
      { doc: "RAG Systems — Deep Dive", page: 6 },
      { doc: "Vector Databases Explained", page: 11 },
    ],
  },
];

const STUDY_TOPICS = [
  { name: "Database", pct: 82, strong: ["SQL", "Normalization"], review: ["Transactions", "Indexing"] },
  { name: "Operating Systems", pct: 61, strong: ["Processes", "Threads"], review: ["Deadlocks", "Scheduling"] },
  { name: "AI & Machine Learning", pct: 45, strong: ["Embeddings"], review: ["RAG", "Fine-tuning"] },
  { name: "Distributed Systems", pct: 28, strong: [], review: ["Consensus", "Paxos", "CAP Theorem"] },
];

const NAV_ITEMS = [
  { id: "home", label: "HOME", icon: HomeIcon },
  { id: "knowledge", label: "KNOWLEDGE", icon: Library },
  { id: "explore", label: "EXPLORE", icon: Compass },
  { id: "chat", label: "CHAT", icon: MessageSquare },
  { id: "study", label: "STUDY", icon: GraduationCap },
  { id: "settings", label: "SETTINGS", icon: SettingsIcon },
];

/* ------------------------------------------------------------------ */
/* Small shared pieces                                                 */
/* ------------------------------------------------------------------ */

function Divider() {
  return <div style={{ height: 1, background: "var(--border-soft)" }} />;
}

function Eyebrow({ children }) {
  return (
    <div className="pkos-mono" style={{ fontSize: 10.5, color: "var(--text-faint)", textTransform: "uppercase" }}>
      {children}
    </div>
  );
}

function StatBlock({ value, label }) {
  return (
    <div style={{ minWidth: 92 }}>
      <div className="pkos-display" style={{ fontSize: 27, color: "var(--text)", lineHeight: 1 }}>
        {value}
      </div>
      <div className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 6, textTransform: "uppercase" }}>
        {label}
      </div>
    </div>
  );
}

function TopicChip({ label, active, onClick }) {
  return (
    <div className={"pkos-chip" + (active ? " active" : "")} onClick={onClick}>
      {label.toUpperCase()}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Constellation map (KnowledgeMap / graph)                            */
/* ------------------------------------------------------------------ */

function ConstellationMap({ nodes, edges, selected, onSelect, height = 340, zoom = 1 }) {
  const [hover, setHover] = useState(null);
  const pos = useMemo(() => {
    const m = {};
    nodes.forEach((n) => (m[n.id] = n));
    return m;
  }, [nodes]);

  return (
    <svg
      viewBox="0 0 420 340"
      width="100%"
      height={height}
      style={{ display: "block", overflow: "visible", maxWidth: "100%" }}
    >
      <g transform={`translate(210 170) scale(${zoom}) translate(-210 -170)`}>
        {edges.map(([a, b], i) => {
          const p1 = pos[a], p2 = pos[b];
          if (!p1 || !p2) return null;
          const isLit = selected && (selected === a || selected === b);
          return (
            <line
              key={i}
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={isLit ? "var(--accent)" : "var(--border)"}
              strokeWidth={isLit ? 1.2 : 0.75}
              opacity={isLit ? 0.9 : 0.55}
              className="pkos-draw"
              style={{ animationDelay: `${i * 70}ms` }}
            />
          );
        })}
        {nodes.map((n) => {
          const isSel = selected === n.id;
          const isHov = hover === n.id;
          return (
            <g
              key={n.id}
              onClick={() => onSelect(n.id)}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
            >
              {(isSel || isHov) && (
                <circle cx={n.x} cy={n.y} r={13} fill="var(--accent)" opacity={0.12} />
              )}
              <circle
                cx={n.x} cy={n.y}
                r={isSel ? 4.6 : 3.4}
                fill={isSel ? "var(--accent)" : "var(--text-dim)"}
                className={"pkos-node " + (isSel ? "pkos-pulse" : "")}
              />
              <text x={n.x + 9} y={n.y + 3.5} className="pkos-node-label" fill={isSel ? "var(--text)" : "var(--text-dim)"}>
                {n.label}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

function MemoryPanel({ nodeId, onClose }) {
  if (!nodeId) return null;
  const node = NODES.find((n) => n.id === nodeId);
  const detail = NODE_DETAIL[nodeId];
  if (!node || !detail) return null;
  return (
    <div className="pkos-fade-in pkos-side-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Eyebrow>Node</Eyebrow>
        <X size={14} color="var(--text-faint)" style={{ cursor: "pointer" }} onClick={onClose} />
      </div>
      <div className="pkos-display" style={{ fontSize: 20, marginTop: 6 }}>{node.label}</div>

      <div style={{ marginTop: 18 }}>
        <Eyebrow>Related concepts</Eyebrow>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {detail.related.map((r) => (
            <div key={r} className="pkos-chip">{r}</div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <Eyebrow>Source documents</Eyebrow>
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
          {detail.sources.map((s) => (
            <div key={s} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, color: "var(--text-dim)" }}>
              <FileText size={12} color="var(--text-faint)" />
              {s}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Views                                                                */
/* ------------------------------------------------------------------ */

function HomeView({ selected, setSelected }) {
  return (
    <div className="pkos-fade-in pkos-view">
      <Eyebrow>Personal Knowledge OS</Eyebrow>
      <h1 className="pkos-display pkos-hero-title">
        Everything you've learned,<br />connected.
      </h1>

      <div style={{ display: "flex", gap: 40, marginTop: 30, flexWrap: "wrap" }}>
        <StatBlock value={STATS.memories.toLocaleString()} label="Memories" />
        <StatBlock value={STATS.documents} label="Documents" />
        <StatBlock value={STATS.topics} label="Topics mapped" />
        <StatBlock value={`${STATS.streak}d`} label="Active streak" />
      </div>

      <div style={{ marginTop: 34, display: "flex", alignItems: "center", gap: 12, maxWidth: 560 }}>
        <Search size={16} color="var(--text-faint)" />
        <input className="pkos-input" placeholder="Search everything you know…" style={{ flex: 1, padding: "8px 0", fontSize: 15 }} />
      </div>

      <div style={{ display: "flex", gap: 40, marginTop: 40, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 420px", minWidth: 280 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <Eyebrow>Knowledge map</Eyebrow>
            <span className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)" }}>CLICK A NODE</span>
          </div>
          <div style={{ marginTop: 8, border: "1px solid var(--border-soft)", background: "var(--bg-panel)" }}>
            <ConstellationMap nodes={NODES} edges={EDGES} selected={selected} onSelect={setSelected} />
          </div>
        </div>

        {selected ? (
          <MemoryPanel nodeId={selected} onClose={() => setSelected(null)} />
        ) : (
          <div style={{ minWidth: 210, paddingTop: 4 }}>
            <Eyebrow>Recently added</Eyebrow>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 12 }}>
              {DOCUMENTS.slice(0, 4).map((d) => (
                <div key={d.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ color: "var(--text)" }}>{d.title}</span>
                  <span className="pkos-mono" style={{ color: "var(--text-faint)", fontSize: 10.5, whiteSpace: "nowrap", marginLeft: 12 }}>{d.uploaded}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 22 }}>
              <Eyebrow>Currently studying</Eyebrow>
              <div style={{ marginTop: 10, fontSize: 13, color: "var(--text-dim)" }}>
                Distributed Systems — Consensus &amp; Paxos
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentCard({ doc, onOpen }) {
  return (
    <div className="pkos-card" style={{ padding: "16px 18px", cursor: "pointer" }} onClick={() => onOpen(doc)}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="pkos-mono" style={{ fontSize: 10, color: "var(--accent)", border: "1px solid var(--accent-soft)", padding: "2px 6px" }}>
          {doc.type}
        </div>
        <span className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)" }}>{doc.concepts} CONCEPTS</span>
      </div>
      <div className="pkos-display" style={{ fontSize: 17, marginTop: 12 }}>{doc.title}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
        {doc.topics.map((t) => (
          <span key={t} className="pkos-mono" style={{ fontSize: 9.5, color: "var(--text-faint)" }}>#{t.replace(/\s/g, "")}</span>
        ))}
      </div>
      <Divider />
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 11.5, color: "var(--text-faint)" }}>
        <span>{doc.pages} pages</span>
        <span>Opened {doc.lastAccessed}</span>
      </div>
    </div>
  );
}

function DocumentDetail({ doc, onClose }) {
  return (
    <div className="pkos-fade-in pkos-view pkos-overlay">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <Eyebrow>{doc.type} · {doc.pages} pages · uploaded {doc.uploaded}</Eyebrow>
          <h2 className="pkos-display" style={{ fontSize: 30, marginTop: 8 }}>{doc.title}</h2>
        </div>
        <div className="pkos-btn-ghost" onClick={onClose} style={{ cursor: "pointer" }}>CLOSE</div>
      </div>

      <div style={{ display: "flex", gap: 48, marginTop: 30, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 420px", minWidth: 280 }}>
          <Eyebrow>AI summary</Eyebrow>
          <p style={{ fontSize: 14.5, lineHeight: 1.7, color: "var(--text-dim)", marginTop: 10, maxWidth: 620 }}>
            This document covers the core mechanics of {doc.topics[0].toLowerCase()}, walking through foundational
            definitions before building toward applied examples. {doc.concepts} distinct concepts were extracted and
            linked into your knowledge graph.
          </p>

          <div style={{ marginTop: 26 }}>
            <Eyebrow>Important concepts</Eyebrow>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
              {["Core definitions", "Trade-offs", "Failure modes", "Worked example"].map((c) => (
                <div key={c} className="pkos-chip">{c}</div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ minWidth: 220 }}>
          <Eyebrow>Related documents</Eyebrow>
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
            {DOCUMENTS.filter((d) => d.id !== doc.id && d.topics.some((t) => doc.topics.includes(t))).slice(0, 3).map((d) => (
              <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "var(--text-dim)" }}>
                <ArrowUpRight size={12} color="var(--accent)" />
                {d.title}
              </div>
            ))}
          </div>

          <div style={{ marginTop: 26 }}>
            <Eyebrow>Ask about this document</Eyebrow>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
              <input className="pkos-input" placeholder="e.g. explain page 4…" style={{ flex: 1, padding: "6px 0", fontSize: 13 }} />
              <Send size={15} color="var(--accent)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function UploadPanel({ onClose }) {
  const STEPS = ["UPLOADING", "READING", "UNDERSTANDING", "INDEXING", "CONNECTED"];
  const [step, setStep] = useState(-1);
  const [done, setDone] = useState(false);

  const start = () => {
    setStep(0);
    setDone(false);
  };

  useEffect(() => {
    if (step < 0 || step >= STEPS.length - 1) {
      if (step === STEPS.length - 1) setDone(true);
      return;
    }
    const t = setTimeout(() => setStep((s) => s + 1), 650);
    return () => clearTimeout(t);
  }, [step]);

  return (
    <div className="pkos-fade-in pkos-modal-backdrop">
      <div className="pkos-modal">
        <X size={14} color="var(--text-faint)" style={{ position: "absolute", top: 16, right: 16, cursor: "pointer" }} onClick={onClose} />
        <Eyebrow>Add to your knowledge</Eyebrow>
        <div onClick={start} className="pkos-dropzone">
          <Upload size={20} color="var(--accent)" style={{ margin: "0 auto" }} />
          <div style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 12 }}>
            Drop a PDF, TXT, or Markdown file — or click to simulate
          </div>
        </div>

        {step >= 0 && (
          <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 8 }}>
            {STEPS.map((s, i) => (
              <div key={s} className="pkos-mono" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 8, color: i <= step ? "var(--text)" : "var(--text-faint)" }}>
                {i < step || (i === step && done) ? (
                  <Check size={12} color="var(--accent)" />
                ) : i === step ? (
                  <span className="pkos-cursor" style={{ color: "var(--accent)" }}>›</span>
                ) : (
                  <span style={{ opacity: 0.3 }}>·</span>
                )}
                {s}
              </div>
            ))}
          </div>
        )}

        {done && (
          <div className="pkos-fade-in" style={{ marginTop: 20 }}>
            <Eyebrow>Extracted topics</Eyebrow>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
              {["Consensus", "Leader Election", "Failure Detection"].map((t) => (
                <div key={t} className="pkos-chip">{t}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function KnowledgeView() {
  const [filter, setFilter] = useState("All");
  const [q, setQ] = useState("");
  const [openDoc, setOpenDoc] = useState(null);
  const [uploading, setUploading] = useState(false);

  const filtered = DOCUMENTS.filter((d) => {
    const matchesTopic = filter === "All" || d.topics.includes(filter);
    const matchesQ = d.title.toLowerCase().includes(q.toLowerCase());
    return matchesTopic && matchesQ;
  });

  return (
    <div className="pkos-fade-in pkos-view" style={{ position: "relative", minHeight: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <Eyebrow>Library</Eyebrow>
          <h2 className="pkos-display" style={{ fontSize: 30, marginTop: 6 }}>Knowledge</h2>
        </div>
        <div className="pkos-btn" style={{ cursor: "pointer" }} onClick={() => setUploading(true)}>ADD TO YOUR KNOWLEDGE</div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 26, maxWidth: 420 }}>
        <Search size={14} color="var(--text-faint)" />
        <input className="pkos-input" placeholder="Search your library…" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, padding: "6px 0", fontSize: 13.5 }} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
        {TOPIC_FILTERS.map((t) => (
          <TopicChip key={t} label={t} active={filter === t} onClick={() => setFilter(t)} />
        ))}
      </div>

      <div className="pkos-scrim pkos-doc-grid">
        {filtered.map((d) => (
          <DocumentCard key={d.id} doc={d} onOpen={setOpenDoc} />
        ))}
        {filtered.length === 0 && (
          <div style={{ color: "var(--text-faint)", fontSize: 13 }}>Nothing matches — try another topic or term.</div>
        )}
      </div>

      {openDoc && <DocumentDetail doc={openDoc} onClose={() => setOpenDoc(null)} />}
      {uploading && <UploadPanel onClose={() => setUploading(false)} />}
    </div>
  );
}

function ExploreView() {
  const [selected, setSelected] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [q, setQ] = useState("");

  const filteredId = useMemo(() => {
    if (!q) return null;
    const hit = NODES.find((n) => n.label.toLowerCase().includes(q.toLowerCase()));
    return hit ? hit.id : null;
  }, [q]);

  return (
    <div className="pkos-fade-in pkos-view" style={{ display: "flex", gap: 40, flexWrap: "wrap" }}>
      <div style={{ flex: "1 1 460px", minWidth: 280 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <Eyebrow>Graph</Eyebrow>
            <h2 className="pkos-display" style={{ fontSize: 30, marginTop: 6 }}>Explore</h2>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <Search size={13} color="var(--text-faint)" />
            <input className="pkos-input" placeholder="Find a concept…" value={q} onChange={(e) => setQ(e.target.value)} style={{ fontSize: 13, padding: "4px 0", width: 150 }} />
            <ZoomOut size={15} color="var(--text-dim)" style={{ cursor: "pointer" }} onClick={() => setZoom((z) => Math.max(0.7, z - 0.15))} />
            <ZoomIn size={15} color="var(--text-dim)" style={{ cursor: "pointer" }} onClick={() => setZoom((z) => Math.min(1.6, z + 0.15))} />
          </div>
        </div>
        <div style={{ marginTop: 18, border: "1px solid var(--border-soft)", background: "var(--bg-panel)" }}>
          <ConstellationMap nodes={NODES} edges={EDGES} selected={selected || filteredId} onSelect={setSelected} height={400} zoom={zoom} />
        </div>
      </div>

      <MemoryPanel nodeId={selected || filteredId} onClose={() => setSelected(null)} />
    </div>
  );
}

function Citation({ source, onClick }) {
  return (
    <div onClick={onClick} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
      <FileText size={11} color="var(--accent)" />
      <span style={{ color: "var(--text-dim)" }}>{source.doc}</span>
      <span className="pkos-mono" style={{ color: "var(--text-faint)", fontSize: 10.5 }}>· p.{source.page}</span>
    </div>
  );
}

function SourcePanel({ source, onClose }) {
  if (!source) return null;
  return (
    <div className="pkos-fade-in pkos-side-panel">
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <Eyebrow>Source</Eyebrow>
        <X size={14} color="var(--text-faint)" style={{ cursor: "pointer" }} onClick={onClose} />
      </div>
      <div className="pkos-display" style={{ fontSize: 17, marginTop: 8 }}>{source.doc}</div>
      <div className="pkos-mono" style={{ fontSize: 10.5, color: "var(--text-faint)", marginTop: 4 }}>PAGE {source.page}</div>
      <p style={{ fontSize: 12.5, color: "var(--text-dim)", lineHeight: 1.6, marginTop: 14 }}>
        Excerpt preview would render here, pulled directly from the retrieved passage and highlighted against your query.
      </p>
    </div>
  );
}

function ChatView() {
  const [messages, setMessages] = useState(CHAT_SEED);
  const [input, setInput] = useState("");
  const [activeSource, setActiveSource] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const send = () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    const reply = {
      role: "assistant",
      text: "Based on what's indexed so far, here's a grounded answer drawn from your notes rather than general knowledge.",
      sources: [{ doc: "Operating Systems Notes", page: 3 }],
    };
    setMessages((m) => [...m, userMsg, reply]);
    setInput("");
  };

  return (
    <div className="pkos-fade-in pkos-view" style={{ display: "flex", gap: 40, flexWrap: "wrap" }}>
      <div style={{ flex: "1 1 460px", minWidth: 280, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <Eyebrow>Research terminal</Eyebrow>
        <h2 className="pkos-display" style={{ fontSize: 26, marginTop: 6 }}>Chat</h2>

        <div className="pkos-scrim pkos-chat-log">
          {messages.map((m, i) => (
            <div key={i}>
              <div className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 6 }}>
                {m.role === "user" ? "> YOU" : "> ASSISTANT"}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.65, color: m.role === "user" ? "var(--text)" : "var(--text-dim)" }}>
                {m.text}
              </div>
              {m.sources && (
                <div style={{ marginTop: 12, borderTop: "1px solid var(--border-soft)", paddingTop: 10 }}>
                  <div className="pkos-mono" style={{ fontSize: 9.5, color: "var(--text-faint)", marginBottom: 8 }}>SOURCES</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                    {m.sources.map((s, j) => (
                      <Citation key={j} source={s} onClick={() => setActiveSource(s)} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 18, borderTop: "1px solid var(--border-soft)", paddingTop: 14 }}>
          <span className="pkos-mono" style={{ color: "var(--accent)" }}>›</span>
          <input
            className="pkos-input"
            style={{ flex: 1, padding: "4px 0", fontSize: 13.5, borderBottom: "none" }}
            placeholder="Ask your knowledge base…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <Send size={15} color="var(--accent)" style={{ cursor: "pointer" }} onClick={send} />
        </div>
      </div>

      {activeSource && <SourcePanel source={activeSource} onClose={() => setActiveSource(null)} />}
    </div>
  );
}

function StudyTopicCard({ topic }) {
  return (
    <div className="pkos-card" style={{ padding: "18px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div className="pkos-display" style={{ fontSize: 17 }}>{topic.name.toUpperCase()}</div>
        <span className="pkos-mono" style={{ fontSize: 11, color: "var(--accent)" }}>{topic.pct}% explored</span>
      </div>
      <div style={{ height: 3, background: "var(--border-soft)", marginTop: 12 }}>
        <div style={{ height: "100%", width: `${topic.pct}%`, background: "var(--accent)" }} />
      </div>

      <div style={{ display: "flex", gap: 28, marginTop: 16, flexWrap: "wrap" }}>
        <div>
          <div className="pkos-mono" style={{ fontSize: 9.5, color: "var(--text-faint)" }}>STRONG</div>
          <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
            {topic.strong.length ? topic.strong.map((s) => (
              <span key={s} style={{ fontSize: 12.5, color: "var(--text-dim)" }}>{s}</span>
            )) : <span style={{ fontSize: 12, color: "var(--text-faint)" }}>—</span>}
          </div>
        </div>
        <div>
          <div className="pkos-mono" style={{ fontSize: 9.5, color: "var(--text-faint)" }}>NEEDS REVIEW</div>
          <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
            {topic.review.map((s) => (
              <span key={s} style={{ fontSize: 12.5, color: "var(--text)" }}>{s}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StudyView() {
  return (
    <div className="pkos-fade-in pkos-scrim pkos-view" style={{ overflowY: "auto", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <Eyebrow>Progress</Eyebrow>
          <h2 className="pkos-display" style={{ fontSize: 30, marginTop: 6 }}>Study</h2>
        </div>
        <div className="pkos-btn" style={{ cursor: "pointer" }}>START QUIZ</div>
      </div>

      <div className="pkos-study-grid">
        {STUDY_TOPICS.map((t) => (
          <StudyTopicCard key={t.name} topic={t} />
        ))}
      </div>
    </div>
  );
}

function SettingsRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 0", borderBottom: "1px solid var(--border-soft)", gap: 16, flexWrap: "wrap" }}>
      <span style={{ fontSize: 13.5, color: "var(--text)" }}>{label}</span>
      <span className="pkos-mono" style={{ fontSize: 11.5, color: "var(--text-faint)" }}>{value}</span>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="pkos-fade-in pkos-view" style={{ maxWidth: 520 }}>
      <Eyebrow>Preferences</Eyebrow>
      <h2 className="pkos-display" style={{ fontSize: 30, marginTop: 6 }}>Settings</h2>

      <div style={{ marginTop: 26 }}>
        <div className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 4 }}>ACCOUNT</div>
        <SettingsRow label="Display name" value="Explorer" />
        <SettingsRow label="Storage used" value="1.2 GB / 5 GB" />
      </div>

      <div style={{ marginTop: 26 }}>
        <div className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 4 }}>SYSTEM</div>
        <SettingsRow label="Retrieval depth" value="Balanced" />
        <SettingsRow label="Auto-connect new topics" value="Enabled" />
        <SettingsRow label="Accent" value="Brass" />
      </div>

      <div style={{ marginTop: 26 }}>
        <div className="pkos-mono" style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 4 }}>DATA</div>
        <SettingsRow label="Export knowledge graph" value="JSON / GraphML" />
        <SettingsRow label="Delete all memories" value="—" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shell                                                                */
/* ------------------------------------------------------------------ */

function Sidebar({ active, setActive }) {
  return (
    <div className="pkos-sidebar">
      <div>
        <div className="pkos-logo">
          <div className="pkos-logo-dot" />
          <span className="pkos-mono" style={{ fontSize: 11, letterSpacing: "0.08em", color: "var(--text)" }}>PK / OS</span>
        </div>
        <div className="pkos-nav-list">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.id} className={"pkos-nav-item" + (active === item.id ? " active" : "")} onClick={() => setActive(item.id)}>
                <Icon size={14} />
                <span className="pkos-mono pkos-nav-label" style={{ fontSize: 11 }}>{item.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="pkos-mono pkos-status">
        <div>NODES: {STATS.memories}</div>
        <div>LINKED: 98.2%</div>
        <div style={{ color: "var(--accent)" }}>● SYSTEM ONLINE</div>
      </div>
    </div>
  );
}

export default function App() {
  const [active, setActive] = useState("home");
  const [selectedNode, setSelectedNode] = useState(null);

  const view = {
    home: <HomeView selected={selectedNode} setSelected={setSelectedNode} />,
    knowledge: <KnowledgeView />,
    explore: <ExploreView />,
    chat: <ChatView />,
    study: <StudyView />,
    settings: <SettingsView />,
  }[active];

  return (
    <div className="pkos">
      <div className="pkos-shell">
        <Sidebar active={active} setActive={setActive} />
        <div className="pkos-scrim pkos-main">
          {view}
        </div>
      </div>
    </div>
  );
}