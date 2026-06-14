# Low Absorb 后续优化任务拆解

## 1. 任务说明

本任务列表面向 Claude Code CLI 执行。每个任务应尽量覆盖 1-3 个文件，并保持可独立验收。执行时必须遵守人工执行交易边界：不实现真实券商下单、不接入券商交易 API、不实现自动交易、不出现禁用动作按钮文案。

任务依赖标记：

- `P0`：必须优先完成。
- `P1`：核心能力任务。
- `P2`：增强任务。
- `parallel`：可与其他无依赖任务并行。
- `blocked`：需要上游任务完成或用户确认。

## 2. P0 任务

### T001：页面中文化访问验收

- 优先级：P0
- 并行：parallel
- 文件范围：
  - `frontend/src/pages/Home.tsx`
  - `frontend/src/components/layout/Layout.tsx`
  - `frontend/index.html`
- 任务内容：
  - 确认首页、品牌名、页面标题和主菜单显示为简体中文。
  - 确认品牌名为 `Elio 胡交易看板`。
  - 检查页面无明显英文残留、乱码、截断和溢出。
- 验收标准：
  - 首页可正常打开。
  - 品牌名显示正确。
  - 主导航显示中文。

### T002：Low Absorb 禁用动作文案巡检

- 优先级：P0
- 并行：parallel
- 文件范围：
  - `frontend/src/pages/low-absorb/Workbench.tsx`
  - `frontend/src/components/low-absorb/workbench/SignalPanel.tsx`
  - `frontend/src/components/low-absorb/workbench/TradePlanPanel.tsx`
- 任务内容：
  - 检查 Low Absorb 工作台动作按钮文案。
  - 确认不存在独立按钮文案：买入、卖出、下单、自动交易。
  - 只保留人工执行语义。
- 验收标准：
  - 禁用动作文案不存在。
  - 人工执行动作文案存在且清晰。

## 3. 数据源任务

### T003：定义统一行情数据源契约

- 优先级：P1
- 并行：blocked
- 依赖：T001
- 文件范围：
  - `agent/src/low_absorb/data_provider.py`
  - `agent/src/low_absorb/models.py`
- 任务内容：
  - 扩展 Low Absorb 数据源契约。
  - 覆盖 A 股日线、分钟线、市场宽度、行业强度、新闻和 F10 数据。
  - 增加数据源状态、数据时间戳和数据新鲜度字段。
- 验收标准：
  - 数据源契约能表达 A 股、全球行情和美股行情。
  - 数据缺失或过期能够被上层识别。

### T004：接入 A 股数据源适配层

- 优先级：P1
- 并行：blocked
- 依赖：T003
- 文件范围：
  - `agent/src/low_absorb/data_provider.py`
  - `agent/src/low_absorb/config.py`
  - `agent/tests/test_low_absorb_data_sources.py`
- 任务内容：
  - 使用 Python 后端代码接入 `a-stock-data` 能力。
  - 封装为 Low Absorb 数据源适配器。
  - 支持真实数据失败时明确返回失败原因。
- 验收标准：
  - A 股数据由后端数据源模块提供。
  - 数据源失败时不生成交易建议。
  - 测试覆盖正常数据和异常数据。

### T005：接入全球行情与美股行情适配层

- 优先级：P1
- 并行：parallel
- 依赖：T003
- 文件范围：
  - `agent/src/low_absorb/data_provider.py`
  - `agent/src/low_absorb/sentiment.py`
  - `agent/tests/test_low_absorb_data_sources.py`
- 任务内容：
  - 增加美股和全球指数数据源适配。
  - 第一阶段可使用 `yfinance` 或 `Stooq`。
  - 数据用于全球风险偏好和海外科技情绪判断。
- 验收标准：
  - 市场情绪能消费全球风险偏好数据。
  - 数据源异常时返回观察或拦截结论。

### T006：实现数据新鲜度 fail-closed

