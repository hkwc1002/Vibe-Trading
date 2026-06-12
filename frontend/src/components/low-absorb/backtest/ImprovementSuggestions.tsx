export function ImprovementSuggestions({ suggestions }: { suggestions: string[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">改进建议</h2>
      <ul className="mt-4 space-y-2 text-sm leading-6 text-muted-foreground">
        {suggestions.map((suggestion) => (
          <li key={suggestion} className="rounded-md border bg-background px-3 py-2">{suggestion}</li>
        ))}
      </ul>
    </section>
  );
}
