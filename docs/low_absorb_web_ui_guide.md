# AI Low Absorb Web UI 操作说明

## 1. 打开页面

启动前端开发服务后，在浏览器访问：

```text
http://localhost:5899/low-absorb
```

如果使用后端统一托管的生产构建，启动 API 服务后访问：

```text
http://localhost:8000/low-absorb
```

左侧导航进入 `AI Low Absorb` 分组，可看到：

- 交易工作台：`/low-absorb`
- 市场情绪：`/low-absorb/sentiment`
- AI 产业链：`/low-absorb/chain`
- 策略回测：`/low-absorb/backtest`
- 复盘报告：`/low-absorb/reports`
- 系统设置：`/low-absorb/settings`

## 2. 交易工作台

交易工作台是人工执行流程的主入口，顶部二级标签包括：

- 总览
- 今日信号
- 交易计划
- 人工持仓

当前前端仍使用本地 mock 数据展示页面结构；策略扫描、闸门、人工成交对账和 R 风险计算位于后端 `agent/src/low_absorb/`。

## 3. 市场情绪

市场情绪页展示：

- 综合情绪分
- A 股情绪
- 全球风险偏好
- AI 资金温度
- A 股情绪闸门
- 全球风险偏好表
- 社交账号监听 preview
- 新闻事件监听 preview
- 情绪规则 preview

此页不抓取真实社交媒体，不接外部新闻 API，仅保留未来接口结构。

## 4. AI 产业链

AI 产业链页展示：

- 最强分支
- 最弱分支
- 今日轮动方向
- 候选股票数
- AI 成本拓扑 placeholder
- 分支 RS 表
- 个股映射表
- 分支闸门规则

拓扑当前是可替换占位组件，没有新增 ReactFlow 依赖。

## 5. 策略回测

策略回测页顶部二级标签包括：

- 回测总览
- 策略参数
- 历史信号
- 参数敏感性
- 分支归因
- 改进建议

当前仅展示 mock fixture 和 API contract，不运行真实回测引擎。

## 6. 人工执行边界

AI Low Absorb 是人工执行交易助手，不是券商执行系统：

- 不接入券商 API。
- 不托管资金。
- 不生成真实订单。
- 不执行自动化交易。
- 所有真实交易动作都由用户在外部国内券商 App 中自行完成。

系统只负责信号、人工计划、飞书建议、人工成交回填、持仓风险监督、收盘复盘和回测改进。

## 7. 后端接口状态

Low Absorb 后端接口挂载在 `/low-absorb`，主要 contract 包括：

- `GET /low-absorb/snapshot`
- `POST /low-absorb/scan-tail`
- `GET /low-absorb/signals`
- `POST /low-absorb/signals/{signal_id}/notify`
- `GET /low-absorb/trade-plans`
- `POST /low-absorb/trade-plans/{plan_id}/send-feishu`
- `POST /low-absorb/fills`
- `GET /low-absorb/positions`
- `PATCH /low-absorb/positions/{position_id}`
- `POST /low-absorb/positions/{position_id}/close`
- `POST /low-absorb/supervise/morning`
- `POST /low-absorb/supervise/position/{position_id}`
- `GET /low-absorb/sentiment/snapshot`
- `GET /low-absorb/chain/snapshot`
- `GET /low-absorb/backtest/summary`
- `POST /low-absorb/backtest/run`
- `GET /low-absorb/settings`
- `PATCH /low-absorb/settings`
- `POST /low-absorb/notify/test`

当前存储为进程内存储，后续可替换为本地持久化或数据库。

## 8. 飞书与设置

飞书 webhook secret 不会返回给前端。设置接口只返回 `maskedWebhook`，例如：

```text
https://open.feishu.cn/open-apis/bot/v2/hook/****
```

飞书失败不会中断扫描、对账或风控监督流程。
