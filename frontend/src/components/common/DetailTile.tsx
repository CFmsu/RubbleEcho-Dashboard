import type { ReactNode } from "react";

export function DetailTile({
  title,
  value,
  hint,
  onOpen,
}: {
  title: string;
  value: ReactNode;
  hint?: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex min-h-[64px] flex-col items-start justify-center border border-line bg-panel px-3 py-2 text-left transition-colors hover:border-orange hover:bg-[#fff1e7]"
    >
      <span className="text-sm text-muted">{title}</span>
      <span className="mt-0.5 w-full truncate text-[16px] font-bold text-text">{value}</span>
      <span className="mt-1 text-xs font-semibold text-orange">{hint ?? "Open"}</span>
    </button>
  );
}
