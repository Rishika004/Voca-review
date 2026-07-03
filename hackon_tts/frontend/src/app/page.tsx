"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface Turn {
  speaker: "You" | "Aria";
  text: string;
  sentiment?: string;
}

const SENTIMENT_EMOJI: Record<string, string> = {
  Positive: "😊",
  Neutral: "😐",
  Negative: "😠",
};
const SENTIMENT_COLOR: Record<string, string> = {
  Positive: "#22c55e",
  Neutral: "#f59e0b",
  Negative: "#ef4444",
};

export default function Home() {
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sentiment, setSentiment] = useState("Neutral");
  const [leadName, setLeadName] = useState<string | null>(null);
  const [leadEmail, setLeadEmail] = useState<string | null>(null);
  const [meetingTime, setMeetingTime] = useState<string | null>(null);
  const [callSeconds, setCallSeconds] = useState(0);
  const [callEnded, setCallEnded] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const ws = useRef<WebSocket | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const audioWorkletNode = useRef<AudioWorkletNode | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);
  const audioQueue = useRef<Blob[]>([]);
  const isPlayingAudio = useRef(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const BACKEND = "wss://caller-karta.onrender.com/api/agent/voice";
  const API = "https://caller-karta.onrender.com";

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [turns]);

  // Timer
  useEffect(() => {
    if (connected && !callEnded) {
      timerRef.current = setInterval(() => setCallSeconds((s) => s + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [connected, callEnded]);

  const fmtTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const playNextChunk = useCallback(() => {
    if (audioQueue.current.length === 0) {
      isPlayingAudio.current = false;
      return;
    }
    isPlayingAudio.current = true;
    const blob = audioQueue.current.shift()!;
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); playNextChunk(); };
    audio.play();
  }, []);

  const stopRecording = useCallback(async () => {
    audioWorkletNode.current?.disconnect();
    audioWorkletNode.current = null;
    if (audioContext.current) {
      await audioContext.current.close();
      audioContext.current = null;
    }
    mediaStream.current?.getTracks().forEach((t) => t.stop());
    mediaStream.current = null;
    setRecording(false);
  }, []);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    setCallSeconds(0);
    setCallEnded(false);
    setSummary(null);
    setTurns([]);
    setSentiment("Neutral");
    setLeadName(null);
    setLeadEmail(null);
    setMeetingTime(null);

    ws.current = new WebSocket(BACKEND);

    ws.current.onopen = () => setConnected(true);

    ws.current.onmessage = (event) => {
      if (typeof event.data === "string") {
        const msg = JSON.parse(event.data);

        if (msg.type === "transcript") {
          if (msg.user_text) {
            setTurns((prev) => [...prev, { speaker: "You", text: msg.user_text, sentiment: msg.sentiment }]);
          }
          if (msg.agent_reply) {
            setTurns((prev) => [...prev, { speaker: "Aria", text: msg.agent_reply }]);
          }
          if (msg.overall_sentiment) setSentiment(msg.overall_sentiment);
          if (msg.lead_name) setLeadName(msg.lead_name);
          if (msg.lead_email) setLeadEmail(msg.lead_email);
          if (msg.meeting_time) setMeetingTime(msg.meeting_time);
        }

        if (msg.type === "call_summary") {
          if (msg.lead_name) setLeadName(msg.lead_name);
          if (msg.lead_email) setLeadEmail(msg.lead_email);
          if (msg.meeting_time) setMeetingTime(msg.meeting_time);
          if (msg.overall_sentiment) setSentiment(msg.overall_sentiment);
        }
      } else if (event.data instanceof Blob) {
        audioQueue.current.push(event.data);
        if (!isPlayingAudio.current) playNextChunk();
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      setRecording(false);
    };
    ws.current.onerror = () => {
      setConnected(false);
      setRecording(false);
    };
  }, [playNextChunk]);

  const endCall = useCallback(async () => {
    if (recording) await stopRecording();

    // Ask backend for final summary state
    ws.current?.send(JSON.stringify({ type: "call_ended" }));

    // Small delay to receive call_summary message
    await new Promise((r) => setTimeout(r, 600));

    ws.current?.close();
    setCallEnded(true);

    // Build simple summary from turns
    const userLines = turns.filter((t) => t.speaker === "You").map((t) => t.text);
    const autoSummary = userLines.length
      ? `Lead discussed: "${userLines.slice(0, 3).join(" / ")}". Sentiment: ${sentiment}.`
      : "No user speech captured.";
    setSummary(autoSummary);

    // POST to backend
    setSaving(true);
    try {
      await fetch(`${API}/api/calls/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: turns.map((t) => ({
            speaker: t.speaker,
            text: t.text,
            sentiment: t.sentiment || "Neutral",
          })),
          lead_name: leadName,
          lead_email: leadEmail,
          meeting_time: meetingTime,
          duration_seconds: callSeconds,
          overall_sentiment: sentiment,
          summary: autoSummary,
        }),
      });
    } catch (e) {
      console.error("Failed to save call:", e);
    } finally {
      setSaving(false);
    }
  }, [recording, stopRecording, turns, sentiment, leadName, leadEmail, callSeconds]);

  const toggleRecording = useCallback(async () => {
    if (!connected) return;

    if (recording) {
      await stopRecording();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 48000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      mediaStream.current = stream;
      audioContext.current = new AudioContext();
      await audioContext.current.audioWorklet.addModule("/wav-processor.js");
      audioWorkletNode.current = new AudioWorkletNode(audioContext.current, "wav-processor");
      audioWorkletNode.current.port.onmessage = (e) => {
        if (e.data.type === "audioData" && ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(e.data.data);
        }
      };
      const source = audioContext.current.createMediaStreamSource(stream);
      source.connect(audioWorkletNode.current);
      setRecording(true);
    } catch {
      alert("Could not access microphone.");
    }
  }, [connected, recording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      ws.current?.close();
      audioWorkletNode.current?.disconnect();
      audioContext.current?.close();
      mediaStream.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: "#0f0f14", minHeight: "100vh", color: "#e2e8f0" }}>
      {/* Header */}
      <div style={{ background: "#1a1a2e", borderBottom: "1px solid #2d2d44", padding: "16px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: 36, height: 36, borderRadius: "50%", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>K</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#fff" }}>Aria</div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>AI Sales Agent</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {/* Live sentiment badge */}
          <div style={{ background: SENTIMENT_COLOR[sentiment] + "22", border: `1px solid ${SENTIMENT_COLOR[sentiment]}55`, padding: "6px 14px", borderRadius: 20, fontSize: 13, color: SENTIMENT_COLOR[sentiment], fontWeight: 600 }}>
            {SENTIMENT_EMOJI[sentiment]} {sentiment}
          </div>
          {/* Timer */}
          <div style={{ background: "#1e1e35", border: "1px solid #3d3d5c", padding: "6px 14px", borderRadius: 20, fontSize: 13, fontVariantNumeric: "tabular-nums", color: connected ? "#a5f3fc" : "#64748b" }}>
            {fmtTime(callSeconds)}
          </div>
          <a href="/customers" style={{ background: "#6366f1", color: "#fff", padding: "8px 16px", borderRadius: 8, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            Dashboard
          </a>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 0, height: "calc(100vh - 69px)" }}>
        {/* Main call area */}
        <div style={{ display: "flex", flexDirection: "column", padding: "24px 32px" }}>

          {/* Connection row */}
          <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
            {!connected && !callEnded && (
              <button onClick={connect} style={btn("#6366f1")}>
                Start Call
              </button>
            )}
            {connected && (
              <>
                <button
                  onClick={toggleRecording}
                  style={btn(recording ? "#ef4444" : "#22c55e")}
                >
                  {recording ? "⏸ Mute" : "🎙 Speak"}
                </button>
                <button onClick={endCall} style={btn("#f59e0b")}>
                  End Call
                </button>
              </>
            )}
            {callEnded && (
              <button onClick={connect} style={btn("#6366f1")}>
                New Call
              </button>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto", fontSize: 13 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: connected ? "#22c55e" : callEnded ? "#f59e0b" : "#64748b" }} />
              <span style={{ color: "#94a3b8" }}>{connected ? "Live" : callEnded ? "Ended" : "Idle"}</span>
            </div>
          </div>

          {/* Transcript */}
          <div ref={transcriptRef} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, paddingRight: 8 }}>
            {turns.length === 0 && (
              <div style={{ color: "#475569", textAlign: "center", marginTop: 80, fontSize: 15 }}>
                {connected ? "Speak to start the conversation…" : "Click \"Start Call\" to connect to Aria."}
              </div>
            )}
            {turns.map((turn, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: turn.speaker === "You" ? "flex-end" : "flex-start" }}>
                <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4, paddingLeft: turn.speaker === "Aria" ? 8 : 0, paddingRight: turn.speaker === "You" ? 8 : 0 }}>
                  {turn.speaker}
                  {turn.sentiment && turn.speaker === "You" && (
                    <span style={{ marginLeft: 6, color: SENTIMENT_COLOR[turn.sentiment] }}>
                      {SENTIMENT_EMOJI[turn.sentiment]}
                    </span>
                  )}
                </div>
                <div style={{
                  maxWidth: "72%",
                  background: turn.speaker === "You" ? "#1e3a5f" : "#1e1e35",
                  border: `1px solid ${turn.speaker === "You" ? "#2563eb44" : "#3d3d5c"}`,
                  borderRadius: turn.speaker === "You" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                  padding: "10px 14px",
                  fontSize: 14,
                  lineHeight: 1.5,
                  color: "#e2e8f0",
                }}>
                  {turn.text}
                </div>
              </div>
            ))}
          </div>

          {/* Recording indicator */}
          {recording && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0", color: "#ef4444", fontSize: 13 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", animation: "pulse 1s infinite" }} />
              Listening…
            </div>
          )}

          {/* Post-call summary */}
          {callEnded && summary && (
            <div style={{ background: "#1a2744", border: "1px solid #2563eb44", borderRadius: 12, padding: 16, marginTop: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#93c5fd", marginBottom: 8 }}>Post-Call Summary</div>
              <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>{summary}</div>
              {saving && <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>Saving to dashboard…</div>}
            </div>
          )}
        </div>

        {/* Right sidebar — Lead info */}
        <div style={{ background: "#13131f", borderLeft: "1px solid #2d2d44", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#c4b5fd" }}>Lead Intelligence</div>

          <InfoCard label="Name" value={leadName} placeholder="Listening for name…" />
          <InfoCard label="Email" value={leadEmail} placeholder="Listening for email…" />
          <InfoCard label="Meeting Booked" value={meetingTime} placeholder="Asking for preferred time…" />
          <InfoCard label="Call Duration" value={fmtTime(callSeconds)} />

          {/* Sentiment breakdown */}
          <div>
            <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Sentiment Trend</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {(["Positive", "Neutral", "Negative"] as const).map((s) => {
                const total = turns.filter((t) => t.speaker === "You" && t.sentiment).length;
                const count = turns.filter((t) => t.speaker === "You" && t.sentiment === s).length;
                const pct = total ? Math.round((count / total) * 100) : 0;
                return (
                  <div key={s}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#94a3b8", marginBottom: 3 }}>
                      <span>{SENTIMENT_EMOJI[s]} {s}</span>
                      <span>{pct}%</span>
                    </div>
                    <div style={{ background: "#1e1e35", borderRadius: 4, height: 6 }}>
                      <div style={{ background: SENTIMENT_COLOR[s], borderRadius: 4, height: 6, width: `${pct}%`, transition: "width 0.4s" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Aria persona note */}
          <div style={{ background: "#1e1e35", border: "1px solid #3d3d5c", borderRadius: 10, padding: 14, fontSize: 12, color: "#94a3b8", lineHeight: 1.6 }}>
            <strong style={{ color: "#c4b5fd" }}>Aria</strong> is Karta&apos;s AI sales agent — trained on Karta&apos;s product knowledge, pricing, and enterprise use cases.
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #3d3d5c; border-radius: 2px; }
      `}</style>
    </div>
  );
}

function btn(color: string) {
  return {
    background: color,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties;
}

function InfoCard({ label, value, placeholder }: { label: string; value?: string | null; placeholder?: string }) {
  return (
    <div style={{ background: "#1e1e35", border: "1px solid #3d3d5c", borderRadius: 10, padding: 14 }}>
      <div style={{ fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 14, color: value ? "#e2e8f0" : "#475569", fontStyle: value ? "normal" : "italic" }}>
        {value || placeholder || "—"}
      </div>
    </div>
  );
}
