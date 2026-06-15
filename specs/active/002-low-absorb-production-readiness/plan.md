# Low Absorb 生产化与外部联调技术方案

> 任务编号: `002-low-absorb-production-readiness`  
> 基于规范: `specs/active/002-low-absorb-production-readiness/spec.md`  
> 创建者: Codex  
> 状态: 待任务拆解  
> 风险等级: A 类高风险任务

---

## 1. 方案定位

本方案把 Low Absorb 从“本地可演示的人工交易 Copilot”推进到“真实数据可接入、异常可降级、联调可控制、本机可长期运行”的生产化阶段。

本阶段只处理非 UI 生产化主线：多源行情、成本链半自动采集审核、日线级真实回测、飞书真实联调和 Windows 本机长期运行部署。页面中文化和 UI 视觉优化后续独立立项。

系统仍然不是交易执行系统。所有真实交易继续由用户在国内券商 App 中手动完成。系统只提供研究信号、交易计划、飞书通知、人工成交记录、风控提醒、复盘报告和回测研究。

## 2. 总体架构

```text
外部数据源
  ├─ A 股多源行情：mootdx / 腾讯 / 百度 / 新浪 / 巨潮 / 同花顺 / 东方财富
  ├─ 全球与美股行情：Stooq / Yahoo 类公开源 / 其他受控公开源
  ├─ 成本链资料：公开资料 / 券商估算 / 产业研究 / 手动维护
  └─ 飞书 Webhook

后端 agent/src/low_absorb/
  ├─ data_sources/        多源 provider、健康检查、fallback、熔断、质量模型
  ├─ cost_chain/          成本链采集、候选版本、审核、审计、回滚
  ├─ backtest/            日线级回测任务、历史数据、指标归因
  ├─ notifications/       飞书真实联调、幂等、结果记录
  ├─ deployment/          健康检查、环境诊断、备份恢复
  ├─ storage.py           持久化仓储
  └─ api/                 FastAPI 路由
```

核心原则：

- 外部数据只允许后端访问。
- 前端不计算策略规则，不直接调用行情源。
- 外部副作用默认关闭，真实飞书联调必须显式启用。
- 任何数据异常都必须显式暴露，并在交易建议路径上 fail-closed。
- 生产模式不得用 fixture fallback 伪装真实数据。

## 3. 架构决策

### 3.1 A 股行情采用多源编排

- **选择**：新增多源编排层，统一管理 `mootdx`、腾讯、百度、新浪、巨潮、同花顺、东方财富等来源。
- **理由**：单一公开源容易受限流、字段变化、网络波动影响；Low Absorb 的交易许可和信号生成必须优先保障数据可靠性。
- **约束**：优先参考 `a-stock-data` skill 的数据源优先级；东方财富只用于独有数据或必要备份，必须串行限流、复用会话、记录风控状态。

### 3.2 使用统一数据质量模型

- **选择**：所有 provider 返回带来源、时间、新鲜度、字段完整性、fallback、冲突和失败原因的数据包。
- **理由**：策略层不能只看到“有数据/无数据”，还必须知道数据是否可靠。
- **结果**：扫描、情绪和回测都通过同一质量判断进入允许、观察或拦截状态。

### 3.3 成本链采用“采集 → 候选 → 审核 → 生效”

- **选择**：半自动采集只生成候选版本，人工审核后才能生效。
- **理由**：英伟达 AI 服务器成本权重通常来自估算和研报，不应未经审核直接改变交易建议。
- **结果**：低置信度数据可以展示为研究信息，但不得自动提升候选优先级。

### 3.4 回测先做日线级可重复研究

- **选择**：第一阶段只支持日线级真实回测。
- **理由**：分钟级 14:45、09:30-10:00 和 10:00 监督回测对数据完整性要求更高，适合后续单独增强。
- **结果**：本阶段重点验证漏斗、排序、R 风险和分支归因，不模拟真实盘中成交。

### 3.5 飞书真实联调必须环境变量保护

- **选择**：真实 Webhook 调用默认关闭，只在显式环境变量或设置允许时开启。
- **理由**：避免测试、开发或误操作造成真实通知轰炸。
- **结果**：默认测试走 mock；真实联调测试必须被环境变量 guard。

