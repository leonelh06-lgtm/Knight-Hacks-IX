import { useEffect, useState } from "react";

export function activeDirection(status) {
  if (
    !status ||
    !status.active ||
    !status.handDetected ||
    status.simulated ||
    status.paused ||
    status.calibrating ||
    status.error ||
    !Number.isFinite(status.frameAgeMs) ||
    !Number.isFinite(status.staleAfterMs) ||
    status.frameAgeMs > status.staleAfterMs
  )
    return null;
  return ["up", "down", "left", "right"].includes(status.direction)
    ? status.direction
    : null;
}

export function useTrackingStatus() {
  const [sample, setSample] = useState(null);
  const [connectionState, setConnectionState] = useState("connecting");
  const [now, setNow] = useState(() => performance.now());
  useEffect(() => {
    let disposed = false,
      timer,
      controller;
    let pollDelay = 150;
    const clock = setInterval(() => setNow(performance.now()), 100);
    async function poll() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 1200);
      try {
        const response = await fetch("/tracking/status", {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error("Preview offline");
        const status = await response.json();
        if (!status || typeof status.phase !== "string")
          throw new Error("Invalid preview status");
        pollDelay =
          Number.isFinite(status.staleAfterMs) && status.staleAfterMs > 0
            ? Math.max(25, Math.min(150, status.staleAfterMs / 3))
            : 150;
        if (!disposed) {
          setSample({ status, received: performance.now() });
          setConnectionState("connected");
        }
      } catch {
        if (!disposed) {
          setSample(null);
          setConnectionState("disconnected");
        }
      } finally {
        clearTimeout(timeout);
        if (!disposed) timer = setTimeout(poll, pollDelay);
      }
    }
    poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
      clearInterval(clock);
      controller?.abort();
    };
  }, []);
  const status = sample
    ? {
        ...sample.status,
        frameAgeMs: Number.isFinite(sample.status.frameAgeMs)
          ? sample.status.frameAgeMs + Math.max(0, now - sample.received)
          : null,
      }
    : null;
  return { status, connectionState };
}
