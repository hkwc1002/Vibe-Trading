# 任务列表：Low Absorb 生产化与外部联调

> 任务编号：`002-low-absorb-production-readiness`  
> 基于方案：`specs/active/002-low-absorb-production-readiness/plan.md`  
> 总任务数：5  
> 风险等级：A 类高风险任务

---

## 1. 任务目标

- 补齐真实行情多源稳定性，保证数据异常时信号、情绪许可和交易计划 fail-closed。
- 建立英伟达 AI 服务器成本链半自动采集、候选版本、人工审核、生效、驳回和回滚流程。
- 接入日线级真实回测引擎，输出可复现、可解释、明确限制的研究结果。
- 完成飞书全类型通知的 mock/真实受控联调、幂等和审计。
- 提供 Windows 本机长期运行所需的健康检查、生产配置、备份恢复和部署文档。

---

## 2. 依赖关系图

```text
Task 1 多源行情稳定性
  ├─→ Task 2 成本链半自动更新
  │     ├─→ Task 3 日线级真实回测
  │     └─→ Task 4 飞书真实联调
  └──────────────────────────────┐
Task 3 日线级真实回测 ────────────┤
Task 4 飞书真实联调 ──────────────┤
                                  ↓
Task 5 本机生产部署配置
```

- `Task 1` 是生产化数据质量基础，必须先完成。
- `Task 2`、`Task 3`、`Task 4` 都可能修改 `storage.py` 或共享模型，默认按顺序执行，避免并行冲突。
- `Task 5` 汇总前四批能力，最后执行。

---

## 3. 实现前必读约束

### 3.1 文档与流程约束

- Claude Code 必须先阅读 `brief.md`、`contract.yaml`、`spec.md`、`plan.md`、`tasks.md`。
- Claude Code 必须先生成 `implementation.yaml`，等待 Codex 确认后才能写代码。
- 实现完成后必须自我审查、修复自查问题、重新验证，再生成 `delivery.yaml`。
- Claude Code 不得提交、推送或创建 PR；版本阶段必须等待 Codex `review.yaml` 结论为 `APPROVED_FOR_COMMIT` 且用户授权。

### 3.2 宪法约束

- 文件 ≤ 800 行，函数 ≤ 50 行，嵌套 ≤ 4 层。
- 后端公共 API 必须有类型注解。
- 后端 API 响应格式统一为 `{ success: bool, data: any, error: string | null }`。
- 错误必须显式处理，禁止静默吞掉异常。
- 禁止硬编码密钥、Webhook、Token 或真实账户信息。
- 前端不包含策略规则。
- 测试优先，后端使用 pytest，前端使用 vitest + React Testing Library。

### 3.3 本任务特殊约束

- 本阶段不做页面中文化、品牌文案、首页文字、菜单文字、按钮文字、整体视觉体验或 UI 优化。
- 默认不修改 `frontend/src/**`；如确需修改前端，必须停止并请求 Codex 更新契约。
- A 股数据源可参考 `a-stock-data` skill，但必须封装在后端 provider 内。
- 真实依赖不可用时，可以使用受控 mock/fixture 完成测试，但必须显式标记，不得在生产模式伪装真实数据。
- 如需新增依赖或修改 `pyproject.toml`、`requirements*.txt`、`uv.lock`、`package.json`、`frontend/package.json`，必须停止并请求确认。

### 3.4 金融安全约束

- 不实现真实券商下单。
- 不实现自动买卖。
- 不实现自动委托。
- 不接入券商交易执行 API。
- 不实现一键交易。
- 不添加独立按钮文案：`买入`、`卖出`、`下单`、`自动交易`。
- 允许使用人工执行语义：`推送飞书`、`复制人工下单信息`、`记录人工成交`、`标记失效`、`生成风控提醒`、`记录卖出`。

---

## 4. 需求追踪矩阵