- 优先级：P1
- 并行：blocked
- 依赖：T004, T005
- 文件范围：
  - `agent/src/low_absorb/scanner.py`
  - `agent/src/low_absorb/sentiment.py`
  - `agent/tests/test_low_absorb_scanner.py`
- 任务内容：
  - 在扫描和情绪门控中检查数据新鲜度。
  - 超过阈值时不生成信号。
  - 返回可解释拦截原因。
- 验收标准：
  - 过期数据不生成交易计划。
  - 测试覆盖 stale data 场景。

## 4. 英伟达 AI 服务器成本链任务

### T007：扩展成本链数据模型

- 优先级：P1
- 并行：parallel
- 文件范围：
  - `agent/src/low_absorb/models.py`
  - `agent/src/low_absorb/config.py`
  - `frontend/src/types/lowAbsorb.ts`
- 任务内容：
  - 增加成本权重、权重区间、代际增幅、来源类型、置信度、as_of、估算说明等字段。
  - 保留 `GB200 NVL72`、`GB300 NVL72`、`custom/manual` 版本。
- 验收标准：
  - 前后端类型可以表达完整成本链字段。
  - 前端不硬编码真实成本权重。

### T008：填充成本链资料配置

- 优先级：P1
- 并行：blocked
- 依赖：T007
- 文件范围：
  - `agent/src/low_absorb/chain_matrix.py`
  - `agent/src/low_absorb/config.py`
  - `agent/tests/test_low_absorb_chain_matrix.py`
- 任务内容：
  - 基于专业资料填充英伟达 AI 服务器成本链配置。
  - 区分官方资料、券商估算、产业研究和手动维护。
  - 每条数据必须带置信度和 as_of 日期。
- 验收标准：
  - 成本链快照返回完整字段。
  - 低置信度数据可展示但不单独决定交易建议。

### T009：实现 custom/manual 成本链编辑保存

- 优先级：P1
- 并行：blocked
- 依赖：T007
- 文件范围：
  - `agent/src/low_absorb/api/chain.py`
  - `agent/src/low_absorb/storage.py`
  - `agent/tests/test_low_absorb_chain_api.py`
- 任务内容：
  - 仅允许更新 `custom/manual` 版本。
  - 更新后持久化。
  - 返回掩码或安全响应，不暴露敏感信息。
- 验收标准：
  - custom/manual 可保存。
  - 非 custom/manual 更新被拒绝。

### T010：AI 产业链页面显示来源与置信度

- 优先级：P1
- 并行：blocked
- 依赖：T007, T009
- 文件范围：
  - `frontend/src/pages/low-absorb/Chain.tsx`
  - `frontend/src/pages/low-absorb/__tests__/DecisionDashboardUi.test.tsx`
- 任务内容：
  - 成本总览展示来源类型、置信度、as_of 和估算说明。
  - 显示自定义版本保存结果。
- 验收标准：
  - 成本链表格显示来源与置信度。
  - 页面测试覆盖版本切换和自定义保存。

## 5. 交易建议与策略闭环任务

### T011：将成本链权重纳入信号排序

- 优先级：P1
- 并行：blocked
- 依赖：T006, T008
- 文件范围：
  - `agent/src/low_absorb/scanner.py`
  - `agent/src/low_absorb/chain_matrix.py`
  - `agent/tests/test_low_absorb_scanner.py`
- 任务内容：
  - 信号排序使用 AI 分支强度和成本链 signal weight。
  - 弱分支股票降级或拦截。
  - 强成本增量板块在技术条件相近时提高优先级。
- 验收标准：
  - 技术条件相同时强分支排序更高。
  - 弱分支存在降级或拦截原因。

### T012：扩展交易计划 AI 产业链解释

- 优先级：P1
- 并行：blocked
- 依赖：T011
- 文件范围：
  - `agent/src/low_absorb/trade_plan.py`
  - `agent/src/low_absorb/models.py`
  - `agent/tests/test_low_absorb_trade_plan.py`