### 3.6 部署优先 Windows 本机长期运行

- **选择**：第一阶段按 Windows 本机长期运行设计。
- **理由**：贴合当前项目使用环境，部署复杂度低，可先验证真实数据和外部联调稳定性。
- **结果**：生产配置重点覆盖本机路径、环境变量、日志、健康检查、备份恢复和回滚。

## 4. 后端模块方案

### 4.1 多源行情与数据质量模块

建议新增或重构模块：

| 文件路径 | 操作 | 职责 |
|----------|------|------|
| `agent/src/low_absorb/data_sources/__init__.py` | 新建 | 数据源包导出 |
| `agent/src/low_absorb/data_sources/models.py` | 新建 | 数据源状态、尝试记录、冲突记录、质量评分模型 |
| `agent/src/low_absorb/data_sources/a_share_orchestrator.py` | 新建 | A 股多源编排、fallback、熔断、健康评分 |
| `agent/src/low_absorb/data_sources/a_share_adapters.py` | 新建 | mootdx、腾讯、百度、新浪、巨潮、同花顺、东方财富适配器 |
| `agent/src/low_absorb/data_sources/global_provider.py` | 新建或改造 | 全球与美股行情 provider |
| `agent/src/low_absorb/data_sources/health.py` | 新建 | 健康检查、熔断冷却、来源可用性 |
| `agent/src/low_absorb/data_provider.py` | 修改 | 与既有 `MarketDataProvider` 契约兼容 |
| `agent/src/low_absorb/config.py` | 修改 | 数据源优先级、新鲜度、冲突阈值、生产 fallback 开关 |

数据源优先级：

1. `mootdx`：K 线、盘口、逐笔、财务快照、F10。
2. 腾讯财经：实时价格、涨跌幅、估值、市值、换手率、指数、ETF。
3. 百度股市通 / 新浪 / 巨潮 / 同花顺：K 线、财报、公告、热点、题材补充。
4. 东方财富：行业板块、资金流、龙虎榜、解禁、研报、个股新闻等独有数据；必须限流。

关键规则：

- 单源失败后可尝试同等级或下一等级来源。
- 短时间连续失败的来源进入熔断冷却。
- 多源关键字段冲突超过阈值时，返回冲突状态而不是任选其一。
- 生产模式下多源全部失败，返回失败状态，不允许 fixture 伪装真实数据。
- dev/test 可使用 fixture fallback，但响应必须标记 `data_source="fixture_fallback"`。
- 若实现需要新增依赖，Claude Code 必须停止并请求更新契约。

### 4.2 成本链半自动采集审核模块

建议新增或重构模块：

| 文件路径 | 操作 | 职责 |
|----------|------|------|
| `agent/src/low_absorb/cost_chain/sources.py` | 新建 | 公开资料、券商估算、产业研究、手动维护来源定义 |
| `agent/src/low_absorb/cost_chain/updater.py` | 新建 | 半自动采集、规范化、候选版本生成 |
| `agent/src/low_absorb/cost_chain/review.py` | 新建 | 待审核、生效、驳回、回滚流程 |
| `agent/src/low_absorb/cost_chain/audit.py` | 新建 | 变更前后差异和来源审计 |
| `agent/src/low_absorb/chain_matrix.py` | 修改 | 消费已生效版本，不直接消费未审核候选 |
| `agent/src/low_absorb/api/chain.py` | 修改 | 增加更新、审核、回滚和审计查询接口 |

成本链状态：

```text
DISCOVERED → NORMALIZED → REVIEW_PENDING → APPROVED → ACTIVE
                         ↘ REJECTED
ACTIVE → ROLLED_BACK
```

生效规则：

- 内置版本可读不可直接覆盖。
- `custom/manual` 可编辑并保留版本历史。
- 自动采集版本必须先进入 `REVIEW_PENDING`。
- `confidence=low` 的条目不得自动影响 `signal_weight`。
- 更新失败时保留上一有效版本。

### 4.3 日线级真实回测模块

建议新增模块：