| 需求编号 | 任务编号 | 涉及文件 | 测试或验证 | 验收证据 |
|----------|----------|----------|------------|----------|
| FR-1 | Task 1 | `agent/src/low_absorb/data_sources/**`、`data_provider.py`、`sentiment.py`、`scanner.py` | `pytest agent/tests/test_low_absorb_data_sources.py agent/tests/test_low_absorb_sentiment.py agent/tests/test_low_absorb_scanner.py -q` | 多源 fallback、冲突、过期、全部失败 fail-closed 证据 |
| FR-2 | Task 2 | `agent/src/low_absorb/cost_chain/**`、`chain_matrix.py`、`storage.py`、`api/chain.py` | `pytest agent/tests/test_low_absorb_chain_matrix.py agent/tests/test_low_absorb_chain_api.py agent/tests/test_low_absorb_storage.py -q` | 候选、审核、生效、驳回、回滚、审计证据 |
| FR-3 | Task 3 | `agent/src/low_absorb/backtest/**`、`api/backtest.py`、`scanner.py`、`risk.py` | `pytest agent/tests/test_low_absorb_backtest.py agent/tests/test_low_absorb_api_contract.py -q` | 日线级回测成功、失败、可重复、限制说明证据 |
| FR-4 | Task 4 | `notifier.py`、`api/settings.py`、`api/reports.py`、`storage.py` | `pytest agent/tests/test_low_absorb_notifier.py agent/tests/test_low_absorb_reports.py agent/tests/test_low_absorb_feishu_integration.py -q` | mock/真实开关、幂等、Webhook 掩码、审计证据 |
| FR-5 | Task 5 | `agent/src/low_absorb/deployment/**`、`api/health.py`、`docs/deployment/low_absorb_production.md` | `pytest agent/tests/test_low_absorb_api_contract.py agent/tests/test_low_absorb_main_api_integration.py agent/tests/test_low_absorb_storage.py -q` | readiness、liveness、备份恢复、部署文档证据 |
| 金融安全边界 | 全部任务 | `agent/src/**`、`frontend/src/**` | `rg -n "券商|自动交易|一键交易|买入|卖出|下单" agent/src frontend/src` | 禁止能力和禁用文案扫描说明 |

---

## 5. 全局允许修改范围

| 路径 | 说明 |
|------|------|
| `agent/src/low_absorb/data_sources/**` | 多源行情、健康检查、fallback、熔断、数据质量模型 |
| `agent/src/low_absorb/cost_chain/**` | 成本链半自动采集、候选版本、审核、审计、回滚 |
| `agent/src/low_absorb/backtest/**` | 日线级真实回测任务、数据集、指标 |
| `agent/src/low_absorb/deployment/**` | 本机生产配置校验、备份恢复 |
| `agent/src/low_absorb/api/**` | Low Absorb 相关 API |
| `agent/src/low_absorb/config.py` | 数据源、回测、飞书、部署配置 |
| `agent/src/low_absorb/data_provider.py` | 与现有 MarketDataProvider 契约兼容 |
| `agent/src/low_absorb/a_stock_provider.py` | A 股真实数据适配 |
| `agent/src/low_absorb/fallback_provider.py` | dev/test fixture fallback 规范 |
| `agent/src/low_absorb/global_market_provider.py` | 全球与美股行情输入 |
| `agent/src/low_absorb/sentiment.py` | 市场情绪消费数据质量状态 |
| `agent/src/low_absorb/scanner.py` | 数据异常时阻断信号与计划生成 |
| `agent/src/low_absorb/chain_matrix.py` | 消费已审核成本链版本 |
| `agent/src/low_absorb/notifier.py` | 飞书发送策略、幂等、审计 |
| `agent/src/low_absorb/storage.py` | 持久化新增状态 |
| `agent/src/low_absorb/models.py` | 共享 Pydantic 模型 |
| `agent/tests/test_low_absorb*.py` | Low Absorb 后端测试 |
| `docs/deployment/low_absorb_production.md` | Windows 本机生产部署文档 |
| `specs/active/002-low-absorb-production-readiness/implementation.yaml` | Claude Code 实现前复述 |
| `specs/active/002-low-absorb-production-readiness/delivery.yaml` | Claude Code 交付证据 |

## 6. 全局禁止修改范围

| 路径或范围 | 原因 |
|------------|------|
| `frontend/src/**` | UI 中文化、视觉优化和页面改动独立立项；本阶段默认不改前端 |
| `package.json` | 未授权依赖或脚本变更 |
| `frontend/package.json` | 未授权前端依赖或脚本变更 |
| `pyproject.toml` | 新增 Python 依赖必须先确认 |
| `requirements*.txt` | 新增 Python 依赖必须先确认 |
| `uv.lock` | 依赖锁文件变更必须先确认 |
| `.github/**` | 本任务不修改 CI 或版本流程 |
| `specs/constitution.md` | 项目宪法不得修改 |
| `agent/ai_low_absorb/**` | Low Absorb 模块必须使用 `agent/src/low_absorb` |

