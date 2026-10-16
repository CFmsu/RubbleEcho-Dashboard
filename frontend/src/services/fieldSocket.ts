import type { ConnectionStatus } from "../types/mission";
import type { FieldSnapshot } from "../types/field";

export function connectField(
  onSnapshot: (snapshot: FieldSnapshot) => void,
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
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/field`);
    socket.onopen = () => {
      delay = 600;
      onStatus("connected");
    };
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as FieldSnapshot;
        if (payload.type === "field") onSnapshot(payload);
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
