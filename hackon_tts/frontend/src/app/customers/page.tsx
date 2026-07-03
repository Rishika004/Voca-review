"use client";

import { useState, useEffect } from "react";

interface CallRecord {
  call_id: string;
  timestamp: string;
  lead_name: string;
  lead_email: string;
  duration_seconds: number;
  overall_sentiment: string;
  summary: string;
  resolution_status: string;
  transcript: { speaker: string; text: string; sentiment: string }[];
}

const SENTIMENT_COLOR: Record<string, string> = {
  Positive: "#22c55e",
  Neutral: "#f59e0b",
  Negative: "#ef4444",
};

export default function CustomersPage() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const API = "https://caller-karta.onrender.com";

  const fetchCalls = () => {
    fetch(`${API}/api/calls/history`)
      .then((r) => r.json())
      .then((data) => {
        setCalls(data.calls || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchCalls();
    const interval = setInterval(fetchCalls, 5000);
    return () => clearInterval(interval);
  }, []);

  const fmtDuration = (s: number) =>
    `${Math.floor(s / 60)}m ${s % 60}s`;

  const totalCalls = calls.length;
  const positiveCalls = calls.filter((c) => c.overall_sentiment === "Positive").length;
  const avgDuration = totalCalls
    ? Math.round(calls.reduce((sum, c) => sum + c.duration_seconds, 0) / totalCalls)
    : 0;

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: "#0f0f14", minHeight: "100vh", color: "#e2e8f0" }}>
      {/* Header */}
      <div style={{ background: "#1a1a2e", borderBottom: "1px solid #2d2d44", padding: "16px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: 36, height: 36, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>K</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#fff" }}>Call Dashboard</div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>Live call intelligence</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={fetchCalls} style={{ background: "#1e1e35", border: "1px solid #3d3d5c", color: "#94a3b8", padding: "8px 16px", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>
            ↻ Refresh
          </button>
          <a href="/" style={{ background: "#6366f1", color: "#fff", padding: "8px 16px", borderRadius: 8, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            ← Live Agent
          </a>
        </div>
      </div>

      <div style={{ padding: "24px 32px" }}>
        {/* Summary stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
          {[
            { label: "Total Calls", value: totalCalls, color: "#6366f1" },
            { label: "Positive Sentiment", value: positiveCalls, color: "#22c55e" },
            { label: "Avg Duration", value: fmtDuration(avgDuration), color: "#f59e0b" },
            { label: "Leads Captured", value: calls.filter((c) => c.lead_email !== "—").length, color: "#a78bfa" },
          ].map((stat) => (
            <div key={stat.label} style={{ background: "#1a1a2e", border: "1px solid #2d2d44", borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>{stat.label}</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>{stat.value}</div>
            </div>
          ))}
        </div>

        {/* Call list */}
        {loading ? (
          <div style={{ color: "#64748b", textAlign: "center", padding: 60 }}>Loading calls…</div>
        ) : calls.length === 0 ? (
          <div style={{ background: "#1a1a2e", border: "1px solid #2d2d44", borderRadius: 12, padding: 60, textAlign: "center", color: "#475569" }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>📞</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "#94a3b8", marginBottom: 8 }}>No calls yet</div>
            <div style={{ fontSize: 13 }}>Start a conversation with Aria — calls will appear here automatically.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {calls.map((call) => (
              <div key={call.call_id} style={{ background: "#1a1a2e", border: "1px solid #2d2d44", borderRadius: 12, overflow: "hidden" }}>
                {/* Row */}
                <div
                  onClick={() => setExpanded(expanded === call.call_id ? null : call.call_id)}
                  style={{ display: "grid", gridTemplateColumns: "1fr 1fr 120px 120px 100px 80px", gap: 16, padding: "16px 20px", cursor: "pointer", alignItems: "center" }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: "#e2e8f0" }}>{call.lead_name}</div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{call.call_id}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 13, color: "#94a3b8" }}>{call.lead_email}</div>
                    <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>{call.timestamp}</div>
                  </div>
                  <div style={{ fontSize: 13, color: "#cbd5e1" }}>{fmtDuration(call.duration_seconds)}</div>
                  <div>
                    <span style={{ background: (SENTIMENT_COLOR[call.overall_sentiment] || "#64748b") + "22", color: SENTIMENT_COLOR[call.overall_sentiment] || "#64748b", padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
                      {call.overall_sentiment}
                    </span>
                  </div>
                  <div>
                    <span style={{ background: "#22c55e22", color: "#22c55e", padding: "4px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
                      {call.resolution_status}
                    </span>
                  </div>
                  <div style={{ fontSize: 18, color: "#475569", textAlign: "right" }}>
                    {expanded === call.call_id ? "▲" : "▼"}
                  </div>
                </div>

                {/* Expanded detail */}
                {expanded === call.call_id && (
                  <div style={{ borderTop: "1px solid #2d2d44", padding: "16px 20px", background: "#13131f" }}>
                    {call.summary && (
                      <div style={{ marginBottom: 16, padding: 14, background: "#1a2744", border: "1px solid #2563eb33", borderRadius: 8, fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>
                        <strong style={{ color: "#93c5fd" }}>Summary: </strong>{call.summary}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>Transcript</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 260, overflowY: "auto" }}>
                      {call.transcript.map((t, i) => (
                        <div key={i} style={{ display: "flex", gap: 10, fontSize: 13 }}>
                          <span style={{ color: t.speaker === "You" ? "#60a5fa" : "#a78bfa", fontWeight: 600, minWidth: 36 }}>{t.speaker}:</span>
                          <span style={{ color: "#cbd5e1" }}>{t.text}</span>
                          {t.speaker === "You" && t.sentiment && (
                            <span style={{ color: SENTIMENT_COLOR[t.sentiment], marginLeft: "auto", fontSize: 11 }}>{t.sentiment}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