- 任务内容：
  - 交易计划包含分支强度、成本链权重、排序理由和降级原因。
  - 人类可读解释用于前端详情抽屉和飞书卡片。
- 验收标准：
  - 交易计划中存在 AI 产业链解释。
  - 解释包含分支强度和成本链权重。

### T013：完善 Workbench 右侧详情抽屉

- 优先级：P2
- 并行：blocked
- 依赖：T012
- 文件范围：
  - `frontend/src/pages/low-absorb/Workbench.tsx`
  - `frontend/src/components/low-absorb/workbench/FeishuPreviewCard.tsx`
  - `frontend/src/components/low-absorb/workbench/ManualFillDrawer.tsx`
- 任务内容：
  - 展示信号详情、交易计划详情、飞书预览、人工成交表单和风险解释。
  - 保持所有动作是人工执行语义。
- 验收标准：
  - 用户可查看计划详情和飞书预览。
  - 用户可记录人工成交。
  - 无禁用动作文案。

### T014：完善底部统一动作栏

- 优先级：P2
- 并行：blocked
- 依赖：T013
- 文件范围：
  - `frontend/src/pages/low-absorb/Workbench.tsx`
  - `frontend/src/components/low-absorb/workbench/TradePlanPanel.tsx`
- 任务内容：
  - 在详情上下文中统一展示推送飞书、复制人工下单信息、记录人工成交、生成风控提醒、标记失效等动作。
  - 禁止出现真实交易执行语义。
- 验收标准：
  - 动作栏可根据选中对象变化。
  - 动作文案符合人工执行边界。

## 6. 市场情绪任务

### T015：扩展交易许可快照

- 优先级：P1
- 并行：parallel
- 依赖：T005
- 文件范围：
  - `agent/src/low_absorb/sentiment.py`
  - `agent/src/low_absorb/api/sentiment.py`
  - `agent/tests/test_low_absorb_sentiment.py`
- 任务内容：
  - 返回全球情绪、A 股情绪、六个闸门和交易许可结论。
  - 支持允许、观察、拦截三类结论。
- 验收标准：
  - 情绪快照可解释交易许可。
  - 异常数据返回观察或拦截。

### T016：市场情绪页面仪表化

- 优先级：P2
- 并行：blocked
- 依赖：T015
- 文件范围：
  - `frontend/src/pages/low-absorb/Sentiment.tsx`
  - `frontend/src/components/low-absorb/sentiment/SentimentRulesPanel.tsx`
  - `frontend/src/pages/low-absorb/__tests__/Stage9Pages.test.tsx`
- 任务内容：
  - 展示全球情绪仪表、A 股情绪仪表、六个 instrument panels 和事件流。
- 验收标准：
  - 用户能看到交易许可结论。
  - 页面测试覆盖六个闸门。

## 7. 回测与报告任务

### T017：定义回测快照契约

- 优先级：P2
- 并行：parallel
- 文件范围：
  - `agent/src/low_absorb/api/backtest.py`
  - `agent/src/low_absorb/models.py`
  - `frontend/src/types/lowAbsorb.ts`
- 任务内容：
  - 定义回测总览、参数、历史信号、敏感性、分支归因和改进建议的数据结构。
- 验收标准：
  - 前后端类型能覆盖回测页面所需字段。

### T018：增强策略回测页面

- 优先级：P2
- 并行：blocked
- 依赖：T017
- 文件范围：
  - `frontend/src/pages/low-absorb/Backtest.tsx`
  - `frontend/src/components/low-absorb/backtest/BacktestOverview.tsx`
  - `frontend/src/pages/low-absorb/__tests__/Stage9Pages.test.tsx`
- 任务内容：
  - 展示回测总览、策略参数、历史信号、参数敏感性、分支归因和改进建议。
- 验收标准：
  - 回测页不只是静态占位。
  - 页面可解释策略有效和失效场景。