---

## 7. 停止条件

Claude Code 遇到以下情况必须停止实现，并在 `implementation.yaml` 或 `delivery.yaml` 中记录：

- 需要修改允许范围之外的文件。
- 需要修改 `frontend/src/**` 或引入 UI 中文化/视觉优化。
- 需要新增依赖或修改项目配置。
- 真实行情依赖不可用，且无法用现有依赖或受控 mock 完成测试。
- 接口契约与现有实现冲突。
- 发现需求与金融安全边界冲突。
- 指定测试或构建命令无法运行且无法判断风险。
- 发现真实券商下单、自动交易、一键交易或券商执行 API 风险。
- 任何密钥、Webhook、Token 可能完整暴露到前端、日志、测试快照或 API 响应。

---

## 8. 任务单元

### Task 1：Batch A 多源行情稳定性

- **依赖**：无
- **可并行**：否
- **目标**：
  - 建立真实行情多源编排、数据质量模型、fallback、熔断、冲突检测和 fail-closed。
  - 让市场情绪、扫描和交易计划生成消费数据质量状态。

#### 允许修改文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `agent/src/low_absorb/data_sources/**` | 新建 | 数据源模型、编排器、适配器、健康检查 |
| `agent/src/low_absorb/config.py` | 修改 | 新鲜度、冲突阈值、fallback、数据源优先级 |
| `agent/src/low_absorb/data_provider.py` | 修改 | 兼容现有 provider 契约 |
| `agent/src/low_absorb/a_stock_provider.py` | 修改 | A 股真实 provider 适配 |
| `agent/src/low_absorb/fallback_provider.py` | 修改 | fixture fallback 显式标记 |
| `agent/src/low_absorb/global_market_provider.py` | 修改 | 全球与美股行情输入 |
| `agent/src/low_absorb/sentiment.py` | 修改 | 数据异常时观察或拦截 |
| `agent/src/low_absorb/scanner.py` | 修改 | 数据异常时不生成新信号/计划 |
| `agent/src/low_absorb/models.py` | 修改 | 数据源共享模型 |
| `agent/src/low_absorb/api/**` | 修改 | 数据源状态 API |
| `agent/tests/test_low_absorb_data_sources.py` | 新建/修改 | 多源数据测试 |
| `agent/tests/test_low_absorb_sentiment.py` | 修改 | 情绪 fail-closed 测试 |
| `agent/tests/test_low_absorb_scanner.py` | 修改 | 扫描 fail-closed 测试 |
| `agent/tests/test_low_absorb_api_contract.py` | 修改 | 数据源 API 契约测试 |

#### 禁止修改文件

| 文件路径或范围 | 原因 |
|----------------|------|
| `frontend/src/**` | UI 独立立项 |
| `pyproject.toml`、`requirements*.txt`、`uv.lock` | 依赖变更需先确认 |

#### 实现要求

- A 股数据源优先级必须符合 `a-stock-data` 原则：`mootdx` 和腾讯优先，东方财富仅独有数据或必要备份且限流。
- 每次数据获取记录来源、时间、新鲜度、字段完整性、fallback、冲突和失败原因。
- 多源关键字段冲突超过阈值时返回 conflict，不得静默任选一个来源。
- 生产模式多源全部失败时返回 fail-closed，不得 fixture 伪装真实数据。
- 数据异常时，情绪许可不得返回“允许”，扫描不得生成新信号或交易计划。

#### 不得实现

- 不新增依赖；如必须新增，停止并请求确认。
- 不从前端直接调用外部行情源。
- 不用 AI 生成行情数据。

#### 必须新增或更新的测试

| 测试文件 | 覆盖内容 |
|----------|----------|
| `agent/tests/test_low_absorb_data_sources.py` | 单源成功、fallback、冲突、过期、全部失败、生产禁止 fixture |
| `agent/tests/test_low_absorb_sentiment.py` | 全球/A 股行情缺失时观察或拦截 |
| `agent/tests/test_low_absorb_scanner.py` | 数据 fail-closed 时不生成新信号/计划 |
| `agent/tests/test_low_absorb_api_contract.py` | 数据源状态 API 响应格式 |

