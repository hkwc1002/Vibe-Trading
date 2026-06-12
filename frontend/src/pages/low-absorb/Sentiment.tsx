import { LOW_ABSORB_SENTIMENT_MOCK } from "@/mocks/lowAbsorb";
import { AShareSentimentPanel } from "@/components/low-absorb/sentiment/AShareSentimentPanel";
import { GlobalSentimentPanel } from "@/components/low-absorb/sentiment/GlobalSentimentPanel";
import { NewsMonitorPreview } from "@/components/low-absorb/sentiment/NewsMonitorPreview";
import { SentimentOverview } from "@/components/low-absorb/sentiment/SentimentOverview";
import { SentimentRulesPanel } from "@/components/low-absorb/sentiment/SentimentRulesPanel";
import { SocialMonitorPreview } from "@/components/low-absorb/sentiment/SocialMonitorPreview";
import { TwinSentimentClock } from "@/components/low-absorb/sentiment/TwinSentimentClock";
import { LowAbsorbPageShell } from "./shared";

export function Sentiment() {
  return (
    <LowAbsorbPageShell
      title="市场情绪"
      description="展示宏观情绪闸门、A 股风险偏好、全球风险偏好和未来监听接口的 mock 工作区。"
    >
      <SentimentOverview metrics={LOW_ABSORB_SENTIMENT_MOCK.metrics} />
      <TwinSentimentClock />
      <div className="grid gap-4 xl:grid-cols-2">
        <AShareSentimentPanel gates={LOW_ABSORB_SENTIMENT_MOCK.aShareGates} />
        <GlobalSentimentPanel gates={LOW_ABSORB_SENTIMENT_MOCK.globalGates} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <SocialMonitorPreview items={LOW_ABSORB_SENTIMENT_MOCK.socialPreviews} />
        <NewsMonitorPreview items={LOW_ABSORB_SENTIMENT_MOCK.newsPreviews} />
      </div>
      <SentimentRulesPanel rules={LOW_ABSORB_SENTIMENT_MOCK.rules} />
    </LowAbsorbPageShell>
  );
}