### T019：实现收盘报告快照与归档

- 优先级：P2
- 并行：parallel
- 文件范围：
  - `agent/src/low_absorb/report.py`
  - `agent/src/low_absorb/api/reports.py`
  - `agent/tests/test_low_absorb_reports.py`
- 任务内容：
  - 生成并保存收盘报告。
  - 报告包含信号、计划、飞书、人工成交、持仓风险、失效原因和次日监督事项。
- 验收标准：
  - 报告可保存和读取。
  - 报告区分系统建议与人工执行结果。

### T020：增强复盘报告页面

- 优先级：P2
- 并行：blocked
- 依赖：T019
- 文件范围：
  - `frontend/src/pages/low-absorb/Reports.tsx`
  - `frontend/src/pages/low-absorb/__tests__/LowAbsorbPages.test.tsx`
- 任务内容：
  - 展示收盘报告、复盘清单、风险变化和历史归档。
- 验收标准：
  - 用户可查看历史报告。
  - 页面显示当日复盘摘要。

## 8. 设置与存储任务

### T021：扩展 Low Absorb 设置项

- 优先级：P1
- 并行：parallel
- 文件范围：
  - `agent/src/low_absorb/config.py`
  - `agent/src/low_absorb/api/settings.py`
  - `agent/tests/test_low_absorb_settings.py`
- 任务内容：
  - 增加数据源模式、全球行情源、美股行情源、数据新鲜度阈值、成本链版本等设置。
- 验收标准：
  - 设置可读取和更新。
  - 敏感信息不明文回显。

### T022：扩展设置页面

- 优先级：P2
- 并行：blocked
- 依赖：T021
- 文件范围：
  - `frontend/src/pages/low-absorb/Settings.tsx`
  - `frontend/src/pages/low-absorb/__tests__/SettingsUi.test.tsx`
- 任务内容：
  - 显示并编辑核心阈值、数据源模式、飞书机器人地址和成本链版本。
  - 保存后敏感信息只显示掩码。
- 验收标准：
  - 设置页可更新数据源和阈值。
  - 飞书机器人地址不完整暴露。

### T023：扩展持久化仓储

- 优先级：P1
- 并行：blocked
- 依赖：T007, T021
- 文件范围：
  - `agent/src/low_absorb/storage.py`
  - `agent/tests/test_low_absorb_storage.py`
- 任务内容：
  - 持久化信号、计划、成交、持仓、风险、报告、通知、设置、成本链。
- 验收标准：
  - 重启或重新加载后关键数据仍可读取。
  - 测试覆盖存储 roundtrip。

## 9. 总体验收任务

### T024：补充端到端业务流测试

- 优先级：P1
- 并行：blocked
- 依赖：T011, T012, T013, T015, T019, T023
- 文件范围：
  - `agent/tests/test_low_absorb_workflow.py`
  - `frontend/src/pages/low-absorb/__tests__/DecisionDashboardUi.test.tsx`
- 任务内容：
  - 覆盖 signal → trade plan → Feishu recommendation → manual fill → position supervision → close report。
- 验收标准：
  - 主流程测试通过。
  - 人工执行边界测试通过。

### T025：执行验证命令

- 优先级：P0
- 并行：blocked
- 依赖：全部实现任务
- 文件范围：
  - 无固定文件
- 任务内容：
  - 运行后端 Low Absorb 测试。
  - 运行前端测试。
  - 运行前端构建。
  - 打开本地页面进行人工可视检查。
- 验收标准：
  - 后端测试通过。
  - 前端测试通过。
  - 前端构建通过。
  - 页面可正常打开。

## 10. 推荐执行顺序

1. T001、T002。
2. T003、T007、T021。
3. T004、T005、T008、T009、T023。
4. T006、T011、T012、T015。
5. T010、T013、T014、T016。
6. T017、T018、T019、T020、T022。
7. T024、T025。