| 文件路径 | 操作 | 职责 |
|----------|------|------|
| `agent/src/low_absorb/backtest/__init__.py` | 新建 | 回测包导出 |
| `agent/src/low_absorb/backtest/models.py` | 新建 | 回测请求、任务、结果、样本、指标模型 |
| `agent/src/low_absorb/backtest/engine.py` | 新建 | 日线级回测主引擎 |
| `agent/src/low_absorb/backtest/dataset.py` | 新建 | 历史行情与成本链快照装载 |
| `agent/src/low_absorb/backtest/metrics.py` | 新建 | 胜率、平均 R、最大回撤、归因、敏感性 |
| `agent/src/low_absorb/api/backtest.py` | 修改 | 从示例快照升级为真实任务接口 |

回测原则：

- 输入固定：日期范围、股票池、策略参数、成本链版本、数据源版本。
- 输出可复现：同一输入配置应产生一致结果或解释差异原因。
- 回测只生成研究结果，不写入真实人工成交或真实持仓。
- 人工成交假设必须与系统建议分离展示。
- 本阶段不实现分钟级盘中回测。

### 4.4 飞书真实联调模块

建议修改模块：

| 文件路径 | 操作 | 职责 |
|----------|------|------|
| `agent/src/low_absorb/notifier.py` | 修改 | Webhook 调用、幂等、错误归因、真实发送开关 |
| `agent/src/low_absorb/api/settings.py` | 修改 | 掩码配置、测试通知入口 |
| `agent/src/low_absorb/storage.py` | 修改 | 通知结果持久化 |
| `agent/tests/test_low_absorb_feishu_integration.py` | 新建 | 环境变量保护的真实联调测试 |

联调原则：

- 默认 `LOW_ABSORB_FEISHU_REAL_SEND=false`。
- 真实联调必须同时满足 Webhook 存在和真实发送开关开启。
- Webhook 永不完整回显。
- 通知结果必须记录幂等键、目标对象、通知类型、状态、错误、发送时间。
- 推荐卡片、10:00 风控提醒、成交回填提醒、复盘报告和测试卡片均应支持受控真实发送。

### 4.5 本机部署与生产配置模块

建议新增：

| 文件路径 | 操作 | 职责 |
|----------|------|------|
| `docs/deployment/low_absorb_production.md` | 新建 | Windows 本机部署、环境变量、启动停止、备份恢复 |
| `agent/src/low_absorb/api/health.py` | 新建 | 健康检查 API |
| `agent/src/low_absorb/deployment/config_check.py` | 新建 | 生产配置校验 |
| `agent/src/low_absorb/deployment/backup.py` | 新建 | JSON/SQLite 状态备份与恢复 |

生产环境变量建议：

| 变量名 | 用途 | 生产默认 |
|--------|------|----------|
| `LOW_ABSORB_ENV` | `dev/test/prod` | `prod` |
| `LOW_ABSORB_STORAGE_PATH` | 状态存储路径 | 必填 |
| `LOW_ABSORB_DATA_PROVIDER_MODE` | `real/fixture/auto` | `real` |
| `LOW_ABSORB_ENABLE_FIXTURE_FALLBACK` | 是否允许 fixture fallback | `false` |
| `LOW_ABSORB_MAX_DATA_STALENESS_SECONDS` | 数据新鲜度阈值 | 按市场场景配置 |
| `LOW_ABSORB_FEISHU_WEBHOOK` | 飞书 Webhook | 可选但需掩码 |
| `LOW_ABSORB_FEISHU_REAL_SEND` | 是否真实发送 | `false` |
| `LOW_ABSORB_LOG_LEVEL` | 日志级别 | `INFO` |
| `IWENCAI_API_KEY` | 可选语义搜索 Key | 未配置时禁用相关能力 |

## 5. 数据模型

### 5.1 数据源状态模型

```python
class DataSourceAttempt:
    source_id: str
    source_type: str
    started_at: datetime
    finished_at: datetime | None
    ok: bool
    latency_ms: int | None
    error_code: str | None
    error_message: str | None
    returned_rows: int | None

class DataConflict:
    field: str
    values_by_source: dict[str, object]
    tolerance: Decimal | None
    severity: str

class DataSourceHealth:
    source_id: str
    enabled: bool
    health_score: Decimal
    circuit_state: str  # CLOSED / OPEN / HALF_OPEN
    last_success_at: datetime | None
    last_failure_at: datetime | None
    cooldown_until: datetime | None
    consecutive_failures: int

class MultiSourceFetchResult:
    ok: bool
    selected_source: str | None
    fallback_used: bool
    attempts: list[DataSourceAttempt]
    conflicts: list[DataConflict]
    freshness_seconds: int | None
    data: object | None
    fail_closed_reason: str | None
```

