"use client";

import { useState, useRef, useEffect } from "react";

export default function Home() {
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const [isRecording, setIsRecording] = useState(false);
  const [userTranscript, setUserTranscript] = useState("");
  const [agentResponse, setAgentResponse] = useState("");

  const ws = useRef<WebSocket | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const audioWorkletNode = useRef<AudioWorkletNode | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);

  const WEBSOCKET_URL = "ws://127.0.0.1:8000/api/agent/voice";

  useEffect(() => {
    // Cleanup WebSocket connection and audio resources on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (audioWorkletNode.current) {
        audioWorkletNode.current.disconnect();
      }
      if (audioContext.current) {
        audioContext.current.close();
      }
      if (mediaStream.current) {
        mediaStream.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const connect = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("Already connected.");
      return;
    }

    setConnectionStatus("Connecting...");
    ws.current = new WebSocket(WEBSOCKET_URL);

    ws.current.onopen = () => {
      setConnectionStatus("Connected");
      console.log("WebSocket connection established.");
    };

    ws.current.onmessage = (event) => {
      if (typeof event.data === "string") {
        const message = JSON.parse(event.data);
        console.log("Received text message:", message);
        if (message.user_text) {
          setUserTranscript((prev) => `${prev}\n\nYou: ${message.user_text}`);
        }
        if (message.agent_reply) {
          setAgentResponse(
            (prev) => `${prev}\n\nAgent: ${message.agent_reply}`
          );
        }
      } else if (event.data instanceof Blob) {
        console.log("Received audio data.");
        const audioBlob = event.data;
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();
      }
    };

    ws.current.onclose = () => {
      setConnectionStatus("Disconnected");
      console.log("WebSocket connection closed.");
      setIsRecording(false);
    };

    ws.current.onerror = (error) => {
      setConnectionStatus("Error");
      console.error("WebSocket error:", error);
      setIsRecording(false);
    };
  };

  const disconnect = () => {
    if (ws.current) {
      ws.current.close();
    }
    // Also stop any ongoing recording
    if (isRecording) {
      toggleRecording();
    }
  };

  const toggleRecording = async () => {
    if (connectionStatus !== "Connected") {
      alert("Please connect to the server first.");
      return;
    }

    if (isRecording) {
      // Stop recording
      if (audioWorkletNode.current) {
        audioWorkletNode.current.disconnect();
        audioWorkletNode.current = null;
      }
      if (audioContext.current) {
        await audioContext.current.close();
        audioContext.current = null;
      }
      if (mediaStream.current) {
        mediaStream.current.getTracks().forEach((track) => track.stop());
        mediaStream.current = null;
      }
      setIsRecording(false);
    } else {
      // Start recording
      try {
        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 48000, // High sample rate, will be downsampled
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        mediaStream.current = stream;

        // Create audio context
        audioContext.current = new AudioContext();

        // Load the WAV processor worklet
        await audioContext.current.audioWorklet.addModule("/wav-processor.js");

        // Create audio worklet node
        audioWorkletNode.current = new AudioWorkletNode(
          audioContext.current,
          "wav-processor"
        );

        // Handle messages from the worklet (WAV data)
        audioWorkletNode.current.port.onmessage = (event) => {
          if (
            event.data.type === "audioData" &&
            ws.current?.readyState === WebSocket.OPEN
          ) {
            console.log(
              `[React] Received audio data: ${event.data.data.byteLength} bytes`
            );

            // Verify the data has RIFF header
            const headerBytes = new Uint8Array(event.data.data, 0, 12);
            const riffMarker = String.fromCharCode(
              headerBytes[0],
              headerBytes[1],
              headerBytes[2],
              headerBytes[3]
            );
            console.log(`[React] RIFF marker in data: "${riffMarker}"`);
            console.log(
              `[React] Header bytes:`,
              Array.from(headerBytes)
                .map((b) => b.toString(16).padStart(2, "0"))
                .join(" ")
            );

            // Send the WAV data as binary
            ws.current.send(event.data.data);
            console.log(`[React] Sent WAV data to server`);
          }
        };

        // Connect audio source to worklet
        const source = audioContext.current.createMediaStreamSource(stream);
        source.connect(audioWorkletNode.current);

        setIsRecording(true);
      } catch (error) {
        console.error("Error accessing microphone:", error);
        alert("Could not access microphone. Please check permissions.");
      }
    }
  };

  return (
    <div
      style={{
        fontFamily: "sans-serif",
        padding: "20px",
        maxWidth: "800px",
        margin: "auto",
      }}
    >
      <h1 style={{ textAlign: "center", color: "#333" }}>AI Voice Agent</h1>

      <div
        style={{
          textAlign: "center",
          marginBottom: "20px",
        }}
      >
        <a
          href="/customers"
          style={{
            display: "inline-block",
            padding: "10px 20px",
            backgroundColor: "#007bff",
            color: "white",
            textDecoration: "none",
            borderRadius: "5px",
            fontWeight: "500",
            fontSize: "14px",
          }}
        >
          📊 View Customer Dashboard
        </a>
      </div>

      <div
        style={{
          border: "1px solid #ccc",
          padding: "15px",
          borderRadius: "8px",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Connection</h2>
        <p>
          Status:{" "}
          <span
            style={{
              fontWeight: "bold",
              color: connectionStatus === "Connected" ? "green" : "red",
            }}
          >
            {connectionStatus}
          </span>
        </p>
        <button
          onClick={connect}
          disabled={
            connectionStatus === "Connected" ||
            connectionStatus === "Connecting..."
          }
        >
          Connect
        </button>
        <button
          onClick={disconnect}
          disabled={connectionStatus !== "Connected"}
        >
          Disconnect
        </button>
      </div>

      <div
        style={{
          border: "1px solid #ccc",
          padding: "15px",
          borderRadius: "8px",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Conversation</h2>
        <button
          onClick={toggleRecording}
          disabled={connectionStatus !== "Connected"}
          style={{
            backgroundColor: isRecording ? "#f44336" : "#4CAF50",
            color: "white",
            padding: "10px 20px",
            border: "none",
            borderRadius: "5px",
            cursor: "pointer",
            fontSize: "16px",
          }}
        >
          {isRecording ? "Stop Listening" : "Start Listening"}
        </button>
        <div
          style={{
            marginTop: "20px",
            background: "#f9f9f9",
            padding: "10px",
            borderRadius: "5px",
            minHeight: "200px",
            whiteSpace: "pre-wrap",
          }}
        >
          <p>
            <strong>Your side:</strong>
            {userTranscript}
          </p>
          <hr />
          <p>
            <strong>Agent's side:</strong>
            {agentResponse}
          </p>
        </div>
      </div>
    </div>
  );
}
