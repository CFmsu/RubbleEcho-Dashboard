import { useEffect, type ReactNode } from "react";

export function PopOut({
  title,
  aside,
  open,
  onClose,
  children,
}: {
  title: string;
  aside?: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-[#121820]/55" onClick={onClose} />
      <div className="relative z-10 flex max-h-[min(820px,90vh)] w-full max-w-3xl flex-col border border-line bg-panel shadow-[0_24px_80px_rgba(18,24,32,0.28)]">
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-xl font-extrabold text-text">{title}</h2>
            {aside ? <p className="mt-0.5 text-sm text-muted">{aside}</p> : null}
          </div>
          <button type="button" className="cmd primary shrink-0" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto p-5">{children}</div>
      </div>
    </div>
  );
}
