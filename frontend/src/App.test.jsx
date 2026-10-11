import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import App from "./App.jsx";
import { activeDirection, useTrackingStatus } from "./tracking.js";
import TrackingPreview from "./TrackingPreview.jsx";
const live = {
  phase: "Tracking",
  status: "Open palm: moving up",
  direction: "up",
  active: true,
  handDetected: true,
  hasFrame: true,
  frameAgeMs: 20,
  staleAfterMs: 350,
  inferenceMs: 15,
  simulated: false,
  paused: false,
  calibrating: false,
  error: "",
};
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe("display-only player guide", () => {
  it("keeps every gesture visible and embeds the existing game without controls", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /The Guiding Hands/ }),
    ).toBeInTheDocument();
    for (const name of ["Forward", "Down", "Left", "Right"])
      expect(screen.getByRole("heading", { name })).toBeVisible();
    expect(screen.getByTitle("Forest Motion live game")).toHaveAttribute(
      "src",
      "/debug.html",
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByText(/remaining fingers extended/i)).toBeVisible();
    expect(screen.getByText(/relax your hand/i)).toBeVisible();
  });
  it("highlights only real fresh active movement", () => {
    expect(activeDirection(live)).toBe("up");
    for (const change of [
      { frameAgeMs: 400 },
      { paused: true },
      { calibrating: true },
      { simulated: true },
      { active: false },
      { handDetected: false },
      { error: "Camera failed" },
      { frameAgeMs: null },
    ])
      expect(activeDirection({ ...live, ...change })).toBe(null);
  });
  it("shows a real annotated preview only when a frame is available", () => {
    const { rerender } = render(
      <TrackingPreview status={live} connectionState="connected" />,
    );
    expect(screen.getByAltText(/live camera/i).getAttribute("src")).toContain(
      "/tracking/stream.mjpg",
    );
    rerender(<TrackingPreview status={null} connectionState="disconnected" />);
    expect(screen.queryByAltText(/live camera/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/camera offline/i)[0]).toBeVisible();
    rerender(
      <TrackingPreview
        status={{ ...live, simulated: true, hasFrame: false }}
        connectionState="connected"
      />,
    );
    expect(screen.getAllByText(/simulated input/i)[0]).toBeVisible();
  });
  it("reconnects and clears old state after a failed read", async () => {
    vi.useFakeTimers();
    let request = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        request++;
        if (request === 2) throw new Error("offline");
        return { ok: true, json: async () => live };
      }),
    );
    function Probe() {
      const { status, connectionState } = useTrackingStatus();
      return (
        <div>
          {connectionState}:{status?.direction || "none"}
        </div>
      );
    }
    const { unmount } = render(<Probe />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("connected:up")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("disconnected:none")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("connected:up")).toBeInTheDocument();
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(request).toBe(3);
  });
});
