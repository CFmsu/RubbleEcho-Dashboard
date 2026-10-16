import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "../common/Panel";
import { ApiError, postJson } from "../../services/api";
import { connectField } from "../../services/fieldSocket";
import type { FieldSnapshot } from "../../types/field";

const BAUD_RATES = [9600, 19200, 38400, 57600, 115200];

export function RangePanel() {
  const [snapshot, setSnapshot] = useState<FieldSnapshot | null>(null);
  const [port, setPort] = useState("");
  const [baud, setBaud] = useState(115200);
  const [error, setError] = useState("");

  useEffect(() => connectField(setSnapshot, () => undefined), []);

  const hardware = snapshot?.hardware;
  const status = hardware?.link_status ?? "DISCONNECTED";
  const readings = hardware?.distances ?? [];
  const latest = readings.length > 0 ? readings[readings.length - 1] : null;
  const live = status === "CONNECTED" && latest?.distance_cm != null;
  const points = readings.slice(-60).map((reading) => ({
    sequence: reading.sequence,
    cm: reading.distance_cm,
    time: reading.timestamp?.slice(11, 19) ?? "",
  }));

  const connect = async () => {
    setError("");
    try {
      await postJson("/api/hardware/connect", { port, baud });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not open the COM port.");
    }
  };

  const disconnect = async () => {
    setError("");
    try {
      await postJson("/api/hardware/disconnect");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not close the COM port.");
    }
  };

  return (
    <Panel
      title="HC-SR04 distance"
      aside={<span className={status === "CONNECTED" ? "text-green" : "text-red"}>{status}</span>}
      className=""
      fitContent
      bodyClassName="grid gap-3 p-3 lg:grid-cols-[220px_minmax(0,1fr)_240px]"
    >
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold tracking-wide text-orange">REAL HARDWARE</p>
        <p className="num text-4xl font-semibold leading-none">
          {live ? latest?.distance_cm?.toFixed(1) : "—"}
          <span className="ml-1 text-base text-muted">cm</span>
        </p>
        <p className="text-sm text-muted">
          {status === "DISCONNECTED"
            ? "Arduino is disconnected. No new readings are being added."
            : status === "STALE"
              ? "Port is open, but no distance line has arrived. Match the baud rate to the Arduino Serial Monitor."
              : "Live reading from the connected Arduino."}
        </p>
        <p className="text-sm">
          Readings <span className="num">{hardware?.distance_count ?? 0}</span>
        </p>
        <p className="text-xs text-muted">Last {latest ? latest.timestamp : "—"}</p>
        <label className="text-xs font-semibold">
          COM port
          <select className="field mt-1 w-full" value={port} onChange={(event) => setPort(event.target.value)}>
            <option value="">Select the Arduino port</option>
            {(hardware?.ports ?? []).map((item) => (
              <option key={item.device} value={item.device}>
                {item.device} {item.description}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Baud rate
          <select className="field mt-1 w-full" value={baud} onChange={(event) => setBaud(Number(event.target.value))}>
            {BAUD_RATES.map((rate) => (
              <option key={rate} value={rate}>
                {rate}
                {rate === 115200 ? " — this Arduino sketch" : ""}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-2">
          <button type="button" className="cmd primary" disabled={!port} onClick={() => void connect()}>
            Connect
          </button>
          <button type="button" className="cmd" onClick={() => void disconnect()}>
            Disconnect
          </button>
        </div>
        {hardware?.port ? (
          <p className="text-xs text-muted">
            Open {hardware.port} at {hardware.baud} baud
          </p>
        ) : null}
        {error || hardware?.error ? <p className="text-sm text-red">{error || hardware?.error}</p> : null}
        <p className="text-xs text-muted">Close the Arduino Serial Monitor before connecting. It keeps the same COM port.</p>
      </div>
      <div className="h-[180px] min-w-0">
        {points.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#d8dee6" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis
                tick={{ fontSize: 11 }}
                width={40}
                domain={["auto", "auto"]}
                unit=" cm"
                label={{ value: "cm", angle: -90, position: "insideLeft" }}
              />
              <Tooltip formatter={(value) => [`${value} cm`, "Distance"]} />
              <Line type="linear" dataKey="cm" stroke="#e85d04" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center text-sm text-muted">Waiting for a real Distance line from the Arduino.</div>
        )}
      </div>
      <div className="max-h-[180px] overflow-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-muted">
              <th className="py-1 pr-2 font-semibold">#</th>
              <th className="py-1 pr-2 font-semibold">cm</th>
              <th className="py-1 font-semibold">Time</th>
            </tr>
          </thead>
          <tbody>
            {readings
              .slice(-8)
              .reverse()
              .map((reading) => (
                <tr key={reading.event_id} className="border-t border-line">
                  <td className="num py-1 pr-2">{reading.sequence}</td>
                  <td className="num py-1 pr-2">{reading.distance_cm ?? "—"}</td>
                  <td className="py-1">{reading.timestamp?.slice(11, 19)}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-muted">Source REAL_HARDWARE · sensor hc-sr04. Closer objects print a smaller centimeter value.</p>
      </div>
    </Panel>
  );
}
