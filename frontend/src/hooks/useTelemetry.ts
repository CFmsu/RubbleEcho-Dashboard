import { useEffect, useState } from "react";
import { connectTelemetry } from "../services/websocket";
import type { ConnectionStatus, TelemetrySnapshot } from "../types/mission";

export function useTelemetry() {
  const [snapshot, setSnapshot] = useState<TelemetrySnapshot | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");

  useEffect(() => connectTelemetry(setSnapshot, setConnection), []);

  return { snapshot, connection };
}
