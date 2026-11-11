# Aliyun CLI 踩坑速查

调用前对照本表，避免同类参数在不同产品间的形态/格式差异导致报错。均以真实报错信息为准。

## 参数形态

同类参数形态要用对，否则报 `InvalidParameter` / `MissingParam`：

- **`InstanceIds`** — ECS（`DescribeInstances`）要 JSON 数组串 `'["<ecs-id>"]'`；裸串会报 `InvalidParameter`。
- **`RunCommand` 的实例参数** — 用 `.N` 重复形态 `--InstanceId.1 <ecs-id>`；裸 `--InstanceId`
  会报 `MissingParam.InstanceId`。

## 时间参数格式

`StartTime` / `EndTime` 用 UTC ISO8601，精度按产品要求，用错会报 `InvalidStartTime.Malformed`：

- **RDS `DescribeDBInstancePerformance`** — 到分、**不带秒**：`YYYY-MM-DDTHH:mmZ`
  （如 `2026-09-09T08:00Z`；Python 用 `%Y-%m-%dT%H:%MZ`）。

报错信息通常会给出该接口期望的格式。

## 响应解析

- **ECS `DescribeInvocations` 的命令输出** — 需加 `--IncludeOutput true`；回显在
  `Invocations.Invocation[0].InvokeInstances.InvokeInstance[0].Output`，为 Base64，需解码；
  先轮询 `InvokeRecordStatus` 至 `Finished` 再取。
