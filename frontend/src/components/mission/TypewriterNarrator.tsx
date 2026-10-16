import { useEffect, useState } from "react";

export function TypewriterNarrator({
  title,
  text,
  active,
  speed = 1,
}: {
  title: string;
  text: string;
  active: boolean;
  speed?: number;
}) {
  const [shown, setShown] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setShown("");
    setDone(false);
    if (!text) return;

    let index = 0;
    let timer = 0;
    const rate = Math.max(0.5, Math.min(speed, 10));

    const tick = () => {
      const burst = rate >= 8 ? 6 : rate >= 5 ? 3 : rate >= 2 ? 2 : 1;
      index = Math.min(text.length, index + burst);
      setShown(text.slice(0, index));
      if (index >= text.length) {
        setDone(true);
        return;
      }
      const ch = text[index - 1];
      const pause = ch === "." || ch === "!" || ch === "?" ? 160 : ch === "," || ch === "—" || ch === ";" ? 70 : 18;
      timer = window.setTimeout(tick, Math.max(4, pause / rate));
    };

    timer = window.setTimeout(tick, 40);
    return () => window.clearTimeout(timer);
  }, [text, speed]);

  return (
    <section className="border border-line bg-panel px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-orange">{title}</p>
        <p className="text-xs font-semibold text-muted">{active ? (done ? "Ready" : "Narrating…") : "Paused"}</p>
      </div>
      <p className="mt-2 min-h-[3.2rem] text-[17px] font-semibold leading-7 text-text">
        {shown}
        <span
          className={`ml-0.5 inline-block h-[1.05em] w-[0.55ch] translate-y-[0.12em] bg-orange align-baseline ${
            done ? "opacity-0" : "animate-pulse"
          }`}
          aria-hidden
        />
      </p>
    </section>
  );
}
