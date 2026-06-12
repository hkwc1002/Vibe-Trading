import { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";

const Home = lazy(() => import("@/pages/Home").then((m) => ({ default: m.Home })));
const Agent = lazy(() => import("@/pages/Agent").then((m) => ({ default: m.Agent })));
const RunDetail = lazy(() =>
  import("@/pages/RunDetail").then((m) => ({ default: m.RunDetail })),
);
const Compare = lazy(() =>
  import("@/pages/Compare").then((m) => ({ default: m.Compare })),
);
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const Correlation = lazy(() =>
  import("@/pages/Correlation").then((m) => ({ default: m.Correlation })),
);
const AlphaZoo = lazy(() =>
  import("@/pages/AlphaZoo").then((m) => ({ default: m.AlphaZoo })),
);
const LowAbsorbWorkbench = lazy(() =>
  import("@/pages/low-absorb/Workbench").then((m) => ({ default: m.Workbench })),
);
const LowAbsorbSentiment = lazy(() =>
  import("@/pages/low-absorb/Sentiment").then((m) => ({ default: m.Sentiment })),
);
const LowAbsorbChain = lazy(() =>
  import("@/pages/low-absorb/Chain").then((m) => ({ default: m.Chain })),
);
const LowAbsorbBacktest = lazy(() =>
  import("@/pages/low-absorb/Backtest").then((m) => ({ default: m.Backtest })),
);
const LowAbsorbReports = lazy(() =>
  import("@/pages/low-absorb/Reports").then((m) => ({ default: m.Reports })),
);
const LowAbsorbSettings = lazy(() =>
  import("@/pages/low-absorb/Settings").then((m) => ({ default: m.Settings })),
);

function PageLoader() {
  return (
    <div className="flex h-[60vh] items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function wrap(Component: ComponentType) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: wrap(Home) },
      { path: "/agent", element: wrap(Agent) },
      { path: "/settings", element: wrap(Settings) },
      { path: "/runs/:runId", element: wrap(RunDetail) },
      { path: "/compare", element: wrap(Compare) },
      { path: "/correlation", element: wrap(Correlation) },
      { path: "/alpha-zoo", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/bench", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/compare", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/:alphaId", element: wrap(AlphaZoo) },
      { path: "/low-absorb", element: wrap(LowAbsorbWorkbench) },
      { path: "/low-absorb/sentiment", element: wrap(LowAbsorbSentiment) },
      { path: "/low-absorb/chain", element: wrap(LowAbsorbChain) },
      { path: "/low-absorb/backtest", element: wrap(LowAbsorbBacktest) },
      { path: "/low-absorb/reports", element: wrap(LowAbsorbReports) },
      { path: "/low-absorb/settings", element: wrap(LowAbsorbSettings) },
    ],
  },
]);