#### 验证命令

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_data_sources.py agent/tests/test_low_absorb_sentiment.py agent/tests/test_low_absorb_scanner.py -q
```

#### 验收标准

- [ ] 多源 fallback、冲突、过期和全部失败均有测试。
- [ ] 生产模式不使用 fixture fallback 伪装真实数据。
- [ ] scanner 和 sentiment 均消费数据质量状态并 fail-closed。

#### 回滚边界

- 只回滚本任务允许修改文件。

---

### Task 2：Batch B 成本链半自动更新

- **依赖**：Task 1
- **可并行**：否
- **目标**：
  - 建立英伟达 AI 服务器成本链候选版本、人工审核、生效、驳回、回滚和审计流程。
  - 保证未审核或低置信度数据不影响信号排序。

#### 允许修改文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `agent/src/low_absorb/cost_chain/**` | 新建 | 成本链来源、采集、审核、审计 |
| `agent/src/low_absorb/chain_matrix.py` | 修改 | 只消费 ACTIVE 成本链版本 |
| `agent/src/low_absorb/storage.py` | 修改 | 持久化候选版本和审计记录 |
| `agent/src/low_absorb/models.py` | 修改 | 成本链候选与审计模型 |
| `agent/src/low_absorb/api/chain.py` | 修改 | 更新、审核、驳回、回滚、审计 API |
| `agent/tests/test_low_absorb_chain_matrix.py` | 修改 | 排序与低置信度规则 |
| `agent/tests/test_low_absorb_chain_api.py` | 修改 | 成本链 API 测试 |
| `agent/tests/test_low_absorb_storage.py` | 修改 | 成本链持久化测试 |

#### 禁止修改文件

| 文件路径或范围 | 原因 |
|----------------|------|
| `frontend/src/**` | UI 独立立项 |
| `pyproject.toml`、`requirements*.txt`、`uv.lock` | 依赖变更需先确认 |

#### 实现要求

- 半自动采集只生成 `REVIEW_PENDING` 候选版本。
- `APPROVED` 后才能成为 `ACTIVE` 并被 `chain_matrix` 消费。
- `REJECTED` 不得影响当前有效版本。
- `ROLLED_BACK` 必须恢复到上一有效版本或指定有效版本。
- 审计记录必须包含来源、差异、动作、操作者或任务来源、时间。

#### 不得实现

- 不让自动采集结果直接影响交易排序。
- 不用 AI 生成成本权重或成本表。
- 不覆盖内置版本的原始数据。

#### 必须新增或更新的测试

| 测试文件 | 覆盖内容 |
|----------|----------|
| `agent/tests/test_low_absorb_chain_matrix.py` | ACTIVE 版本消费、低置信度不影响排序 |
| `agent/tests/test_low_absorb_chain_api.py` | run、approve、reject、rollback、audit |
| `agent/tests/test_low_absorb_storage.py` | 候选版本、审核状态、审计持久化 |

#### 验证命令

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_chain_matrix.py agent/tests/test_low_absorb_chain_api.py agent/tests/test_low_absorb_storage.py -q
```

#### 验收标准

- [ ] 未审核候选版本不影响信号排序。
- [ ] 审核、驳回、回滚和审计均可通过 API 验证。
- [ ] 成本链更新失败时保留上一有效版本。

#### 回滚边界

- 只回滚本任务允许修改文件。

---

### Task 3：Batch C 日线级真实回测

- **依赖**：Task 1、Task 2
- **可并行**：否
- **目标**：
  - 接入日线级真实回测引擎。
  - 输出信号漏斗、计划数量、风险指标、分支归因和限制说明。

#### 允许修改文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `agent/src/low_absorb/backtest/**` | 新建 | 日线级回测模型、数据集、引擎、指标 |
| `agent/src/low_absorb/api/backtest.py` | 修改 | 回测任务 API |
| `agent/src/low_absorb/data_provider.py` | 修改 | 历史日线数据装载 |
| `agent/src/low_absorb/scanner.py` | 修改 | 复用策略漏斗 |
| `agent/src/low_absorb/trade_plan.py` | 修改 | 生成研究型计划样本 |
| `agent/src/low_absorb/risk.py` | 修改 | 回测 R 风险指标 |
| `agent/src/low_absorb/storage.py` | 修改 | 回测任务和结果持久化 |
| `agent/src/low_absorb/models.py` | 修改 | 回测请求、任务、结果模型 |
| `agent/tests/test_low_absorb_backtest.py` | 修改 | 日线回测测试 |
| `agent/tests/test_low_absorb_api_contract.py` | 修改 | 回测 API 契约测试 |

#### 禁止修改文件

| 文件路径或范围 | 原因 |
|----------------|------|
| `frontend/src/**` | UI 独立立项 |
| `pyproject.toml`、`requirements*.txt`、`uv.lock` | 依赖变更需先确认 |

#### 实现要求

- 第一阶段只支持日线级，不实现分钟级 14:45、09:30-10:00 或 10:00 监督回测。
- 回测输入必须固定日期范围、股票池、参数快照、成本链版本、数据源版本。
- 回测输出必须包含信号漏斗、计划数量、触发/失效原因、胜率、平均 R、最大回撤、样本数、分支归因、敏感性和限制说明。
- 回测结果不得写入真实人工成交或真实持仓。
- 缺失历史数据时任务必须失败并说明缺失区间。

#### 不得实现

- 不把系统建议等同真实成交。
- 不展示或返回收益承诺式结论。
- 不做分钟级回测。

#### 必须新增或更新的测试

| 测试文件 | 覆盖内容 |
|----------|----------|
| `agent/tests/test_low_absorb_backtest.py` | 成功、失败、缺失数据、可重复性、限制说明 |
| `agent/tests/test_low_absorb_api_contract.py` | 回测任务 API 响应格式 |

#### 验证命令

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_backtest.py agent/tests/test_low_absorb_api_contract.py -q
```

#### 验收标准

- [ ] 同一输入配置能得到可解释的一致结果。
- [ ] 缺失数据时任务失败并返回明确原因。
- [ ] 回测输出包含完整研究指标和限制说明。

#### 回滚边界

- 只回滚本任务允许修改文件。

---

### Task 4：Batch D 飞书真实联调

- **依赖**：Task 1、Task 2
- **可并行**：否
- **目标**：
  - 为推荐卡片、10:00 风控提醒、成交回填提醒、收盘复盘报告、测试卡片提供 mock/真实受控发送。
  - 补齐幂等键、Webhook 掩码和通知审计。

#### 允许修改文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `agent/src/low_absorb/notifier.py` | 修改 | Webhook 调用、真实发送开关、幂等 |
| `agent/src/low_absorb/api/settings.py` | 修改 | 飞书配置状态、测试通知入口 |
| `agent/src/low_absorb/api/reports.py` | 修改 | 复盘报告通知 |
| `agent/src/low_absorb/storage.py` | 修改 | 通知审计持久化 |
| `agent/src/low_absorb/models.py` | 修改 | 飞书发送策略和审计模型 |
| `agent/tests/test_low_absorb_notifier.py` | 修改 | 飞书 mock、幂等、掩码测试 |
| `agent/tests/test_low_absorb_reports.py` | 修改 | 复盘通知测试 |
| `agent/tests/test_low_absorb_feishu_integration.py` | 新建 | 真实联调 env guard 测试 |

#### 禁止修改文件

| 文件路径或范围 | 原因 |
|----------------|------|
| `frontend/src/**` | UI 独立立项 |
| `pyproject.toml`、`requirements*.txt`、`uv.lock` | 依赖变更需先确认 |

#### 实现要求

- 默认 `LOW_ABSORB_FEISHU_REAL_SEND=false`。
- 真实发送必须同时满足 Webhook 存在和真实发送开关开启。
- Webhook 不得完整回显到 API、日志、测试快照。
- 每类通知必须有幂等键和审计记录。
- 真实联调测试缺少环境变量时必须 skip。

#### 不得实现

- 不在默认测试中真实发送飞书。
- 不打印完整 Webhook。
- 不把通知按钮改成交易执行入口。

#### 必须新增或更新的测试

| 测试文件 | 覆盖内容 |
|----------|----------|
| `agent/tests/test_low_absorb_notifier.py` | mock、真实开关、幂等、防重复、Webhook 掩码 |
| `agent/tests/test_low_absorb_reports.py` | 复盘报告通知 |
| `agent/tests/test_low_absorb_feishu_integration.py` | 环境变量保护的真实联调 |

#### 验证命令

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_notifier.py agent/tests/test_low_absorb_reports.py agent/tests/test_low_absorb_feishu_integration.py -q
```

#### 验收标准

- [ ] 默认测试不真实发送飞书。
- [ ] 真实联调必须显式开启。
- [ ] 全类型通知均有幂等和审计。

#### 回滚边界

- 只回滚本任务允许修改文件。

---

### Task 5：Batch E 本机生产部署配置

- **依赖**：Task 1、Task 2、Task 3、Task 4
- **可并行**：否
- **目标**：
  - 提供 Windows 本机长期运行部署方案。
  - 补齐 health/readiness/liveness、生产配置校验、备份恢复和回滚说明。

#### 允许修改文件

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `agent/src/low_absorb/deployment/**` | 新建 | 配置校验、备份恢复 |
| `agent/src/low_absorb/api/health.py` | 新建 | 健康检查 API |
| `agent/src/low_absorb/api/__init__.py` | 修改 | 注册健康检查路由 |
| `agent/src/low_absorb/config.py` | 修改 | 生产环境变量 |
| `agent/src/low_absorb/storage.py` | 修改 | 备份恢复支持 |
| `docs/deployment/low_absorb_production.md` | 新建 | Windows 本机部署说明 |
| `agent/tests/test_low_absorb_api_contract.py` | 修改 | 健康 API 契约 |
| `agent/tests/test_low_absorb_main_api_integration.py` | 修改 | 主应用路由集成 |
| `agent/tests/test_low_absorb_storage.py` | 修改 | 备份恢复测试 |

#### 禁止修改文件

| 文件路径或范围 | 原因 |
|----------------|------|
| `frontend/src/**` | UI 独立立项 |
| `pyproject.toml`、`requirements*.txt`、`uv.lock` | 依赖变更需先确认 |

#### 实现要求

- readiness 必须检查存储路径、生产环境变量、真实数据源、fixture fallback、飞书配置、成本链有效版本。
- 生产模式误开启 fixture fallback 时 readiness 必须失败。
- 部署文档必须包含环境变量、启动、停止、日志查看、备份、恢复、回滚。
- 生产配置不得硬编码个人路径、真实账号、密钥或 Webhook。

#### 不得实现

- 不修改 CI。
- 不创建 Windows 服务安装脚本，除非后续单独授权。
- 不硬编码本机私有路径作为生产默认值。

#### 必须新增或更新的测试

| 测试文件 | 覆盖内容 |
|----------|----------|
| `agent/tests/test_low_absorb_api_contract.py` | health/readiness/liveness API |
| `agent/tests/test_low_absorb_main_api_integration.py` | 主应用包含健康路由 |
| `agent/tests/test_low_absorb_storage.py` | 备份恢复 |

#### 验证命令

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_api_contract.py agent/tests/test_low_absorb_main_api_integration.py agent/tests/test_low_absorb_storage.py -q
```

#### 验收标准

- [ ] readiness 能明确报告缺失项。
- [ ] 生产 fixture fallback 误开启时 readiness 失败。
- [ ] 部署文档可指导 Windows 本机长期运行、备份恢复和回滚。

#### 回滚边界

- 只回滚本任务允许修改文件。

---

## 9. 全局验收

完成所有任务后，确认：

- [ ] 对照 `spec.md` FR-1 至 FR-5 逐项核对通过。
- [ ] 对照需求追踪矩阵逐项提供证据。
- [ ] Claude Code 已生成 `delivery.yaml`，包含自我审查、修复记录、验证结果和风险检查。
- [ ] 后端 Low Absorb 测试通过：

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests -k low_absorb -q
```

- [ ] 前端测试通过，证明未破坏现有页面：

```powershell
cd frontend
npm.cmd run test:run
```

- [ ] 前端构建通过：

```powershell
cd frontend
npm.cmd run build
```

- [ ] 金融安全边界扫描完成，任何命中都必须在 `delivery.yaml` 解释上下文：

```powershell
rg -n "券商|自动交易|一键交易|买入|卖出|下单" agent/src frontend/src
```

- [ ] 无任务外文件改动，或已在 `delivery.yaml` 中解释并获得 Codex 确认。
- [ ] 无密钥、Webhook、Token 完整暴露。
- [ ] 无真实券商下单、自动交易、自动委托、券商交易执行 API 或一键交易。
- [ ] 本阶段未实现页面中文化、视觉优化或 UI 重构。
