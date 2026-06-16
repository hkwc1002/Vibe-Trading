# Low Absorb Windows 本机部署指南

> 本文档适用于 Low Absorb 模块在 Windows 本机长期运行的生产部署。
> 当前版本：Batch E — 本机生产部署配置

---

## 目录

1. [环境变量](#1-环境变量)
2. [启动与停止](#2-启动与停止)
3. [日志](#3-日志)
4. [健康检查](#4-健康检查)
5. [备份与恢复](#5-备份与恢复)
6. [回滚](#6-回滚)
7. [故障排查](#7-故障排查)

---

## 1. 环境变量

Low Absorb 通过环境变量控制运行时行为。以下是在 Windows **PowerShell** 中设置的方式：

```powershell
# 存储路径（默认：agent/.ui_runtime/low_absorb/state.json）
$env:LOW_ABSORB_STORAGE_PATH = "C:\low_absorb_data\state.json"

# 飞书 Webhook（真实发送时必须配置）
$env:LOW_ABSORB_FEISHU_WEBHOOK = "https://open.feishu.cn/webhook/your-token"

# 飞书真实发送开关（默认 false；设为 true 后才会调用真实 Webhook）
$env:LOW_ABSORB_FEISHU_REAL_SEND = "false"

# API 认证（非本机访问时必须设置）
$env:API_AUTH_KEY = "your-secret-key"

# 数据生产模式（true 时禁止 fixture fallback，所有数据源必须真实可用）
$env:LOW_ABSORB_DATA_PRODUCTION_MODE = "false"

# 日志级别（DEBUG / INFO / WARNING / ERROR）
$env:LOW_ABSORB_LOG_LEVEL = "INFO"
```

### 环境变量汇总

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LOW_ABSORB_STORAGE_PATH` | `agent/.ui_runtime/low_absorb/state.json` | 持久化状态文件路径 |
| `LOW_ABSORB_FEISHU_WEBHOOK` | 无 | 飞书机器人 Webhook URL |
| `LOW_ABSORB_FEISHU_REAL_SEND` | `false` | 是否真实发送飞书通知 |
| `API_AUTH_KEY` | 无 | 非本机 API 访问认证密钥 |
| `LOW_ABSORB_DATA_PRODUCTION_MODE` | `false` | 数据生产模式（启用时 fixture fallback 被禁止） |
| `LOW_ABSORB_LOG_LEVEL` | `INFO` | 日志级别 |

> **安全说明：** 不要将 `LOW_ABSORB_FEISHU_WEBHOOK` 和 `API_AUTH_KEY` 硬编码在启动脚本或配置文件中。应在 PowerShell 会话、系统环境变量或密钥管理器中设置。

### 启动脚本模板

创建一个 `start_low_absorb.ps1`：

```powershell
# start_low_absorb.ps1
$env:LOW_ABSORB_FEISHU_WEBHOOK = "https://open.feishu.cn/webhook/your-token"
$env:API_AUTH_KEY = "your-secret-key"
$env:LOW_ABSORB_DATA_PRODUCTION_MODE = "true"
$env:LOW_ABSORB_LOG_LEVEL = "INFO"

# 进入项目目录并启动
cd C:\path\to\vibe-trading
python agent/api_server.py
```

---

## 2. 启动与停止

### 启动

```powershell
cd C:\path\to\vibe-trading
python agent/api_server.py
```

启动后服务默认监听 `http://localhost:8000`（端口由 FastAPI/Uvicorn 决定，可在 `api_server.py` 中调整）。

### 停止

- **Ctrl + C** 终止前台进程。
- 如已在后台运行，使用 `taskkill`：

```powershell
# 查找 Python 进程
tasklist | findstr python

# 终止指定进程
taskkill /PID <PID> /F
```

---

## 3. 日志

Low Absorb 使用 `loguru` 输出结构化日志。默认输出到控制台。

### 日志级别

通过 `$env:LOW_ABSORB_LOG_LEVEL` 控制：

- `DEBUG`：详细的调试信息，用于问题排查
- `INFO`：常规运行信息（默认）
- `WARNING`：仅警告和错误
- `ERROR`：仅错误

### 日志保存到文件

在启动脚本中添加 loguru 配置或重定向输出：

```powershell
# 输出重定向到文件
python agent/api_server.py > low_absorb_$(Get-Date -Format "yyyyMMdd").log 2>&1
```

---

## 4. 健康检查

Low Absorb 提供两个健康检查端点，均继承 API 路由认证。

### Liveness（存活检查）

```http
GET /low-absorb/health/liveness
```

正常响应：
```json
{"status": "alive"}
```

用于负载均衡器或进程管理器的基本健康探测。

### Readiness（就绪检查）

```http
GET /low-absorb/health/readiness
```

通过响应：
```json
{"ready": true, "failures": []}
```

失败响应（示例）：
```json
{
  "ready": false,
  "failures": [
    {"name": "storage", "ok": false, "detail": "storage_not_writable"},
    {"name": "cost_chain", "ok": false, "detail": "no_active_version"}
  ]
}
```

检查项：

| 检查项 (`name`) | 通过 (`ok=true`) | 失败 (`ok=false`) |
|-----------|-----------|------------|
| `storage` | `"ok"` | `"storage_not_writable"` |
| `api_auth_key` | `"configured"` | `"missing"` |
| `fixture_fallback` | `"ok"` | `"fixture_fallback_forbidden"` |
| `cost_chain` | `"ok"` | `"no_active_version"` |
| `feishu` | `"configured"` | `"missing"` |

> **安全说明：** 所有检查项仅返回固定摘要字符串，不暴露路径、密钥、Token 或 Webhook 的完整值。

---

## 5. 备份与恢复

### 手动备份状态文件

```powershell
# 复制当前状态文件到备份目录
Copy-Item "C:\low_absorb_data\state.json" "C:\backups\state_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
```

### 使用备份工具（Python）

```python
from src.low_absorb.storage import JsonLowAbsorbStorage
from src.low_absorb.deployment.backup import export_state, load_state

storage = JsonLowAbsorbStorage()

# 备份：自动生成时间戳文件名，不覆盖已有文件
backup_path = export_state(storage, "C:\backups")
print(f"备份已保存至: {backup_path}")

# 恢复：自动校验 + 原子替换
load_state(storage, "C:\backups\low_absorb_state_20260616T143000.json")
```

### 备份文件命名

```
low_absorb_state_<YYYYMMDDTHHMMSS>.json
```

如果时间戳相同，自动追加 `_N` 后缀（`low_absorb_state_20260616T143000_1.json`）。

### 恢复流程

1. 备份文件会经过完整 Pydantic 校验（每条记录 `model_validate`）。
2. 校验通过后，系统自动为当前状态创建安全备份（`.state_pre_restore_<timestamp>`）。
3. 使用临时文件 + 原子替换写入新状态。
4. 校验失败或写入失败时，当前状态**不受影响**。

---

## 6. 回滚

### 回滚到上一个备份

1. 确认备份文件存在：

```powershell
dir C:\backups\low_absorb_state_*.json
```

2. 通过 Python 恢复：

```python
from src.low_absorb.storage import JsonLowAbsorbStorage
from src.low_absorb.deployment.backup import load_state

storage = JsonLowAbsorbStorage()
load_state(storage, "C:\backups\low_absorb_state_20260615T090000.json")
```

3. 重启服务。

### 回滚到自动安全备份

每次 `load_state` 自动创建的 `.state_pre_restore_<timestamp>` 文件在 `state.json` 同级目录中。手动恢复：

```powershell
Copy-Item ".state_pre_restore_20260616T150000" "state.json"
```

---

## 7. 故障排查

### 服务无法启动

1. 检查 Python 版本 >= 3.11：
   ```powershell
   python --version
   ```
2. 检查依赖已安装：
   ```powershell
   pip install -r requirements.txt
   ```
3. 检查端口是否被占用：
   ```powershell
   netstat -ano | findstr :8000
   ```
4. 查看日志输出寻找错误信息。

### Readiness 检查失败

| 失败原因 | 解决 |
|---------|------|
| `storage_not_writable` | 检查 `LOW_ABSORB_STORAGE_PATH` 指向的目录是否存在且可写 |
| `api_auth_key: missing` | 设置 `API_AUTH_KEY` 环境变量（本机开发可忽略） |
| `fixture_fallback_forbidden` | 生产模式下设置 `enable_fixture_fallback=false` 或关闭 `data_production_mode` |
| `no_active_version` | 通过成本链 API 审批一个候选版本使其成为 ACTIVE |
| `feishu: missing` | 配置 `LOW_ABSORB_FEISHU_WEBHOOK`（如不需要可忽略） |

### 数据丢失

1. 检查 `state.json` 所在目录是否存在备份文件（`.state_pre_restore_*`）。
2. 使用备份恢复流程回滚。
3. 如无自动备份，使用手动备份文件恢复。

---

## 附录：生产 checklist

- [ ] 设置 `API_AUTH_KEY` 环境变量
- [ ] 配置 `LOW_ABSORB_FEISHU_WEBHOOK`（如需要飞书通知）
- [ ] 确认 `LOW_ABSORB_FEISHU_REAL_SEND` 已按需设置（默认为 false）
- [ ] 确认成本链至少有一个 ACTIVE 版本
- [ ] 如启用 `data_production_mode=true`，关闭 `enable_fixture_fallback`
- [ ] 验证 `/low-absorb/health/readiness` 返回 `{"ready": true}`
- [ ] 创建定期备份策略（建议每日或每周备份 `state.json`）
- [ ] 确认启动脚本不硬编码密钥/Token/Webhook
