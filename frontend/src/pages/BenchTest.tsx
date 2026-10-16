import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "../components/common/Panel";
import { ApiError, postJson } from "../services/api";
import { connectField } from "../services/fieldSocket";
import type { BenchSample, FieldSnapshot } from "../types/field";

const BAUD_RATES = [9600, 19200, 38400, 57600, 115200];

const INVENTORY = [
  { name: "Flex sensor", count: "×1", pin: "A0", note: "Divider junction. ADC counts." },
  { name: "Photocell / LDR", count: "×2", pin: "A1, A2", note: "A1 cavity light. A2 room-light reference. ADC counts until a lux calibration exists." },
  { name: "Thermistor", count: "×1", pin: "A3", note: "Contact warmth trend. ADC counts, not degrees." },
  { name: "PIR motion", count: "×2", pin: "D2, D3", note: "Separate left and right exposed-motion channels. Confirm module supply and pin labels." },
  { name: "Compass", count: "×1", pin: "A4 SDA, A5 SCL", note: "HMC6352 at address 0x21 is an assumption. Magnetic heading context only after the chip is verified." },
  { name: "MaxBotix LV-MaxSonar-EZ1 MB1010", count: "×1", pin: "D8 PW", note: "Coarse clearance. Pin 2 pulse width to D8. Pin 6 is 5V. Pin 7 is GND. Pins 1, 3, 4, and 5 stay open." },
];

const TRACES: Array<{
  key: keyof Pick<
    BenchSample,
    "flex_raw" | "light_pocket_raw" | "light_reference_raw" | "thermistor_raw" | "pir_left" | "pir_right" | "heading_deg" | "range_cm"
  >;
  label: string;
  unit: string;
  color: string;
}> = [
  { key: "flex_raw", label: "Flex A0", unit: "ADC", color: "#1f4b7a" },
  { key: "light_pocket_raw", label: "Cavity LDR A1", unit: "ADC", color: "#0e7490" },
  { key: "light_reference_raw", label: "Room LDR A2", unit: "ADC", color: "#64748b" },
  { key: "thermistor_raw", label: "Thermistor A3", unit: "ADC", color: "#e85d04" },
  { key: "pir_left", label: "PIR left D2", unit: "bit", color: "#1b7a4a" },
  { key: "pir_right", label: "PIR right D3", unit: "bit", color: "#65a30d" },
  { key: "heading_deg", label: "Heading", unit: "deg", color: "#6d28d9" },
  { key: "range_cm", label: "Sonar clearance", unit: "cm", color: "#c2410c" },
];

const STEPS = [
  "Share ground between the Uno and every module. Each analog divider is 5V, then the sensor, then the analog junction, then its own 10 kΩ resistor to GND.",
  "PIR outputs go to D2 (left) and D3 (right). Confirm each module’s supply voltage and pin labels before enabling them. The shipped sketch keeps USE_PIR false, so those fields stay null.",
  "Compass SDA and SCL go to A4 and A5. Treat HMC6352 as unverified until the breakout marking matches. USE_HMC6352 stays false, so heading_deg stays null.",
  "MB1010 pin 2 (PW) goes to D8. Pin 6 goes to 5V. Pin 7 goes to GND. Leave pins 1, 3, 4, and 5 open. Do not add a servo or PWM on D9 or D10; Timer1 captures the pulse.",
  "Upload firmware/uno-multisensor/Rubble_Echo_MB1010.ino at 115200 baud. That upload replaces the sketch that prints distance sentences, so the Live run HC-SR04 card will stop receiving those sentences until that sketch is restored.",
  "Close the Arduino Serial Monitor, choose the Uno port, and connect. One JSON frame is expected about every 100 ms.",
  "Bend the flex sensor and watch A0. Cover the cavity LDR and compare A1 with the room reference on A2. Touch the thermistor and watch A3 move as a count, not a temperature.",
  "For the sonar, move a board in front of the MB1010. A shorter range_cm is a nearer surface. stale_or_invalid and far_limit_or_no_echo are not distances. The sketch converts a fresh pulse with microseconds / 147 × 2.54.",
  "Disconnect or unplug the board. The status becomes DISCONNECTED and the charts stop adding points. Null channels stay blank rather than becoming zero.",
];