### 5.2 成本链候选与审计模型

```python
class CostChainUpdateCandidate:
    candidate_id: str
    version: str
    source_type: str
    source_name: str
    as_of: date
    confidence: str
    components: list[CostChainComponent]
    diff_summary: list[str]
    status: str  # REVIEW_PENDING / APPROVED / REJECTED / ACTIVE / ROLLED_BACK
    created_at: datetime
    reviewed_at: datetime | None
    review_note: str | None

class CostChainAuditRecord:
    audit_id: str
    candidate_id: str
    action: str
    before_version: str | None
    after_version: str | None
    actor: str
    created_at: datetime
    note: str | None
```

### 5.3 回测模型

```python
class BacktestRunRequest:
    start_date: date
    end_date: date
    symbols: list[str] | None
    cost_chain_version: str
    config_snapshot_id: str | None
    include_manual_fill_assumption: bool

class BacktestRun:
    run_id: str
    status: str  # QUEUED / RUNNING / SUCCEEDED / FAILED
    request: BacktestRunRequest
    created_at: datetime
    finished_at: datetime | None
    error: str | None

class BacktestResult:
    run_id: str
    data_sources: list[str]
    sample_count: int
    signal_count: int
    plan_count: int
    win_rate: Decimal | None
    average_r: Decimal | None
    max_drawdown: Decimal | None
    branch_attribution: list[dict[str, object]]
    sensitivity: list[dict[str, object]]
    limitations: list[str]
```

### 5.4 飞书通知模型

```python
class FeishuSendPolicy:
    real_send_enabled: bool
    webhook_configured: bool
    masked_webhook: str | None

class FeishuNotificationAudit:
    notification_id: str
    notification_type: str
    target_id: str
    idempotency_key: str
    real_send: bool
    ok: bool
    error: str | None
    sent_at: datetime | None
```

## 6. API 契约

### 6.1 数据源诊断 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/low-absorb/data-sources/status` | 返回 A 股、全球行情、成本链、飞书配置健康状态 |
| POST | `/low-absorb/data-sources/check` | 手动触发数据源健康检查 |
| GET | `/low-absorb/data-sources/attempts` | 查询近期数据源尝试和失败原因 |

响应要点：

- 使用统一响应格式 `{ success, data, error }`。
- 不返回密钥、Token、完整 Webhook。
- 必须包含 `source_id`、`health_score`、`circuit_state`、`last_success_at`、`last_failure_at`。

### 6.2 成本链更新 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/low-absorb/chain/updates/run` | 触发成本链资料采集，生成候选版本 |
| GET | `/low-absorb/chain/updates` | 查询候选版本和审核状态 |
| POST | `/low-absorb/chain/updates/{candidate_id}/approve` | 审核通过候选版本 |
| POST | `/low-absorb/chain/updates/{candidate_id}/reject` | 驳回候选版本 |
| POST | `/low-absorb/chain/versions/{version}/rollback` | 回滚到指定有效版本 |
| GET | `/low-absorb/chain/audit` | 查询成本链变更审计 |

### 6.3 回测 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/low-absorb/backtest/runs` | 创建日线级真实回测任务 |
| GET | `/low-absorb/backtest/runs` | 查询回测任务列表 |
| GET | `/low-absorb/backtest/runs/{run_id}` | 查询任务状态和结果 |
| GET | `/low-absorb/backtest/runs/{run_id}/export` | 导出回测结果 |

回测 API 必须明确：

- 数据来源；
- 样本区间；
- 策略参数快照；
- 成本链版本；
- 人工成交假设；
- 结果限制。

### 6.4 飞书联调 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/low-absorb/notifications/status` | 查看飞书配置状态和掩码 Webhook |
| POST | `/low-absorb/notifications/test` | 发送测试卡片，默认 mock |
| GET | `/low-absorb/notifications/audit` | 查询通知审计记录 |

