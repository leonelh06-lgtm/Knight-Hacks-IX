import React, { useEffect, useState } from "react";
import { activeDirection } from "./tracking.js";

export default function TrackingPreview({ status, connectionState }) {
  const [imageFailed, setImageFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const age = status?.frameAgeMs;
  const fresh = Number.isFinite(age) && age <= status.staleAfterMs;
  const hasFrame =
    connectionState === "connected" &&
    status?.hasFrame &&
    !status.simulated &&
    fresh &&
    !status.error;
  useEffect(() => {
    if (!imageFailed) return;
    const timer = setTimeout(() => {
      setImageFailed(false);
      setRetry((n) => n + 1);
    }, 2000);
    return () => clearTimeout(timer);
  }, [imageFailed]);
  const label =
    connectionState === "connecting"
      ? "Connecting camera"
      : connectionState !== "connected"
        ? "Camera offline"
        : status?.simulated
          ? "Simulated input"
          : status?.error
            ? "Camera unavailable"
            : status?.calibrating
              ? "Calibrating"
              : status?.paused
                ? "Tracking paused"
                : status?.phase !== "Tracking"
                  ? status?.phase || "Waiting for camera"
                  : status?.handDetected && fresh
                    ? "Hand in view"
                    : "Show your hand";
  const direction = activeDirection(status);
  return (
    <section className="tracking-panel" aria-labelledby="tracking-heading">
      <div className="tracking-header">
        <h2 id="tracking-heading">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="6" width="13" height="12" rx="3" />
            <path d="m16 10 5-3v10l-5-3" />
          </svg>
          Your hand, in view
        </h2>
        <span className={`status-pill ${hasFrame ? "online" : ""}`}>
          <i />
          {hasFrame ? "CAMERA" : "PREVIEW"}
        </span>
      </div>
      <div className="camera-view">
        {hasFrame && !imageFailed ? (
          <img
            src={`/tracking/stream.mjpg?retry=${retry}`}
            alt="Live camera with hand tracking landmarks"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="camera-empty">
            <svg viewBox="0 0 52 52" aria-hidden="true">
              <path d="M8 18v-5a5 5 0 0 1 5-5h5m16 0h5a5 5 0 0 1 5 5v5m0 16v5a5 5 0 0 1-5 5h-5m-16 0h-5a5 5 0 0 1-5-5v-5" />
              <path d="M20 34V20m6 16V16m6 18V21m-12 6-5-4" />
            </svg>
            <span>{imageFailed ? "Preview reconnecting" : label}</span>
            <p>
              {status?.calibrating
                ? "Follow the tracker’s calibration prompts."
                : status?.simulated
                  ? "No camera is being used."
                  : "Your tracking preview will appear here."}
            </p>
          </div>
        )}
        <span className="camera-corner tl" />
        <span className="camera-corner tr" />
        <span className="camera-corner bl" />
        <span className="camera-corner br" />
        {hasFrame && !imageFailed && (
          <span className="camera-caption">HAND LANDMARKS</span>
        )}
      </div>
      <div className="tracking-footer">
        <span>
          <i className={`connection-dot ${hasFrame ? "online" : ""}`} />
          {label}
        </span>
        <span>
          {direction
            ? `Moving ${direction === "up" ? "forward" : direction}`
            : "Keep your palm visible"}
        </span>
      </div>
    </section>
  );
}