export function BenchTest() {
  const [snapshot, setSnapshot] = useState<FieldSnapshot | null>(null);
  const [port, setPort] = useState("");
  const [baud, setBaud] = useState(115200);
  const [error, setError] = useState("");

  useEffect(() => connectField(setSnapshot, () => undefined), []);

  const hardware = snapshot?.hardware;
  const samples = hardware?.bench ?? [];
  const status = hardware?.bench_status ?? "DISCONNECTED";
  const latest = samples.length > 0 ? samples[samples.length - 1] : null;
  const windowed = samples.slice(-120);
  const origin = windowed.find((sample) => sample.device_ms != null)?.device_ms ?? 0;
  const points = windowed.map((sample) => ({
    t: sample.device_ms == null ? sample.sequence : Number(((sample.device_ms - origin) / 1000).toFixed(2)),
    flex_raw: sample.flex_raw,
    light_pocket_raw: sample.light_pocket_raw,
    light_reference_raw: sample.light_reference_raw,
    thermistor_raw: sample.thermistor_raw,
    pir_left: sample.pir_left,
    pir_right: sample.pir_right,
    heading_deg: sample.heading_deg,
    range_cm: sample.range_cm,
  }));
  const tMax = points.length > 0 ? points[points.length - 1].t : 1;

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
    <div className="mx-auto grid max-w-6xl gap-3 p-4">
      <Panel
        title="Multi-sensor Bench Test"
        fitContent
        aside={<span className={status === "CONNECTED" ? "text-green" : status === "WAITING" ? "text-muted" : "text-red"}>{status}</span>}
        bodyClassName="grid gap-3 p-3 lg:grid-cols-[minmax(0,1fr)_280px]"
      >
        <div>
          <p className="text-xs font-semibold tracking-wide text-orange">REAL HARDWARE</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            Live frames from the Uno bench sketch only. Sensor lab stimuli and the Live run mission cards stay labeled synthetic. This page does not draw demonstration traces.
          </p>
          <p className="mt-2 text-sm leading-6">{statusCopy(status)}</p>
          <p className="mt-2 text-sm">
            Bench frames <span className="num">{hardware?.bench_count ?? 0}</span>
            <span className="text-muted"> · HC-SR04 sentences on the Live run card </span>
            <span className="num">{hardware?.distance_count ?? 0}</span>
          </p>
          <p className="mt-1 text-xs text-muted">Last bench frame {latest ? latest.timestamp : "—"}</p>
        </div>
        <div className="flex flex-col gap-2">
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
                  {rate === 115200 ? " — bench sketch" : ""}
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
              Open {hardware.port} at {hardware.baud} baud · serial {hardware.state}
            </p>
          ) : null}
          {error || hardware?.error ? <p className="text-sm text-red">{error || hardware?.error}</p> : null}
          <p className="text-xs text-muted">Close the Arduino Serial Monitor before connecting. One program can own the COM port.</p>
        </div>
      </Panel>

      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Confirmed inventory" fitContent aside="8 units" bodyClassName="p-3">
          <ul className="grid gap-2">
            {INVENTORY.map((item) => (
              <li key={item.name} className="border-b border-line pb-2 last:border-0">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-semibold">{item.name}</span>
                  <span className="num text-sm text-muted">
                    {item.count} · {item.pin}
                  </span>
                </div>
                <p className="text-sm leading-5 text-muted">{item.note}</p>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Electrical diagram" fitContent aside="Uno R3" bodyClassName="p-3">
          <img src="/bench/electrical-diagram.png" alt="Wiring diagram: analog dividers on A0 through A3, PIR outputs on D2 and D3, compass on A4 and A5, MB1010 pulse width on D8." className="w-full border border-line bg-white" />
          <p className="mt-2 text-xs leading-5 text-muted">
            Shared ground. USB serial at 115200 baud. MB1010 range conversion: pulse microseconds / 147 × 2.54 = centimeters.
          </p>
        </Panel>
      </div>

      <Panel title="Physical test procedure" fitContent bodyClassName="p-3">
        <ol className="grid list-decimal gap-2 pl-5 text-sm leading-6">
          {STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </Panel>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_280px]">
        <Panel title="Synchronized sensor charts" fitContent aside="Same time axis" bodyClassName="grid gap-1 p-3">
          {points.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted">No live bench frames yet. Charts stay empty until the Uno sends a multi-sensor JSON line.</p>
          ) : (
            TRACES.map((trace) => (
              <div key={trace.key} className="grid grid-cols-[148px_minmax(0,1fr)_72px] items-center gap-2">
                <div>
                  <p className="text-xs font-semibold">{trace.label}</p>
                  <p className="text-[11px] text-muted">{trace.unit}</p>
                </div>
                <div className="h-14 min-w-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke="#d8dee6" vertical={false} />
                      <XAxis dataKey="t" type="number" domain={[0, Math.max(tMax, 0.1)]} hide />
                      <YAxis hide domain={["auto", "auto"]} />
                      <Tooltip formatter={(value) => [value == null ? "null" : `${value} ${trace.unit}`, trace.label]} />
                      <Line type="linear" dataKey={trace.key} stroke={trace.color} strokeWidth={1.5} dot={false} connectNulls={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="num text-right text-sm">{formatChannel(latest, trace.key)}</p>
              </div>
            ))
          )}
          <p className="pt-1 text-xs text-muted">
            ADC rows are raw counts. Null PIR, heading, and range samples are gaps, not zeros. Time is seconds from the first frame in this window.
          </p>
        </Panel>
        <HeadingRange sample={latest} />
      </div>
    </div>
  );
}

function HeadingRange({ sample }: { sample: BenchSample | null }) {
  const heading = sample?.heading_deg;
  const range = sample?.range_cm;
  const hasHeading = typeof heading === "number";
  const hasRange = typeof range === "number";
  return (
    <Panel title="Heading and range" fitContent aside="Context only" bodyClassName="grid gap-3 p-3">
      <div className="grid grid-cols-[120px_minmax(0,1fr)] items-center gap-3">
        <svg viewBox="0 0 120 120" className="h-[120px] w-[120px]" role="img" aria-label={hasHeading ? `Magnetic heading ${heading} degrees` : "Compass not reporting"}>
          <circle cx="60" cy="60" r="52" fill="none" stroke="#d8dee6" strokeWidth="2" />
          <text x="60" y="16" textAnchor="middle" fontSize="10" fill="#5c6b7a">
            N
          </text>
          {hasHeading ? (
            <line x1="60" y1="60" x2="60" y2="18" stroke="#6d28d9" strokeWidth="3" transform={`rotate(${heading} 60 60)`} />
          ) : null}
          <circle cx="60" cy="60" r="3" fill="#121820" />
        </svg>
        <div>
          <p className="text-xs font-semibold tracking-wide text-muted">Magnetic heading</p>
          <p className="num text-3xl font-semibold">{hasHeading ? heading.toFixed(1) : "—"}</p>
          <p className="text-xs leading-5 text-muted">
            {hasHeading ? "Degrees from the compass frame. This is magnetic context, not a verified bearing." : "Not reporting. The sketch leaves heading null until the compass model is verified."}
          </p>
        </div>
      </div>
      <div>
        <p className="text-xs font-semibold tracking-wide text-muted">Sonar clearance</p>
        <p className="num text-3xl font-semibold">
          {hasRange ? range.toFixed(1) : "—"}
          <span className="ml-1 text-base text-muted">cm</span>
        </p>
        <p className="text-sm">{sample?.range_status ?? "no frame"}</p>
        <div className="mt-2 h-2 bg-[#e7edf3]">
          <div className="h-2 bg-orange" style={{ width: hasRange ? `${Math.min(100, (range / 400) * 100)}%` : "0%" }} />
        </div>
        <p className="mt-2 text-xs leading-5 text-muted">
          Coarse clearance to an exposed surface. A null range is not 0 cm. Pulse {sample?.range_pw_us ?? "—"} µs.
        </p>
      </div>
    </Panel>
  );
}

function formatChannel(sample: BenchSample | null, key: (typeof TRACES)[number]["key"]): string {
  const value = sample?.[key];
  if (value == null) return "null";
  return typeof value === "number" && !Number.isInteger(value) ? value.toFixed(1) : String(value);
}

function statusCopy(status: string): string {
  if (status === "CONNECTED") return "Fresh multi-sensor frames are arriving from the connected Uno.";
  if (status === "WAITING") return "The COM port is open, but no multi-sensor JSON frame has arrived. The port may still be running the HC-SR04 sentence sketch.";
  if (status === "STALE") return "The port is open, but the last bench frame is older than 1.5 seconds. Existing points stay on the chart and no new values are invented.";
  return "The serial port is closed. No new bench samples are being added.";
}
