import React from "react";
import GestureGuide from "./GestureGuide.jsx";
import TrackingPreview from "./TrackingPreview.jsx";
import { useTrackingStatus, activeDirection } from "./tracking.js";

function Crystal({ className = "" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 60 80"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M30 3 50 23 45 58 30 76 12 58 9 23Z"
        fill="url(#crystal-light)"
        stroke="#c6a5ff"
        strokeWidth="1"
      />
      <path
        d="m30 3-8 26 8 47 8-47-8-26ZM9 23l13 6 8-7 8 7 12-6M12 58l18-8 15 8"
        stroke="#e8dcff"
        strokeWidth=".8"
        opacity=".8"
      />
      <defs>
        <linearGradient id="crystal-light" x1="0" x2="1" y2="1">
          <stop stopColor="#c199ff" stopOpacity=".65" />
          <stop offset=".55" stopColor="#683bd3" stopOpacity=".2" />
          <stop offset="1" stopColor="#d3baff" stopOpacity=".55" />
        </linearGradient>
      </defs>
    </svg>
  );
}
function Leaf({ className = "" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M9 37C3 13 27 5 40 8c2 22-11 34-28 31"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="m7 42 26-26M18 32l-2-10m10 2 10-1"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}
export default function App() {
  const { status, connectionState } = useTrackingStatus();
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand">
          <span className="brand-mark">
            <Crystal />
          </span>
          <span>
            KNIGHT HACKS <b className="ix-label">IX</b>
            <span className="brand-divider">/</span>
            <span className="brand-sub">PLAYER COMPANION</span>
          </span>
        </div>
        <span className="header-note">
          <span aria-hidden="true">✧</span> ENTER THE ENCHANTED FOREST
        </span>
      </header>
      <main>
        <section className="welcome">
          <div>
            <p className="eyebrow">
              A NEW WAY TO PLAY. A LITTLE MAGIC TO GUIDE YOU.
            </p>
            <h1>
              Guiding <em>Hands</em>
              <span className="title-spark" aria-hidden="true">
                ✧
              </span>
            </h1>
            <p className="welcome-copy">
              Your hands lead the way. We’ll help you remember how.
            </p>
          </div>
          <div className="welcome-note">
            <div className="crystal-aura">
              <Crystal />
            </div>
            <p>
              Your next move,
              <br />
              <span>at your fingertips.</span>
            </p>
          </div>
        </section>
        <div className="play-layout">
          <section className="game-section" aria-labelledby="game-heading">
            <div className="game-header">
              <div>
                <span className="eyebrow">THE ADVENTURE</span>
                <h2 id="game-heading">Your adventure unfolds here.</h2>
              </div>
              <span className="view-label">
                <i />
                GAME VIEW
              </span>
            </div>
            <div className="game-frame">
              <iframe src="/debug.html" title="Forest Motion live game" />
              <div className="frame-ornament top-left" />
              <div className="frame-ornament bottom-right" />
            </div>
            <div className="game-footer">
              <span className="gentle-tip">
                <span aria-hidden="true">✦</span>
                <span>
                  <strong>Take it one gesture at a time.</strong> Keep your
                  whole hand in the camera’s view.
                </span>
              </span>
              <span className="forest-tag">
                <Leaf /> INTO THE FOREST
              </span>
            </div>
            <div className="rest-note">
              <span className="rest-icon" aria-hidden="true">
                〰
              </span>
              <p>
                <strong>A moment to rest?</strong> Relax your hand to stop
                moving.
              </p>
              <span className="rest-end" aria-hidden="true">
                ✧
              </span>
            </div>
          </section>
          <aside
            className="guide-sidebar"
            aria-label="Hand tracking and movement reminders"
          >
            <TrackingPreview
              status={status}
              connectionState={connectionState}
            />
            <GestureGuide activeDirection={activeDirection(status)} />
          </aside>
        </div>
      </main>
      <footer className="site-footer">
        <span>Made for a more instinctive adventure.</span>
        <span>
          KNIGHT HACKS IX · MADE OF A LITTLE MAGIC{" "}
          <span aria-hidden="true">✧</span>
        </span>
      </footer>
    </div>
  );
}
