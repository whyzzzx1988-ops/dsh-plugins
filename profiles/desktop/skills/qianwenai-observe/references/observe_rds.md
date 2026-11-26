# 可观测·RDS

仅当状态文件中 `outputs.db_instance_id` 非空时执行；否则干净跳过。

## 状态 + 规格

```bash
aliyun rds DescribeDBInstances --RegionId <region> --DBInstanceId <rds-id>
aliyun rds DescribeDBInstanceAttribute --RegionId <region> --DBInstanceId <rds-id>
```

读取实例状态、规格、存储容量。非运行状态 → `unavailable`。

## 性能

```bash
aliyun rds DescribeDBInstancePerformance --RegionId <region> --DBInstanceId <rds-id> \
  --Key MySQL_ThreadStatus,MySQL_QPSTPS,MySQL_IOPS,MySQL_MemCpuUsage,MySQL_Space,MySQL_RowLockCurrentWaits \
  --StartTime <start> --EndTime <end>
```

覆盖 CPU/内存、连接数、QPS/TPS、IOPS、空间使用、行锁等待。标记：

- 连接数接近实例上限 → `degraded`
- 行锁等待高 → `degraded`
- 空间接近写满 → `degraded`

参考：https://help.aliyun.com/en/rds/developer-reference/performance-parameters

## 慢 SQL（脱敏）

```bash
aliyun rds DescribeSlowLogRecords --RegionId <region> --DBInstanceId <rds-id> \
  --StartTime <start> --EndTime <end> --PageSize 30
```

输出 SQL **模板**（或脱敏 SQL）、执行时间、影响。绝不展示字面参数值；每条限制长度。

参考：https://help.aliyun.com/zh/rds/developer-reference/api-rds-2014-08-15-describeslowlogrecords

## 关联应用日志

把 RDS 发现与应用日志信号关联：数据库超时、认证失败、连接拒绝、连接池等待。

## 结果

RDS 层状态附证据：状态、连接数趋势、QPS/TPS、空间、行锁等待，以及脱敏后的慢 SQL 模板 Top。
