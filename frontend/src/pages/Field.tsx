import { useEffect, useMemo, useState } from "react";
import { Panel } from "../components/common/Panel";
import { PhotoGrid, classificationLabel } from "../components/field/PhotoGrid";
import { ApiError, getJson, postForm, postJson } from "../services/api";
import { connectField } from "../services/fieldSocket";
import type { CellClassification, FieldObservation, FieldSnapshot } from "../types/field";
import type { ConnectionStatus } from "../types/mission";

const CLASSIFICATIONS: CellClassification[] = [
  "debris_covered",
  "obstructed",
  "clear_surface",
  "possible_opening",
  "uncertain",
];

export function Field({
  operatingMode,
  onMode,
}: {
  operatingMode: "demo" | "real";
  onMode: (mode: "demo" | "real") => void;
}) {
  const [snapshot, setSnapshot] = useState<FieldSnapshot | null>(null);
  const [link, setLink] = useState<ConnectionStatus>("connecting");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [classification, setClassification] = useState<CellClassification>("uncertain");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [port, setPort] = useState("");
  const [models, setModels] = useState("");

  useEffect(() => connectField(setSnapshot, setLink), []);

  const observation = useMemo(() => {
    const items = snapshot?.observations ?? [];
    return items.find((item) => item.id === selectedId) ?? items[0] ?? null;
  }, [snapshot, selectedId]);

  useEffect(() => {
    if (!observation || !selectedCell) return;
    const cell = observation.cells.find((item) => item.cell === selectedCell);
    if (!cell) return;
    setClassification(cell.classification);
    setNote(cell.observation);
  }, [observation, selectedCell]);

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The request failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 border border-line bg-panel px-4 py-3">
        <div>
          <p className="text-sm font-bold tracking-wide text-orange">{operatingMode === "real" ? "REAL MODE" : "DEMO MODE"}</p>
          <p className="text-sm text-muted">
            Real mode shows uploaded photographs, model responses, and serial events only. The live run page stays a labeled simulation.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" className={`cmd ${operatingMode === "demo" ? "active" : ""}`} onClick={() => onMode("demo")}>
            Demo
          </button>
          <button type="button" className={`cmd ${operatingMode === "real" ? "active" : ""}`} onClick={() => onMode("real")}>
            Real
          </button>
        </div>
      </div>
      {snapshot?.warnings.map((warning) => (
        <p key={warning} className="border border-line bg-[#fff1e7] px-4 py-2 text-sm text-text">
          {warning}
        </p>
      ))}
      {error ? <p className="border border-red bg-[#fde8ea] px-4 py-2 text-sm text-red">{error}</p> : null}
      <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
        <Panel title="Field photograph" aside={observation ? observation.source : "No photograph yet"} bodyClassName="flex min-h-[420px] flex-col">
          {observation ? (
            <PhotoGrid
              src={`/api/observations/${observation.id}/image?t=${encodeURIComponent(observation.created_at)}`}
              cells={observation.cells}
              selected={selectedCell}
              onSelect={setSelectedCell}
            />
          ) : (
            <div className="grid h-full place-items-center px-6 text-center text-muted">
              Upload a JPEG, PNG, or HEIC photograph from the iPhone. The 4×4 grid is A1 at the top left through D4 at the bottom right.
            </div>
          )}
        </Panel>
        <div className="flex min-h-0 flex-col gap-3">
          <Panel title="Photograph" aside={link}>
            <div className="flex flex-col gap-3 p-4">
              <label className="text-sm font-semibold">
                iPhone photograph
                <input
                  className="mt-1 block w-full text-sm"
                  type="file"
                  accept="image/jpeg,image/png,image/heic,image/heif,.jpg,.jpeg,.png,.heic,.heif"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (!file) return;
                    const body = new FormData();
                    body.set("file", file);
                    body.set("source", "iphone_camera");
                    void run(async () => {
                      const created = await postForm<FieldObservation>("/api/observations", body);
                      setSelectedId(created.id);
                      setSelectedCell("A1");
                    });
                  }}
                />
              </label>
              {observation ? (
                <p className="font-mono text-xs text-muted">
                  {observation.id}
                  <br />
                  {observation.created_at} · {observation.width}×{observation.height} · {observation.media_type}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="cmd primary"
                  disabled={!observation || busy}
                  onClick={() => observation && void run(async () => { await postJson(`/api/observations/${observation.id}/analyze`); })}
                >
                  Analyze visible surface
                </button>
                <button
                  type="button"
                  className="cmd"
                  disabled={!observation || busy}
                  onClick={() => observation && void run(async () => { await postJson(`/api/observations/${observation.id}/reason`); })}
                >
                  Write recommendations
                </button>
              </div>
              <InferenceStatus observation={observation} configured={snapshot?.nebius_configured ?? false} />
            </div>
          </Panel>
          <Panel title="Selected sector" aside={selectedCell ?? "none"}>
            <div className="flex flex-col gap-2 p-4">
              <select className="field" value={classification} onChange={(event) => setClassification(event.target.value as CellClassification)}>
                {CLASSIFICATIONS.map((item) => (
                  <option key={item} value={item}>
                    {classificationLabel(item)}
                  </option>
                ))}
              </select>
              <textarea className="min-h-20 border border-line p-2 text-sm" value={note} onChange={(event) => setNote(event.target.value)} placeholder="What is visible in this cell" />
              <button
                type="button"
                className="cmd"
                disabled={!observation || !selectedCell || busy}
                onClick={() =>
                  observation &&
                  selectedCell &&
                  void run(async () => {
                    await postJson(`/api/observations/${observation.id}/cells`, {
                      cell: selectedCell,
                      classification,
                      observation: note,
                      uncertainty: "medium",
                    });
                  })
                }
              >
                Save manual correction
              </button>
              <ul className="grid grid-cols-2 gap-1 text-xs text-muted">
                {CLASSIFICATIONS.map((item) => (
                  <li key={item}>{classificationLabel(item)}</li>
                ))}
              </ul>
            </div>
          </Panel>
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Recommendations" aside={observation?.reasoning.model_id || "no model yet"}>
          <div className="flex flex-col gap-3 p-4 text-sm">
            <p>
              Request {observation?.reasoning.request_status ?? "not_run"}
              {observation?.reasoning.image_input_used ? " · image input used" : " · text observations only"}
            </p>
            {observation?.reasoning.error ? <p className="text-red">{observation.reasoning.error}</p> : null}
            <ul className="flex flex-col gap-2">
              {(observation?.reasoning.priorities ?? []).map((item) => (
                <li key={item.cell} className="border border-line p-2">
                  <p className="font-bold">
                    {item.priority}. {item.cell}
                  </p>
                  <p>{item.reason}</p>
                  <p className="text-muted">Evidence: {item.evidence.join(" ")}</p>
                  <p className="text-muted">Uncertainty: {item.uncertainty}</p>
                  <p>Next: {item.next_action}</p>
                </li>
              ))}
            </ul>
            {(observation?.reasoning.cannot_infer ?? []).length > 0 ? (
              <p className="text-muted">Cannot infer: {observation?.reasoning.cannot_infer.join(", ")}</p>
            ) : null}
          </div>
        </Panel>
        <Panel
          title="ESP32 hardware test"
          aside={<span className={snapshot?.hardware.state === "CONNECTED" ? "text-green" : "text-red"}>{snapshot?.hardware.state ?? "DISCONNECTED"}</span>}
        >
          <div className="flex flex-col gap-3 p-4 text-sm">
            <p>
              Manual hardware test events: <span className="num">{snapshot?.hardware.event_count ?? 0}</span>
              {snapshot?.hardware.port ? ` · ${snapshot.hardware.port}` : ""}
            </p>
            <p className="text-muted">Button presses are manual test events. They are not physiological detections.</p>
            {snapshot?.hardware.error ? <p className="text-red">{snapshot.hardware.error}</p> : null}
            <div className="flex flex-wrap gap-2">
              <select className="field" value={port} onChange={(event) => setPort(event.target.value)}>
                <option value="">COM port</option>
                {(snapshot?.hardware.ports ?? []).map((item) => (
                  <option key={item.device} value={item.device}>
                    {item.device} {item.description}
                  </option>
                ))}
              </select>
              <button type="button" className="cmd primary" disabled={!port || busy} onClick={() => void run(async () => { await postJson("/api/hardware/connect", { port }); })}>
                Connect
              </button>
              <button type="button" className="cmd" disabled={busy} onClick={() => void run(async () => { await postJson("/api/hardware/disconnect"); })}>
                Disconnect
              </button>
            </div>
            <ul className="max-h-40 overflow-auto font-mono text-xs">
              {(snapshot?.hardware.events ?? []).slice().reverse().map((event) => (
                <li key={event.event_id}>
                  {event.received_at} {event.label} {event.device_id} #{event.sequence} {event.uptime_ms} ms
                </li>
              ))}
            </ul>
            <div className="border-t border-line pt-3">
              <p className="font-semibold">HC-SR04 {snapshot?.hardware.link_status ?? "DISCONNECTED"}</p>
              <p className="text-muted">
                Live centimeters are on the Live run page. This page does not invent a distance when the Arduino is unplugged.
              </p>
              <p className="num mt-1">{snapshot?.hardware.distance_count ?? 0} real readings</p>
            </div>
            <button
              type="button"
              className="cmd"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const listed = await getJson<{ models: Array<{ id: string; accepts_images: boolean }> }>("/api/inference/models");
                  setModels(listed.models.map((model) => `${model.id}${model.accepts_images ? " (image)" : ""}`).join("\n"));
                })
              }
            >
              List models
            </button>
            {models ? <pre className="max-h-32 overflow-auto whitespace-pre-wrap font-mono text-xs">{models}</pre> : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function InferenceStatus({ observation, configured }: { observation: FieldObservation | null; configured: boolean }) {
  const analysis = observation?.analysis;
  return (
    <div className="text-sm">
      <p>Model key {configured ? "is set" : "is not set"}</p>
      <p>Vision request {analysis?.request_status ?? "not_run"}{analysis?.model_id ? ` · ${analysis.model_id}` : ""}</p>
      {analysis?.error ? <p className="text-red">{analysis.error}</p> : null}
      {analysis?.summary ? <p>{analysis.summary}</p> : null}
      {analysis?.request_status === "succeeded" && observation ? (
        <ul className="mt-2 grid grid-cols-2 gap-1 text-xs">
          {observation.cells.map((cell) => (
            <li key={cell.cell}>
              {cell.cell} {classificationLabel(cell.classification)} · {cell.source}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