### 6.5 生产健康检查 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/low-absorb/health` | 返回 Low Absorb 模块健康状态 |
| GET | `/low-absorb/health/readiness` | 返回是否具备生产可用条件 |
| GET | `/low-absorb/health/liveness` | 返回进程存活状态 |

## 7. 状态流

### 7.1 行情数据获取状态流

```text
REQUESTED
  → SOURCE_SELECTED
  → FETCHING
  → VALIDATING
  → SUCCESS
  → STALE
  → CONFLICT
  → FALLBACK_USED
  → FAIL_CLOSED
```

处理规则：

- `SUCCESS` 才允许进入策略扫描。
- `FALLBACK_USED` 可进入策略扫描，但必须记录来源和原因；生产环境不得使用 fixture fallback。
- `STALE`、`CONFLICT`、`FAIL_CLOSED` 不允许生成新交易计划。

### 7.2 成本链更新状态流

```text
SCHEDULED → FETCHING → NORMALIZED → REVIEW_PENDING
                                     ├─ APPROVED → ACTIVE
                                     └─ REJECTED
ACTIVE → ROLLED_BACK
```

### 7.3 回测任务状态流

```text
QUEUED → RUNNING → SUCCEEDED
                 └→ FAILED
```

失败必须记录：

- 缺失的数据源；
- 缺失的交易日；
- 参数不合法原因；
- 成本链版本不可用原因。

### 7.4 飞书通知状态流

```text
CREATED → IDEMPOTENCY_CHECKED → MOCKED
                              └→ SENDING → SENT
                                          └→ FAILED
```

默认路径应为 `MOCKED`。只有显式真实发送开关开启时才进入 `SENDING`。

## 8. 错误处理与降级策略

| 场景 | 后端行为 | 前端或诊断入口行为 |
|------|----------|--------------------|
| 单一 A 股来源失败 | 尝试下一来源，记录 attempt | 展示 fallback 来源和原因 |
| 全部 A 股来源失败 | 返回 fail-closed | 交易许可显示拦截 |
| 多源关键字段冲突 | 返回 conflict 状态 | 展示冲突来源和值 |
| 全球行情缺失 | 情绪返回观察或拦截 | 显示全球风险数据缺失 |
| 成本链更新失败 | 保留上一有效版本 | 展示更新失败原因 |
| 成本链候选未审核 | 不影响排序 | 展示待审核状态 |
| 回测数据缺失 | 回测任务 failed | 展示缺失区间和来源 |
| 飞书未配置 | 返回 missing webhook | 显示配置缺失 |
| 真实飞书未开启 | 返回 mocked result | 显示模拟发送 |
| 生产配置缺失 | readiness 失败 | 展示缺失项 |

## 9. 部署方案

### 9.1 环境分层

| 环境 | 数据源 | fixture fallback | 飞书真实发送 | 用途 |
|------|--------|------------------|--------------|------|
| dev | auto | 可开启 | 默认关闭 | 本地开发 |
| test | fixture/mock | 可开启 | 必须关闭 | 自动测试 |
| prod | real | 默认关闭 | 显式开启 | Windows 本机长期运行 |

### 9.2 健康检查

`/low-absorb/health/readiness` 必须检查：

- 存储路径可读写；
- 生产环境变量完整；
- 真实数据源至少一个可用；
- fixture fallback 未在生产误开启；
- 飞书配置状态明确；
- 成本链存在有效版本；
- 最近一次数据源检查未全部失败。

### 9.3 备份与恢复

必须定义：

- 状态存储备份路径；
- 成本链版本备份；
- 通知审计备份；
- 回测结果备份；
- 恢复步骤；
- 回滚到上一有效成本链版本的方法。

## 10. 测试策略

### 10.1 后端测试

必须覆盖：

- 单数据源成功；
- 单数据源失败后 fallback；
- 多源全部失败 fail-closed；
- 多源字段冲突；
- 熔断冷却；
- 数据过期；
- 全球行情缺失降级；
- 成本链候选生成；
- 成本链审核、生效、驳回、回滚；
- 日线级回测任务创建、成功、失败；
- 回测结果可重复；
- 飞书 mock 发送；
- 飞书真实发送 env guard；
- 健康检查 readiness。

