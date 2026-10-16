import { useEffect, useRef, useState } from "react";
import type { CellClassification, GridCell } from "../../types/field";

const TINT: Record<CellClassification, string> = {
  debris_covered: "bg-[#e85d04]/40",
  obstructed: "bg-[#c1121f]/35",
  clear_surface: "bg-[#1b7a4a]/35",
  possible_opening: "bg-[#1f4b7a]/40",
  uncertain: "bg-[#121820]/20",
};

const LABEL: Record<CellClassification, string> = {
  debris_covered: "Debris",
  obstructed: "Obstructed",
  clear_surface: "Clear surface",
  possible_opening: "Possible opening",
  uncertain: "Uncertain",
};

export function PhotoGrid({
  src,
  cells,
  selected,
  onSelect,
}: {
  src: string;
  cells: GridCell[];
  selected: string | null;
  onSelect: (cell: string) => void;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const [box, setBox] = useState({ left: 0, top: 0, width: 0, height: 0 });

  useEffect(() => {
    const measure = () => {
      const img = image.current;
      const host = frame.current;
      if (!img || !host || !img.naturalWidth || !img.naturalHeight) return;
      const bounds = host.getBoundingClientRect();
      const scale = Math.min(bounds.width / img.naturalWidth, bounds.height / img.naturalHeight);
      const width = img.naturalWidth * scale;
      const height = img.naturalHeight * scale;
      setBox({
        left: (bounds.width - width) / 2,
        top: (bounds.height - height) / 2,
        width,
        height,
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (frame.current) observer.observe(frame.current);
    const img = image.current;
    img?.addEventListener("load", measure);
    return () => {
      observer.disconnect();
      img?.removeEventListener("load", measure);
    };
  }, [src]);

  return (
    <div ref={frame} className="relative h-full min-h-[320px] bg-[#121820]">
      <img ref={image} src={src} alt="Uploaded field photograph" className="h-full w-full object-contain" />
      {box.width > 0 ? (
        <div
          className="absolute grid grid-cols-4 grid-rows-4"
          style={{ left: box.left, top: box.top, width: box.width, height: box.height }}
        >
          {cells.map((cell) => (
            <button
              key={cell.cell}
              type="button"
              onClick={() => onSelect(cell.cell)}
              className={`relative border border-white/70 text-left ${cell.source === "unanalyzed" ? "bg-transparent" : TINT[cell.classification]} ${
                selected === cell.cell ? "outline outline-2 outline-orange" : ""
              }`}
            >
              <span className="absolute left-1 top-1 bg-white/90 px-1 font-mono text-[12px] font-semibold text-text">{cell.cell}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function classificationLabel(value: CellClassification): string {
  return LABEL[value];
}
