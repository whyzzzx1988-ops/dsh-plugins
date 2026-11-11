# 可观测流程

怎么开始（识别应用）和怎么收尾（汇总成结论）。

## 识别应用

任何云查询前，先从本地部署状态识别目标应用。

1. 在当前项目目录查找 `.qianwenai-deploy`。若不存在，提示用户 `cd` 进入已部署项目目录或提供项目
   路径——不要臆测资源。
   若状态文件含 `provisional: true`（部署未跑完，缺 `outputs` / `service_name`），说明部署未完成，
   提示用户先完成部署再观测，不要继续云查询。
2. 解析 JSON 状态文件，提取：
   - `region_id`、`stack_id`、`topology`、`app_type`、`nginx_mode`、`app_port`
   - `service_name`（服务名，用于服务/日志检查；缺失时回退 `qianwenai-app`）
   - `outputs.public_ip`、`outputs.ecs_instance_ids[]`、`outputs.security_group_id`、
     `outputs.eip_allocation_id`
   - RDS（存在时）：`outputs.db_instance_id`、`outputs.db_connection_address`、
     `outputs.db_port`、`outputs.db_account`、`db_engine`
   - `created_at`、`updated_at`
3. 判定拓扑：`single`（仅 ECS）或 ECS + RDS（`db_instance_id` 非空）。
4. 校验地域和资源 ID 非空。缺失关键 ID → 将对应层标记为 `unknown` 并说明原因。
5. 若同级存在 `operate_audit.jsonl`，读取最后一行，取其 `time` / `action` / `verification`，
   作为「最近一次运维动作」上下文——把本次观测与最近的恢复关联。文件不存在则跳过。
6. 若同级存在 `app_timeline.jsonl`，读取末尾数行，作为应用近期变更上下文（部署 / 热更 / 历次
   评分 / 运维动作），把本次观测对上最近发生的事。文件不存在则跳过。

只读 `.qianwenai-deploy`。**绝不**读取 `.qianwenai-deploy.local`（含密码）。
`current_artifact_urls` 是签名 URL——不要打印。

| 字段 | 用于 |
|------|------|
| `region_id` | 每条云查询（`--region`） |
| `outputs.ecs_instance_ids` | ECS 状态/指标与成本（匹配账号账单中的行） |
| `outputs.public_ip` | 应用公网探活 |
| `outputs.security_group_id` | 安全组暴露面 / 入方向规则检查 |
| `outputs.eip_allocation_id` | EIP 状态与带宽 |
| `outputs.db_instance_id` | RDS 检查与成本 |
| `app_type` / `nginx_mode` / `app_port` | 应用服务检查 |
| `service_name` | systemd 服务 / 日志文件名（回退 `qianwenai-app`） |

## 汇总成结论

把各层信号汇聚成一个应用级结论。至少识别以下模式：

### 判定硬约束

- 探活只证明入口可达，不单独作为健康结论。健康类结论必须同时带时间范围内的云监控 CPU/内存
  数据点，与探活取最严——任一为坏即不报 `healthy`。
- 每次健康类提问都重新拉最新数据点得出结论，不复用上一次检查的结论；报告的数据时间即该结论的
  有效边界。

| 模式 | 信号 |
|------|------|
| 全部正常 | 应用可达、ECS Running 且指标正常、RDS（如有）正常 |
| ECS 未运行 / 应用服务退出 | ECS Stopped，或 `<service_name>` inactive；公网探活失败 |
| ECS 持续高负载 | 时间范围内 CPU 持续偏高；响应时间上升 |
| 应用无法连接 RDS | 应用日志出现 DB 超时/拒绝/认证失败；RDS 可达但应用连不上 |
| RDS 接近瓶颈 | 连接数接近上限，或空间/IOPS 压力 |
| 慢 SQL 导致变慢 | 慢 SQL、行锁等待或全表扫描与响应时间上升相关 |
| 部分数据缺失 | 某层因权限或采集条件为 `unknown` |

先给单一总体结论，再按层给证据。整个应用取最坏贡献状态
（`unavailable` > `degraded` > `unknown` > `healthy`），但仍报告每层各自状态。存在故障
（而非仅 `unknown`）时，提供下一步：通过 `qianwenai-operate` 进入故障诊断。

读到最近一次运维动作时，在结论里带一句关联，如「最近一次运维：2026-09-09 重启 <service_name>
（已恢复）」，让本次评分能对上最近的恢复。绝不回显审计中的密码或完整连接串。

## 给各层打分

给每层在其权重内打分，再相加成健康分与分级。

| 维度 | 满分（含 RDS） | 满分（无 RDS） |
|------|----------------|----------------|
| 应用 | 35 | 45 |
| ECS | 30 | 45 |
| RDS | 25 | — |
| 可用性 | 10 | 10 |

按状态和证据给每层打分：`healthy` 保留大部分权重，`degraded` 按风险大小酌情扣分，
`unavailable` 接近零分，`unknown` 计零分（说明无法测得）。无 RDS 时其权重移给应用和 ECS。

可用性维度汇总 ECS/RDS 运行状态、近期系统事件、EIP 状态与带宽、安全组暴露面。备份 / 快照缺失
和安全组收敛建议只作为风险与建议项，不计入分数。

`health_score` = 各层分数之和；分级严格随之（`>=90` A · `>=75` B · `>=60` C · `<60` D）。
一句话结论要与分数一致——低分绝不搭配「一切正常」的总结。

已知上一次 observe 结果（如运维恢复前的评分）时，可在报告里带上「上次 → 本次」的分数对照，
让恢复或劣化在分数上可见。

**成本从不计入分数。** 单独报告为实际账单（账期、总额、按产品拆分）加一段基于利用率的优化说明；
绝不预估花费。

## 追加应用档案

得出健康分后，向同级的 `app_timeline.jsonl` 追加一行 JSON（`event=observe`）。字段：`ts`(UTC)、
`skill: qianwenai-observe`、`event: observe`、`summary`（一行结论），并合并 `score` / `grade`，
有真实故障时再加 `fault_layer`：

```json
{"ts":"2026-08-03T16:20:00Z","skill":"qianwenai-observe","event":"observe","summary":"体检 87/100（B）——应用正常，关注 RDS 连接趋势","score":87,"grade":"B"}
```

只写脱敏后的只读结论，绝不写密码或连接串。
