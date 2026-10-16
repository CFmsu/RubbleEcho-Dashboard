import type { ReactNode } from "react";

export function Panel({
  title,
  aside,
  children,
  className = "",
  bodyClassName = "",
  fitContent = false,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  fitContent?: boolean;
}) {
  return (
    <section className={`flex min-h-0 flex-col border border-line bg-panel ${fitContent ? "h-auto shrink-0" : "h-full"} ${className}`}>
      <header className="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-line px-4">
        <h2 className="truncate text-base font-bold text-text">{title}</h2>
        {aside ? <div className="max-w-[55%] truncate text-sm text-muted">{aside}</div> : null}
      </header>
      <div className={`min-h-0 ${fitContent ? "" : "flex-1"} ${bodyClassName}`}>{children}</div>
    </section>
  );
}
