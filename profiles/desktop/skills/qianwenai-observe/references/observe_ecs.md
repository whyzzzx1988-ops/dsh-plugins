# 可观测·ECS

在所选时间范围（15 分钟 / 1 小时 / 24 小时，默认 1 小时）内评估 ECS 运行状态和性能。

## 状态

```bash
aliyun ecs DescribeInstances --RegionId <region> --InstanceIds '["<ecs-id>"]'
```

读取 `Status`（Running / Stopped / …）、实例规格、网络（公/私网 IP、带宽）。非 Running →
`unavailable`；汇报并说明公网探活会失败。

## CPU / 网络 / 磁盘指标

用云监控在时间范围内取时间序列：

```bash
aliyun cms DescribeMetricList --Namespace acs_ecs_dashboard --MetricName CPUUtilization \
  --Dimensions '[{"instanceId":"<ecs-id>"}]' --StartTime <start> --EndTime <end> --Period 60
```

对 `networkin` / `networkout` 和 `diskusage`（磁盘容量）重复。识别：

- 持续高 CPU（如均值偏高或反复接近 100%）→ `degraded`
- 网络异常 → `degraded`
- 磁盘容量风险（接近写满）→ `degraded`

## 内存——三层策略（结果中标注数据来源）

内存趋势来自云监控 agent（`memory_usedutilization`）。agent 由 observe 惰性确保，不在部署时安装。
按顺序执行：

1. **agent 指标（优先）** — 先探活；未装则用云端 API 安装并轮询就绪，再查内存序列：

   ```bash
   aliyun cms DescribeMonitoringAgentStatuses --InstanceIds <ecs-id>
   # 非 running 时用 API 安装（region 取自 <region>），随后轮询 DescribeMonitoringAgentStatuses 至 running：
   aliyun cms InstallMonitoringAgent --RegionId <region> --Force true --InstanceIds.1 <ecs-id>
   aliyun cms DescribeMetricList --Namespace acs_ecs_dashboard --MetricName memory_usedutilization \
     --Dimensions '[{"instanceId":"<ecs-id>"}]' --StartTime <start> --EndTime <end> --Period 60
   ```

   输出与 CPU 同口径的时间序列。数据来源：**云监控 agent（趋势）**。

2. **快照降级** — agent 装不上、异常，或指标返回 403 / 空数据时，用只读云助手读当前快照（`free -m`），
   标注**瞬时值、无趋势**。

3. **未知** — 两条路径都无法获得时，把内存标记为 `unknown` 并说明原因，绝不静默省略。

## 结果

ECS 层状态附证据：状态、CPU 均值/峰值、网络、磁盘余量、内存（含数据来源标注）。

报告的 `data_source`：全程用到 agent 趋势指标时为 `cloudmonitor`；任一指标走了快照降级
（如内存瞬时值）时为 `fallback`。
