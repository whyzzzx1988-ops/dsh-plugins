# 恢复：重启卡死的 ECS

当实例为 `Running`、但公网探活和云助手命令均持续超时（实例卡死）时适用。区别于启动已停止的实例
（见 `recover_ecs.md`）。先尝试重启应用服务（`recover_app.md`）；仅当云助手也无响应、无法在实例内
操作时才重启实例。

## 确认关卡

- 对象：ECS `<ecs-id>`，地域 `<region>`。
- 动作：重启实例（`RebootInstance`）。
- 中断：实例重启期间应用短暂不可用。
- 版本变化：无。
- 新费用：无。
- 验证：等待 `Running`，再检查服务、`/healthz`、首页。
- 失败处理：汇报并停止；不盲目重试。

拒绝 → 不改变任何状态。

## 执行（一个动作）

```bash
aliyun ecs RebootInstance --RegionId <region> --InstanceId <ecs-id>
```

## 等待 Running

轮询 `DescribeInstances` 直到 `Status == Running`（有限次重试）。超时或状态意外 → 停止后续写操作并
汇报。随后验证并记录审计（`workflow.md`）。
