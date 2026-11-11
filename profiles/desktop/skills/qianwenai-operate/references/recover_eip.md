# 恢复：重新绑定 EIP

当诊断显示 EIP 处于 `Available`（已从实例解绑）、且端口在监听、安全组已放行时适用。欠费冻结的 EIP
不在此处理，仅提示用户续费。

## 取 EIP 分配 ID

优先用状态文件的 `outputs.eip_allocation_id`；缺失时反查：

```bash
aliyun vpc DescribeEipAddresses --RegionId <region> --AssociatedInstanceId <ecs-id>
```

若已绑定当前实例，视为无需处置。若查到解绑的 EIP，记录其 `AllocationId`。

## 确认关卡

- 对象：EIP `<eip-id>`，地域 `<region>`。
- 动作：绑定到 ECS `<ecs-id>`（`AssociateEipAddress`）。
- 中断：绑定后公网入口恢复。
- 版本变化：无。
- 新费用：无（EIP 已存在）。
- 验证：`DescribeEipAddresses` 显示 `InUse`，再检查 `/healthz` 和首页。
- 失败处理：汇报并停止。

拒绝 → 不改变任何状态。

## 执行（一个动作）

```bash
aliyun vpc AssociateEipAddress --RegionId <region> --AllocationId <eip-id> --InstanceId <ecs-id>
```

幂等：若已绑定该实例，视为成功。随后验证并记录审计（`workflow.md`）。