验证命令：

```powershell
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests -k low_absorb -q
```

### 10.2 前端相关测试

本阶段不做 UI 中文化或视觉优化，但如新增或调整诊断入口，必须覆盖：

- 数据源诊断渲染；
- 市场情绪数据缺失时不显示允许；
- 成本链候选版本和审核状态渲染；
- 回测任务状态切换；
- 飞书 Webhook 掩码；
- 禁用交易按钮文案不存在。

验证命令：

```powershell
cd frontend
npm.cmd run test:run
npm.cmd run build
```

### 10.3 外部联调测试

默认不运行真实外部副作用。真实联调必须使用环境变量显式开启：

```powershell
$env:LOW_ABSORB_FEISHU_REAL_SEND="true"
$env:LOW_ABSORB_FEISHU_WEBHOOK="<runtime secret>"
C:\Users\hx\AppData\Local\Programs\Python\Python312\python.exe -m pytest agent/tests/test_low_absorb_feishu_integration.py -q
```

如果缺少环境变量，测试必须 `skip`，不得失败或真实发送。

## 11. 安全边界

禁止：

- 真实券商下单；
- 自动买卖；
- 自动委托；
- 接入券商交易执行 API；
- 一键交易；
- 前端独立执行按钮文案：`买入`、`卖出`、`下单`、`自动交易`；
- 日志、API、测试快照中出现完整 Webhook、Token、Key。

允许：

- 生成研究信号；
- 生成交易计划；
- 推送飞书；
- 复制人工下单信息；
- 记录人工成交；
- 标记失效；
- 生成风控提醒；
- 记录卖出；
- 生成复盘报告。

## 12. 批次建议

后续 `tasks.md` 建议按以下批次拆解：

| 批次 | 范围 | 目标 |
|------|------|------|
| Batch A | 多源行情稳定性 | A 股多源编排、全球行情、健康检查、fail-closed |
| Batch B | 成本链半自动更新 | 候选版本、人工审核、审计、回滚 |
| Batch C | 日线级真实回测 | 历史数据、任务状态、结果归因、页面接入 |
| Batch D | 飞书真实联调 | env guard、幂等、审计、全类型测试卡片 |
| Batch E | 本机生产部署配置 | 健康检查、部署文档、备份恢复 |

每个批次都必须重新生成或更新 `implementation.yaml`。A 类批次需等待 Codex 确认后再实现。

## 13. 待确认事项

1. `mootdx`、`requests`、`pandas`、`stockstats` 等 `a-stock-data` 相关依赖是否已经在当前环境可用；若不可用，是否允许新增依赖需要单独授权。
2. 全球与美股行情第一阶段是否继续以 Stooq 或 Yahoo 类公开源为默认，是否允许新增 `yfinance` 需要单独确认。
3. 成本链半自动采集第一阶段是否允许手动上传 CSV/JSON 作为候选来源之一。
4. 日线级回测是否需要先限定股票池规模，避免本机长期运行时任务过慢。
5. Windows 本机长期运行是否需要后续再补 Windows 服务或计划任务说明。

## 14. 规格覆盖检查

| 规格项 | 本方案覆盖位置 |
|--------|----------------|
| FR-1 真实行情数据源稳定性 | 第 4.1、5.1、6.1、7.1、8、10.1 |
| FR-2 成本链半自动采集与人工审核 | 第 4.2、5.2、6.2、7.2、8、10.1 |
| FR-3 日线级真实回测 | 第 4.3、5.3、6.3、7.3、10.1 |
| FR-4 飞书全类型通知受控真实联调 | 第 4.4、5.4、6.4、7.4、10.3 |
| FR-5 Windows 本机长期运行部署 | 第 4.5、6.5、9 |
| 金融安全边界 | 第 11 |

## 15. 独立立项说明

页面中文化、品牌文案、首页文字、菜单文字、按钮文字、整体视觉体验和 UI 优化不属于本阶段生产化主线。该范围应后续单独创建 UI spec，并独立执行需求、方案、任务和审查流程。
