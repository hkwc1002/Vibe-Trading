import { Bell, SlidersHorizontal, Webhook } from "lucide-react";
import { EmptyContentArea, LowAbsorbPageShell, PlaceholderGrid } from "./shared";

export function Settings() {
  return (
    <LowAbsorbPageShell
      title="系统设置"
      description="展示策略参数、飞书通知和人工执行偏好的占位工作区。"
    >
      <PlaceholderGrid
        cards={[
          { title: "策略参数", description: "预留时间窗、过滤阈值和风控参数。", icon: SlidersHorizontal },
          { title: "飞书通知", description: "预留 webhook、幂等键和测试卡配置。", icon: Webhook },
          { title: "人工偏好", description: "预留提醒节奏、复盘模板和显示设置。", icon: Bell },
        ]}
      />
      <EmptyContentArea />
    </LowAbsorbPageShell>
  );
}

