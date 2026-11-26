# 恢复：启动已停止的 ECS

当诊断显示 ECS 实例为 `Stopped` 时适用。

## 确认关卡

动作前先展示并取得明确确认：

- 对象：ECS `<ecs-id>`，地域 `<region>`。
- 动作：启动实例（`StartInstance`）。
- 中断：实例启动；服务起来后应用恢复。
- 版本变化：无。
- 新费用：实例恢复运行后恢复小时计费。
- 验证：等待 `Running`，再检查 `/healthz` 和服务。
- 失败处理：汇报并停止；不盲目重试。

用户拒绝 → 不改变任何状态。

## 执行（一个动作）

```bash
aliyun ecs StartInstance --RegionId <region> --InstanceId <ecs-id>
```

幂等：若已 `Running`，视为成功。

## 等待 Running

轮询 `DescribeInstances` 直到 `Status == Running`（有限次重试）。超时或状态意外，停止后续写操作并
汇报。

随后验证并记录审计（`workflow.md`）。
