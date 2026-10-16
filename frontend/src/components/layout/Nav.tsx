import type { PageId } from "../../types/mission";

const LINKS: Array<{ id: PageId; label: string }> = [
  { id: "dashboard", label: "Live run" },
  { id: "field", label: "Field" },
  { id: "simulation", label: "Setup" },
  { id: "lab", label: "Sensor lab" },
  { id: "bench", label: "Bench test" },
  { id: "architecture", label: "How it works" },
  { id: "about", label: "About" },
];

export function Nav({ page, onChange }: { page: PageId; onChange: (page: PageId) => void }) {
  return (
    <nav className="flex h-12 shrink-0 items-center gap-1 overflow-x-auto border-b border-line bg-panel-2 px-4">
      {LINKS.map((link) => (
        <button
          key={link.id}
          type="button"
          onClick={() => onChange(link.id)}
          className={`h-12 shrink-0 whitespace-nowrap px-3 text-[15px] font-semibold ${
            page === link.id ? "border-b-[3px] border-orange text-text" : "border-b-[3px] border-transparent text-muted hover:text-text"
          }`}
        >
          {link.label}
        </button>
      ))}
    </nav>
  );
}
