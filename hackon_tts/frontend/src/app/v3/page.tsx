"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  Room,
  RoomEvent,
  RemoteParticipant,
  Track,
} from "livekit-client";

const API = process.env.NEXT_PUBLIC_V3_API_URL || "http://localhost:8002";

interface TranscriptEntry {
  speaker: string;
  text: string;
  sentiment: string;
}

interface SessionMeta {
  lead_name: string | null;
  lead_email: string | null;
  meeting_time: string | null;
  overall_sentiment: string;
  sentiment_counts: { Positive: number; Neutral: number; Negative: number };
}

const SENTIMENT_COLOR: Record<string, string> = {
  Positive: "#22c55e",
  Neutral: "#f59e0b",
  Negative: "#ef4444",
};

const SENTIMENT_EMOJI: Record<string, string> = {
  Positive: "😊",
  Neutral: "😐",
  Negative: "😟",
};

export default function V3Page() {
  const [status, setStatus] = useState<"idle" | "connecting" | "connected" | "ended">("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [meta, setMeta] = useState<SessionMeta>({
    lead_name: null,
    lead_email: null,
    meeting_time: null,
    overall_sentiment: "Neutral",
    sentiment_counts: { Positive: 0, Neutral: 0, Negative: 0 },
  });
  const [callDuration, setCallDuration] = useState(0);
  const [ariaActive, setAriaActive] = useState(false);

  const roomRef = useRef<Room | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const startCall = useCallback(async () => {
    setStatus("connecting");
    try {
      // Unique room per call — no room param needed, server generates it
      const res = await fetch(`${API}/api/token`);
      const { token, url } = await res.json();

      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      // Metadata + agent transcript from data channel
      room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
        try {
          const msg = JSON.parse(new TextDecoder().decode(payload));
          if (msg.type === "metadata") {
            setMeta({
              lead_name: msg.lead_name,
              lead_email: msg.lead_email,
              meeting_time: msg.meeting_time,
              overall_sentiment: msg.overall_sentiment,
              sentiment_counts: msg.sentiment_counts,
            });
          } else if (msg.type === "transcript" && msg.speaker && msg.text) {
            setTranscript((prev) => {
              const last = prev[prev.length - 1];
              if (last?.text === msg.text && last?.speaker === msg.speaker) return prev;
              return [...prev, { speaker: msg.speaker, text: msg.text, sentiment: "" }];
            });
            if (msg.speaker === "Aria") { setAriaActive(true); setTimeout(() => setAriaActive(false), 2000); }
          }
        } catch {}
      });

      // Transcript from LiveKit's built-in transcript system
      // participant=undefined means LOCAL user; participant present means remote (agent)
      room.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
        for (const seg of segments) {
          if (seg.final && seg.text?.trim()) {
            const isAgent = !!participant && participant.identity !== room.localParticipant.identity;
            const speaker = isAgent ? "Aria" : "You";
            const sentiment = speaker === "You" ? "Neutral" : "";
            setTranscript((prev) => {
              // Avoid duplicate final segments
              const last = prev[prev.length - 1];
              if (last?.text === seg.text && last?.speaker === speaker) return prev;
              return [...prev, { speaker, text: seg.text, sentiment }];
            });
            if (isAgent) { setAriaActive(true); setTimeout(() => setAriaActive(false), 2000); }
          }
        }
      });

      // Play Aria's audio
      room.on(RoomEvent.TrackSubscribed, (track, _pub, _participant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.autoplay = true;
          document.body.appendChild(el);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => { track.detach(); });

      room.on(RoomEvent.Disconnected, () => {
        setStatus("ended");
        if (timerRef.current) clearInterval(timerRef.current);
      });

      await room.connect(url, token);

      // Publish mic
      await room.localParticipant.setMicrophoneEnabled(true);

      setStatus("connected");
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        setCallDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } catch (err) {
      console.error("Connection failed:", err);
      setStatus("idle");
    }
  }, []);

  const endCall = useCallback(async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    const duration = Math.floor((Date.now() - startTimeRef.current) / 1000);

    if (roomRef.current) {
      await roomRef.current.disconnect();
      roomRef.current = null;
    }

    // Save call record
    try {
      await fetch(`${API}/api/calls/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
          lead_name: meta.lead_name,
          lead_email: meta.lead_email,
          meeting_time: meta.meeting_time,
          duration_seconds: duration,
          overall_sentiment: meta.overall_sentiment,
          summary: `Call with ${meta.lead_name || "unknown lead"}. ${meta.meeting_time ? `Demo booked for ${meta.meeting_time}.` : "No meeting booked."}`,
        }),
      });
    } catch {}

    setStatus("ended");
  }, [transcript, meta]);

  const fmtTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const sentimentTotal = Object.values(meta.sentiment_counts).reduce((a, b) => a + b, 0) || 1;

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: "#0a0a12", minHeight: "100vh", color: "#e2e8f0", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ background: "#12121e", borderBottom: "1px solid #1e1e35", padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 34, height: 34, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 16 }}>K</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, color: "#fff" }}>Aria <span style={{ color: "#6366f1", fontSize: 12, fontWeight: 400 }}>v3 · Hinglish</span></div>
            <div style={{ fontSize: 11, color: "#475569" }}>Karta AI Sales Agent</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {status === "connected" && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", animation: "pulse 1.5s infinite" }} />
              <span style={{ fontSize: 13, color: "#94a3b8", fontFamily: "monospace" }}>{fmtTime(callDuration)}</span>
            </div>
          )}
          <a href="/customers" style={{ background: "#1e1e35", border: "1px solid #2d2d44", color: "#94a3b8", padding: "7px 14px", borderRadius: 8, fontSize: 12, textDecoration: "none" }}>Dashboard →</a>
          <a href="/" style={{ background: "#1e1e35", border: "1px solid #2d2d44", color: "#94a3b8", padding: "7px 14px", borderRadius: 8, fontSize: 12, textDecoration: "none" }}>v1</a>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Main call area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 28, gap: 20 }}>

          {/* Aria avatar + status */}
          <div style={{ background: "#12121e", border: "1px solid #1e1e35", borderRadius: 16, padding: "28px 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <div style={{
              width: 80, height: 80, borderRadius: "50%",
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 32, fontWeight: 700,
              boxShadow: ariaActive ? "0 0 0 6px #6366f133, 0 0 0 12px #6366f111" : "none",
              transition: "box-shadow 0.3s ease",
            }}>A</div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 18, color: "#fff" }}>Aria</div>
              <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                {status === "idle" && "Ready to connect"}
                {status === "connecting" && "Connecting…"}
                {status === "connected" && (ariaActive ? "Speaking…" : "Listening…")}
                {status === "ended" && "Call ended"}
              </div>
            </div>

            <span style={{
              background: (SENTIMENT_COLOR[meta.overall_sentiment] || "#64748b") + "22",
              color: SENTIMENT_COLOR[meta.overall_sentiment] || "#64748b",
              padding: "5px 14px", borderRadius: 20, fontSize: 13, fontWeight: 600,
            }}>
              {SENTIMENT_EMOJI[meta.overall_sentiment]} {meta.overall_sentiment}
            </span>
          </div>

          {/* Transcript */}
          <div style={{ flex: 1, background: "#12121e", border: "1px solid #1e1e35", borderRadius: 16, padding: 20, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
            {transcript.length === 0 ? (
              <div style={{ color: "#334155", fontSize: 14, textAlign: "center", marginTop: 40 }}>
                {status === "idle" ? "Click Start Call to connect with Aria" : "Waiting for conversation…"}
              </div>
            ) : (
              transcript.map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                    background: t.speaker === "Aria" ? "linear-gradient(135deg,#6366f1,#8b5cf6)" : "#1e293b",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 700, color: "#fff",
                  }}>{t.speaker === "Aria" ? "A" : "Y"}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: t.speaker === "Aria" ? "#818cf8" : "#60a5fa", fontWeight: 600, marginBottom: 3 }}>
                      {t.speaker}
                      {t.sentiment && t.speaker !== "Aria" && (
                        <span style={{ color: SENTIMENT_COLOR[t.sentiment], marginLeft: 8, fontSize: 10 }}>
                          {SENTIMENT_EMOJI[t.sentiment]} {t.sentiment}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 14, color: "#cbd5e1", lineHeight: 1.5, background: "#0f0f1a", padding: "10px 14px", borderRadius: 10 }}>
                      {t.text}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>

          {/* Call controls */}
          <div style={{ display: "flex", justifyContent: "center", gap: 16 }}>
            {status === "idle" && (
              <button onClick={startCall} style={{
                background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff",
                border: "none", padding: "14px 40px", borderRadius: 40, fontSize: 16,
                fontWeight: 700, cursor: "pointer",
              }}>
                Start Call
              </button>
            )}
            {status === "connecting" && (
              <button disabled style={{
                background: "#1e1e35", color: "#64748b", border: "1px solid #2d2d44",
                padding: "14px 40px", borderRadius: 40, fontSize: 16, fontWeight: 700,
              }}>Connecting…</button>
            )}
            {status === "connected" && (
              <button onClick={endCall} style={{
                background: "#ef4444", color: "#fff", border: "none",
                padding: "14px 40px", borderRadius: 40, fontSize: 16,
                fontWeight: 700, cursor: "pointer",
              }}>End Call</button>
            )}
            {status === "ended" && (
              <button onClick={() => { setStatus("idle"); setTranscript([]); setCallDuration(0); setMeta({ lead_name: null, lead_email: null, meeting_time: null, overall_sentiment: "Neutral", sentiment_counts: { Positive: 0, Neutral: 0, Negative: 0 } }); }} style={{
                background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff",
                border: "none", padding: "14px 40px", borderRadius: 40, fontSize: 16,
                fontWeight: 700, cursor: "pointer",
              }}>New Call</button>
            )}
          </div>
        </div>

        {/* Lead sidebar */}
        <div style={{ width: 260, background: "#0d0d1a", borderLeft: "1px solid #1e1e35", padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>Lead Info</div>

          {[
            { label: "Name", value: meta.lead_name },
            { label: "Email", value: meta.lead_email },
            { label: "Meeting", value: meta.meeting_time },
          ].map(({ label, value }) => (
            <div key={label} style={{ background: "#12121e", border: "1px solid #1e1e35", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 13, color: value ? "#e2e8f0" : "#334155" }}>{value || "—"}</div>
            </div>
          ))}

          <div style={{ background: "#12121e", border: "1px solid #1e1e35", borderRadius: 10, padding: "12px 14px" }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", marginBottom: 10 }}>Sentiment</div>
            {(["Positive", "Neutral", "Negative"] as const).map((s) => {
              const pct = Math.round((meta.sentiment_counts[s] / sentimentTotal) * 100);
              return (
                <div key={s} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#64748b", marginBottom: 3 }}>
                    <span>{SENTIMENT_EMOJI[s]} {s}</span>
                    <span>{pct}%</span>
                  </div>
                  <div style={{ height: 4, background: "#1e1e35", borderRadius: 2 }}>
                    <div style={{ height: "100%", width: `${pct}%`, background: SENTIMENT_COLOR[s], borderRadius: 2, transition: "width 0.3s" }} />
                  </div>
                </div>
              );
            })}
          </div>

          {status === "connected" && (
            <div style={{ background: "#12121e", border: "1px solid #1e1e35", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Duration</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#6366f1", fontFamily: "monospace" }}>{fmtTime(callDuration)}</div>
            </div>
          )}

          <div style={{ marginTop: "auto", fontSize: 11, color: "#1e293b", textAlign: "center" }}>
            Powered by Karta AI
          </div>
        </div>
      </div>

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
    </div>
  );
}
