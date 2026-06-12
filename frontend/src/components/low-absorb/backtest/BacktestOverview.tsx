export function BacktestOverview() {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">回测总览</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        当前页面展示策略回测 contract 和 mock fixture。真实回测引擎、行情拉取和参数寻优将在后端 API 接入后运行。
      </p>
    </section>
  );
}
