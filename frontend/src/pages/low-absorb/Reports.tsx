import { ClipboardCheck, FileText, History } from "lucide-react";
import { EmptyContentArea, LowAbsorbPageShell, PlaceholderGrid } from "./shared";

export function Reports() {
  return (
    <LowAbsorbPageShell
      title="复盘报告"
      description="展示收盘报告、人工成交复盘和策略复盘材料的占位工作区。"
    >
      <PlaceholderGrid
        cards={[
          { title: "收盘报告", description: "预留信号、计划、人工成交和风险总结。", icon: FileText },
          { title: "复盘清单", description: "预留失效原因、执行偏差和次日观察项。", icon: ClipboardCheck },
          { title: "历史归档", description: "预留按交易日检索的复盘材料。", icon: History },
        ]}
      />
      <EmptyContentArea />
    </LowAbsorbPageShell>
  );
}
