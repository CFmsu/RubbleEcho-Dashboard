import type { SearchDecision } from "../../types/mission";
import { formatPercent } from "../../utils/format";

export function DecisionPanel({ decision }: { decision: SearchDecision }) {
  return (
    <div className="grid h-full content-start gap-2 px-2.5 py-2 text-[12px] leading-5">
      <Block label="Current observation" text={decision.observation} />
      <Block label="Decision" text={decision.decision} />
      <Block label="Reason" text={decision.reason} />
      <div className="flex items-end justify-between border-t border-line pt-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Confidence</div>
          <div className="num text-[18px]">{formatPercent(decision.confidence)}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Decision source</div>
          <div className="tracking-[0.14em] text-yellow">{decision.provider}</div>
        </div>
      </div>
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.14em] text-muted">{label}</div>
      <p>{text}</p>
    </div>
  );
}
