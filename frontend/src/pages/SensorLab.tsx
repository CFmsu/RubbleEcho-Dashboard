import { useState } from "react";
import { Panel } from "../components/common/Panel";
import { FusionPanel } from "../components/sensors/FusionPanel";
import { WaveformChart } from "../components/sensors/WaveformChart";
import type { LabResult } from "../types/mission";

const STIMULI: Array<{ id: string; label: string }> = [
  { id: "knock", label: "Knock" },
  { id: "human_tap", label: "Human Tap" },
  { id: "noise_burst", label: "Noise Burst" },
  { id: "cavity_response", label: "Cavity Response" },
  { id: "weak_response", label: "Weak Response" },
  { id: "strong_response", label: "Strong Response" },
];

export function SensorLab({
  onStimulus,
  onOpenBench,
}: {
  onStimulus: (name: string) => Promise<LabResult | null>;
  onOpenBench: () => void;
}) {
  const [result, setResult] = useState<LabResult | null>(null);
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="mx-auto grid max-w-6xl gap-3 lg:grid-cols-[240px_1fr]">
      <Panel title="Manual stimuli" aside="Synthetic" bodyClassName="p-3">
        <p className="mb-3 text-[12px] leading-5 text-muted">
          Trigger isolated sensor cases without running the search. These traces are synthetic. The multi-sensor bench is a separate live page.
        </p>
        <button type="button" className="cmd primary mb-3" onClick={onOpenBench}>
          Multi-sensor Bench Test
        </button>
        <div className="grid gap-2">
          {STIMULI.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`cmd ${active === item.id ? "active" : ""}`}
              onClick={() => {
                setActive(item.id);
                void onStimulus(item.id).then((value) => {
                  if (value) setResult(value);
                });
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </Panel>
      <div className="grid gap-3">
        <div className="grid gap-3 lg:grid-cols-2">
          <Panel title="Piezo waveform" aside="Synthetic" bodyClassName="p-2">
            <div className="h-40">
              <WaveformChart samples={result?.vibration.waveform.samples} stroke="#1f4b7a" empty="Choose a stimulus" />
            </div>
          </Panel>
          <Panel title="Acoustic waveform" aside="Synthetic" bodyClassName="p-2">
            <div className="h-40">
              <WaveformChart samples={result?.audio.waveform.samples} stroke="#e85d04" empty="Choose a stimulus" />
            </div>
          </Panel>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          <Panel title="Calculated features" bodyClassName="p-3">
            {result ? (
              <dl className="grid gap-1.5 text-[13px]">
                <Row label="Audio state" value={result.features.audio_state} />
                <Row label="Audio label" value={result.features.audio_label} />
                <Row label="Peak amplitude" value={result.features.peak_amplitude.toFixed(3)} />
                <Row label="Signal energy" value={result.features.signal_energy.toFixed(4)} />
                <Row label="Cavity response" value={result.features.cavity_response.toFixed(2)} />
                <Row label="Dominant frequency" value={`${result.features.dominant_frequency_hz.toFixed(1)} Hz`} />
                <p className="pt-2 text-[12px] text-muted">{result.note}</p>
              </dl>
            ) : (
              <p className="text-[13px] text-muted">Features appear after a stimulus.</p>
            )}
          </Panel>
          <Panel title="Fusion confidence" bodyClassName="px-3 py-2">
            <FusionPanel fusion={result?.fusion ?? null} />
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
