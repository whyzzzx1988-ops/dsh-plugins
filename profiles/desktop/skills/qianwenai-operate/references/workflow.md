# 运维流程

任何云调用前先识别应用，每个恢复动作后验证，并记录做了什么。

## 识别应用

1. 在项目目录查找 `.qianwenai-deploy`。若不存在，请用户 `cd` 进入已部署项目目录或提供路径——不要
   臆测资源。
   若状态文件含 `provisional: true`（部署未跑完，缺 `outputs` / `service_name`），说明部署未完成，
   提示用户先完成部署，不要继续诊断或处置。
2. 解析并提取：`region_id`、`stack_id`、`topology`、`app_type`、`nginx_mode`、`app_port`、
   `outputs.public_ip`、`outputs.ecs_instance_ids[]`、`outputs.security_group_id`、
   `outputs.eip_allocation_id`，以及 RDS 字段
   （`outputs.db_instance_id` / `db_connection_address` / `db_port` / `db_account`、`db_engine`）。
   还有 `service_name`（服务名，用于服务/日志检查；缺失时回退 `qianwenai-app`）。
3. 判定拓扑（仅 ECS 还是 ECS + RDS）。

只读 `.qianwenai-deploy`。**绝不**读取 `.qianwenai-deploy.local`（含密码）。不打印
`current_artifact_urls`（签名 URL）。

若存在 `observe_handoff.json`（来自 `qianwenai-observe` 的交接线索），可只读它取 `fault_layer` /
`symptoms` 作为诊断起点；该文件只含只读观测证据、不含密码，用作线索而非结论。

若存在 `app_timeline.jsonl`，可只读末尾数行了解近期变更（部署 / 热更 / 体检 / 历次运维），把当前
故障对上最近发生的事。文件只含脱敏只读信息、不含密码。

## 验证（每个恢复动作后）

1. **CLI/API 结果** — 恢复调用成功；记录其 RequestId。
2. **ECS 状态** — `DescribeInstances` 显示 `Running`。
3. **RDS 状态**（如有）— 实例运行中；连接池问题时连接数恢复正常。
4. **应用进程 / Nginx / 端口** — 只读云助手：`<service_name>` 和 `nginx` active，应用端口 / 80 在监听。
5. **入口** — `/healthz` 和首页返回正常。

返回且仅返回其一，附证据：

- **已恢复** — 入口正常且服务在跑。
- **部分恢复** — 部分层正常、其余仍失败（指明哪些）。
- **未恢复** — 入口仍失败。

**未恢复**或**部分恢复**时，返回失败步骤、CLI RequestId、当前状态和建议下一步。不要自动循环下一次
写操作——明确决定下一个单独动作。

## 重新评分（与 observe 闭环）

得到**已恢复**结论后，提议重跑 `qianwenai-observe`，并给出健康分的恢复前 → 恢复后对照（如「D 52 →
B 84」），让用户在分数上看到恢复效果。用户拒绝或 observe 不可用时跳过。

## 记录（审计）

每个恢复动作（写操作）记录为一条结构化条目。

| 字段 | 值 |
|------|-----|
| `time` | 动作时间戳（UTC） |
| `target` | 资源 id（ECS/RDS）+ 地域 |
| `action` | 执行的动作（如 StartInstance、restart <service_name>、reload nginx） |
| `confirmation` | 用户确认结果（confirmed / declined） |
| `request_id` | 写调用的 CLI RequestId |
| `verification` | 已恢复 / 部分恢复 / 未恢复 |

每条记录以一行 JSON 追加到项目目录下的 `operate_audit.jsonl`（与 `.qianwenai-deploy` 同级），
便于多次运维留痕，observe 也能引用最近一次动作。

同时向同级的 `app_timeline.jsonl` 追加一行 JSON（`event=operate`），让部署 / 热更 / 体检 / 运维在同一
档案里连续可查。字段：`ts`(UTC)、`skill: qianwenai-operate`、`event: operate`、`summary`（一行摘要），
并合并 `target` / `action` / `confirmation` / `request_id` / `verification`：

```json
{"ts":"2026-08-03T16:20:00Z","skill":"qianwenai-operate","event":"operate","summary":"重启 <service_name>，已恢复","target":"i-xxx@cn-hangzhou","action":"restart <service_name>","confirmation":"confirmed","request_id":"...","verification":"已恢复"}
```

审计记录和对话输出绝不含密码、Token 或完整连接凭据。写入前脱敏。被拒绝的确认也要记录，
`confirmation: declined` 且不执行任何写操作。
