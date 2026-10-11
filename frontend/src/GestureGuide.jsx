import React from "react";

export const GESTURES = [
  {
    id: "up",
    name: "Forward",
    pose: "Open palm",
    detail: "Face your palm toward the camera.",
    arrow: "↑",
    number: "01",
  },
  {
    id: "down",
    name: "Down",
    pose: "Closed fist",
    detail: "Close your fist, wrist pointing down.",
    arrow: "↓",
    number: "02",
  },
  {
    id: "left",
    name: "Left",
    pose: "Index + thumb",
    detail: "Touch index to thumb.",
    arrow: "←",
    number: "03",
  },
  {
    id: "right",
    name: "Right",
    pose: "Pinky + thumb",
    detail: "Touch pinky to thumb.",
    arrow: "→",
    number: "04",
  },
];

export function Hand({ pose = "up", className = "" }) {
  const skin = "#baa6df";
  // Distinct continuous outlines: fingers are ordered thumb, index, middle, ring, pinky.
  const outlines = {
    up: "M44 139 L44 121 Q32 111 24 94 L13 70 Q10 61 16 59 Q23 57 29 68 L39 84 L35 35 Q34 26 40 25 Q47 24 48 33 L53 69 L52 18 Q52 9 59 9 Q66 9 66 18 L69 65 L74 23 Q75 15 82 17 Q89 19 87 28 L84 73 L92 44 Q94 36 100 39 Q106 41 103 50 L97 96 Q95 113 85 124 L84 139 Z",
    down: "M44 139 L44 121 Q30 114 26 99 L22 78 Q21 71 27 69 L29 52 Q30 43 38 44 Q45 44 46 51 L47 45 Q48 37 56 39 Q63 39 64 46 L65 47 Q67 39 74 43 Q81 44 81 52 L82 57 Q88 49 95 54 Q101 58 99 66 L96 98 Q94 115 84 124 L84 139 Z",
    left: "M44 139 L44 120 Q26 112 24 93 L22 73 Q21 60 30 52 Q43 39 49 48 Q54 56 45 62 L35 69 Q39 77 46 72 L55 64 L53 18 Q53 10 60 10 Q67 10 67 19 L70 62 L76 24 Q77 16 84 18 Q90 20 88 29 L86 71 L95 46 Q98 38 104 42 Q110 45 106 53 L98 98 Q95 115 85 124 L84 139 Z",
    right:
      "M44 139 L44 121 Q30 112 29 94 L31 73 L34 32 Q35 24 42 25 Q49 27 48 35 L48 69 L54 17 Q55 9 62 11 Q68 12 67 21 L66 68 L77 25 Q79 17 86 20 Q92 22 89 31 L82 75 Q94 67 97 80 Q99 91 89 96 L77 99 Q70 100 64 91 L59 83 Q55 78 50 81 Q46 85 52 91 L66 107 Q77 112 87 105 Q91 118 84 126 L84 139 Z",
  };
  return (
    <svg
      className={`hand-art ${className}`}
      viewBox="0 0 120 150"
      role="img"
      aria-label={
        GESTURES.find((g) => g.id === pose)?.pose + " gesture illustration"
      }
    >
      <defs>
        <linearGradient id={`skin-${pose}`} x1="0" x2="1" y2="1">
          <stop stopColor="#f7f3ff" />
          <stop offset="1" stopColor={skin} />
        </linearGradient>
      </defs>
      <path
        d={outlines[pose]}
        fill={`url(#skin-${pose})`}
        stroke="#8e78b3"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M44 131 Q64 136 84 131 M48 119 Q63 122 76 118"
        fill="none"
        stroke="#9981bb"
        strokeWidth="1"
        opacity=".65"
      />
      {pose === "up" && (
        <path
          d="M44 92 Q64 82 79 92 M51 107 Q59 97 67 95"
          fill="none"
          stroke="#9981bb"
          strokeWidth="1.3"
        />
      )}
      {pose === "down" && (
        <>
          <path
            d="M29 69 Q41 63 53 69 L75 81 Q82 87 77 92 Q73 97 66 94 L44 83 M46 51 L47 67 M64 47 L64 73 M81 54 L81 81"
            fill="none"
            stroke="#9981bb"
            strokeWidth="1.8"
          />
          <path d="M31 98 Q47 106 62 102" fill="none" stroke="#9981bb" />
        </>
      )}
      {pose === "left" && (
        <>
          <path d="M32 64 Q40 60 46 62" fill="none" stroke="#9981bb" />
          <circle
            cx="40"
            cy="64"
            r="13"
            fill="#b69aff"
            fillOpacity=".15"
            stroke="#bc9aff"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />
          <circle cx="40" cy="64" r="3" fill="#fff" />
        </>
      )}
      {pose === "right" && (
        <>
          <path
            d="M62 91 Q73 85 86 91 M89 81 Q82 84 79 90"
            fill="none"
            stroke="#9981bb"
          />
          <circle
            cx="80"
            cy="91"
            r="13"
            fill="#b69aff"
            fillOpacity=".15"
            stroke="#bc9aff"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />
          <circle cx="80" cy="91" r="3" fill="#fff" />
        </>
      )}
    </svg>
  );
}

export default function GestureGuide({ activeDirection }) {
  return (
    <section className="gesture-guide" aria-labelledby="guide-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">YOUR MOVEMENT GUIDE</span>
          <h2 id="guide-heading">A gesture for every step.</h2>
        </div>
        <span className="tiny-spark" aria-hidden="true">
          ✧
        </span>
      </div>
      <div className="gesture-grid">
        {GESTURES.map((g) => (
          <article
            key={g.id}
            className={`gesture-card ${activeDirection === g.id ? "is-active" : ""}`}
            aria-label={`${g.name}: ${g.pose}${activeDirection === g.id ? ", detected" : ""}`}
          >
            <div className="card-top">
              <span className="card-number">{g.number}</span>
              <span className="direction-arrow" aria-hidden="true">
                {g.arrow}
              </span>
            </div>
            <Hand pose={g.id} />
            <div className="card-copy">
              <h3>{g.name}</h3>
              <p className="pose-name">{g.pose}</p>
              <p className="gesture-detail">{g.detail}</p>
            </div>
          </article>
        ))}
      </div>
      <p className="pinch-note">
        <span aria-hidden="true">✧</span> For both pinches, keep your remaining
        fingers extended.
      </p>
    </section>
  );
}
