export function SentimentRulesPanel({ rules }: { rules: string[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">情绪规则预览</h2>
      <ul className="mt-4 space-y-2 text-sm leading-6 text-muted-foreground">
        {rules.map((rule) => (
          <li key={rule} className="rounded-md border bg-background px-3 py-2">{rule}</li>
        ))}
      </ul>
    </section>
  );
}
