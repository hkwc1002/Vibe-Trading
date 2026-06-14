import { Link } from "react-router-dom";
import { ArrowRight, Bot, BarChart3, Zap, UserCircle2 } from "lucide-react";

export function Home() {
  const FEATURES = [
    { icon: Bot, title: "AI 智能体", desc: "用自然语言生成策略，并通过 ReAct 推理拆解研究步骤" },
    { icon: BarChart3, title: "内置回测", desc: "覆盖 A 股、美股/港股与数字货币的多数据源回测" },
    { icon: Zap, title: "实时流式过程", desc: "实时查看智能体思考、调用工具和迭代分析" },
    { icon: UserCircle2, title: "策略复盘", desc: "交易日志分析与影子账户回测，提取规则并归因盈亏差异" },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      <div className="max-w-2xl text-center space-y-6">
        <h1 className="text-4xl font-bold tracking-tight">Elio 胡交易看板</h1>
        <p className="text-lg text-muted-foreground">用自然语言描述交易策略，智能体会生成代码、执行回测并给出优化建议，过程实时可见。</p>
        <Link
          to="/agent"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-medium hover:opacity-90 transition"
        >
          开始研究 <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-16 max-w-5xl w-full">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="border rounded-lg p-6 space-y-3">
            <Icon className="h-8 w-8 text-primary" />
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
