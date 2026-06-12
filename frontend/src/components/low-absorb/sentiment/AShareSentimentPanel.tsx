import type { LowAbsorbSentimentGate } from "@/types/lowAbsorb";

export function AShareSentimentPanel({ gates }: { gates: LowAbsorbSentimentGate[] }) {
  return <GatePanel title="A 股情绪闸门" gates={gates} />;
}

function GatePanel({ title, gates }: { title: string; gates: LowAbsorbSentimentGate[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      <div className="mt-4 space-y-3">
        {gates.map((gate) => (
          <div key={gate.id} className="flex items-center justify-between gap-4 rounded-md border bg-background px-3 py-2">
            <div>
              <p className="text-sm font-medium text-foreground">{gate.label}</p>
              <p className="text-xs text-muted-foreground">{gate.value}</p>
            </div>
            <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">{gate.status}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
