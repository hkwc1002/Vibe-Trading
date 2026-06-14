# 简要说明：001-low-absorb-next-optimization Low Absorb 后续优化

> 本文件用于人类快速理解任务背景。执行约束以 `contract.yaml` 为准。

## 基本信息

- 任务编号：001-low-absorb-next-optimization
- 风险等级：A
- 任务目录：`specs/active/001-low-absorb-next-optimization/`
- 创建人：Codex
- 创建时间：2026-06-14

## 一句话目标

- 在已完成的 Low Absorb 基线之上，继续补齐数据源、英伟达 AI 服务器成本链、交易建议解释、人工执行闭环、市场情绪、回测、复盘和持久化能力。

## 背景

- Low Absorb 已具备前端导航、基础工作台、部分后端 skeleton、数据源契约和初始设置能力。
- 后续任务涉及行情数据源、成本链模型、API 契约、策略排序、前端页面和金融安全边界，属于 A 类高风险任务。
- 本任务必须继续保持人工执行定位：系统只生成研究信号、交易计划、风控提醒、飞书通知和复盘材料，用户始终在国内券商 App 中手动完成真实交易。

## 非目标

- 不实现真实券商下单。
- 不接入券商交易执行 API。
- 不实现自动交易、一键交易或自动委托。
- 不新增依赖或修改项目配置，除非先停止并获得 Codex 与用户确认。
- 不由 Codex 修改源码；源码实现由 Claude Code CLI 完成。

## 关键风险

- 外部行情源不可用、过期或字段不稳定时，必须 fail-closed，不得生成交易建议。
- 英伟达 AI 服务器成本链包含估算数据，必须展示来源、来源类型、置信度和 as_of 日期，不得伪装为官方确定数据。
- 前端不得硬编码真实成本权重或策略规则。
- 页面和动作入口不得让用户误解为系统可以自动交易。

## 执行入口

- 结构化执行契约：`contract.yaml`
- A 类补充需求规格：`spec.md`
- A 类补充技术方案：`plan.md`
- A 类补充任务说明：`tasks.md`
- Claude Code 实现理解：`implementation.yaml`
- Claude Code 交付证据：`delivery.yaml`
- Codex 审查结论：`review.yaml`
