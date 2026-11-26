# 恢复：重启应用服务

当 `<service_name>` 未运行或连接池异常时适用。`<service_name>` 取自状态文件的 `service_name`
字段（缺失时回退 `qianwenai-app`）。

## 确认关卡

- 对象：ECS `<ecs-id>` 上的服务 `<service_name>`。
- 动作：`systemctl restart <service_name>`。
- 中断：短暂——应用重启。
- 版本变化：无（代码不变）。
- 新费用：无。
- 验证：服务稳定后检查端口、`/healthz`、首页；连接池问题还需确认 RDS 连接数恢复。
- 失败处理：汇报失败步骤并停止。

拒绝 → 不改变任何状态。

## 执行（一个白名单恢复命令）

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 \
  --CommandContent "$(printf '%s' 'systemctl restart <service_name> && sleep 3 && systemctl is-active <service_name>' | base64)"
aliyun ecs DescribeInvocations --RegionId <region> --InvokeId <invoke-id> --IncludeOutput true
```

幂等：重启可安全重复。不要把其他变更并进同一条命令。

随后验证并记录审计（`workflow.md`）。
