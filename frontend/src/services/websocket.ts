import type { ConnectionStatus, TelemetrySnapshot } from "../types/mission";

export function connectTelemetry(
  onSnapshot: (snapshot: TelemetrySnapshot) => void,
  onStatus: (status: ConnectionStatus) => void,
): () => void {
  let socket: WebSocket | null = null;
  let stopped = false;
  let delay = 600;
  let timer = 0;

  const connect = () => {
    if (stopped) return;
    onStatus("connecting");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/telemetry`);
    socket.onopen = () => {
      delay = 600;
      onStatus("connected");
    };
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as TelemetrySnapshot;
        if (payload.type === "telemetry") onSnapshot(payload);
      } catch {
        /* ignore malformed frames */
      }
    };
    socket.onclose = () => {
      onStatus("disconnected");
      if (!stopped) {
        timer = window.setTimeout(connect, delay);
        delay = Math.min(delay * 1.6, 5000);
      }
    };
  };

  connect();
  return () => {
    stopped = true;
    window.clearTimeout(timer);
    socket?.close();
  };
}
