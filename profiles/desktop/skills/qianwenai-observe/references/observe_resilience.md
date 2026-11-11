# 可观测·系统事件与备份

评估实例系统事件和数据保护状态，回答「有没有计划内维护」「数据有没有备份」。全部只读。

## ECS 系统事件

```bash
aliyun ecs DescribeInstanceHistoryEvents --RegionId <region> --InstanceId <ecs-id>
```

读取计划内重启、健康维护、实例即将过保等事件。存在未完成的影响性事件 → 可用性层 `degraded`，
汇报事件类型和计划时间。

## ECS 系统盘快照

```bash
aliyun ecs DescribeSnapshots --RegionId <region> --InstanceId <ecs-id>
```

读取快照数量与最近一次创建时间。无快照 → 提示「无系统盘备份」作为数据保护风险（不计入健康分，
作为建议项）。

## RDS 备份（仅含 RDS 时）

```bash
aliyun rds DescribeBackups --RegionId <region> --DBInstanceId <rds-id>
```

读取最近备份集时间与大小。无近期备份 → 提示数据保护风险。

## 结果

并入可用性层：未完成系统事件、系统盘快照与 RDS 备份的最近时间。备份缺失作为建议项呈现，不计分。
