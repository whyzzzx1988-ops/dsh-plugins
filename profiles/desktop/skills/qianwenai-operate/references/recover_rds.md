# 恢复：RDS 相关处置

先识别 RDS 侧状况，再在安全层处置。指标口径与 `qianwenai-observe` 保持一致。

## 识别

- RDS 未运行
- 连接超时 / 认证失败 / 连接拒绝
- 连接数过高
- 慢 SQL / 行锁等待

使用只读 `DescribeDBInstances`、`DescribeDBInstancePerformance`、`DescribeSlowLogRecords`。

## 安全动作

- **由应用导致的连接池耗尽** → 优先重启应用服务（`recover_app.md`）重建连接，再验证 RDS 连接数恢复。
- **RDS 未运行 / 实例级问题 / 非应用导致的高连接 / 慢 SQL / 锁等待** → **不**改动 RDS 实例。
  输出证据和建议下一步（如优化慢 SQL、在控制台提高连接上限、扩容）并停止。

## 输出

RDS 证据（与 observe 同口径）+ 建议下一步。任何写操作都走应用服务路径（`recover_app.md`）及其确认
关卡；之后验证 RDS 连接恢复（`workflow.md`）。
