# Aliyun CLI 踩坑速查

调用前对照本表，避免同类参数在不同产品间的形态/格式差异导致报错。均以真实报错信息为准。

## 参数形态

同类参数在不同产品间形态不同，用错会报 `InvalidParameter` / `MissingParam`：

- **`InstanceIds`** — ECS（`DescribeInstances`）要 JSON 数组串 `'["<ecs-id>"]'`；
  CMS（`DescribeMonitoringAgentStatuses`）要裸串 `<ecs-id>`。给 ECS 传裸串会报 `InvalidParameter`。
- **`RunCommand` 的实例参数** — 用 `.N` 重复形态 `--InstanceId.1 <ecs-id>`；裸 `--InstanceId`
  会报 `MissingParam.InstanceId`。
- **装云监控 agent** — 用 API `aliyun cms InstallMonitoringAgent --Force true --InstanceIds.1 <ecs-id>`
  （`.N` 形态）。

## 时间参数格式

`StartTime` / `EndTime` 用 UTC ISO8601，但**不同产品精度不同**，用错会报
`InvalidStartTime.Malformed`：

- **CMS `DescribeMetricList`** — 到秒：`YYYY-MM-DDTHH:mm:ssZ`（如 `2026-09-09T08:00:00Z`）。
- **RDS `DescribeDBInstancePerformance`** — 到分、**不带秒**：`YYYY-MM-DDTHH:mmZ`
  （如 `2026-09-09T08:00Z`）。

按目标 API 分别格式化时间（Python 分别用 `%Y-%m-%dT%H:%M:%SZ` 和 `%Y-%m-%dT%H:%MZ`）；
报错信息通常会给出该接口期望的格式。

## 响应解析

几个响应字段不是直读的：

- **CMS `DescribeMetricList` 的 `Datapoints`** — 是被转义的 JSON 字符串（非数组），需二次
  `json.loads` 才得到 `[{"timestamp","Average","Maximum",...}]`；空串表示该窗口无数据点。
- **RDS `DescribeDBInstancePerformance`** — 值嵌在
  `PerformanceKeys.PerformanceKey[].Values.PerformanceValue[]`，每点为 `{"Date","Value"}`；
  `Value` 常是逗号分隔多列（如 QPS,TPS），按对应 `Key` 拆列。
- **ECS `DescribeInvocations` 的命令输出** — 需加 `--IncludeOutput true`；回显在
  `Invocations.Invocation[0].InvokeInstances.InvokeInstance[0].Output`，为 Base64，需解码；
  先轮询 `InvokeRecordStatus` 至 `Finished` 再取。
