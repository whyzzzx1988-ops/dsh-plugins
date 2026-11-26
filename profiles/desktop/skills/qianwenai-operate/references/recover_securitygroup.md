# 恢复：放行安全组入方向规则

当诊断显示端口在本机监听、但安全组缺少 80 / 443 入方向规则时适用。仅放行白名单端口（80、443），
绝不放行 22 / 3306 或其他端口。

## 先确认缺口（只读）

```bash
aliyun ecs DescribeSecurityGroupAttribute --RegionId <region> --SecurityGroupId <sg-id> --Direction ingress
```

确认确实缺少目标端口（80 和/或 443）的放行规则。已存在则无需处置。

## 确认关卡

- 对象：安全组 `<sg-id>`，地域 `<region>`。
- 动作：新增入方向规则放行 tcp 80 / 443（`AuthorizeSecurityGroup`）。
- 中断：无——仅放通入站。
- 版本变化：无。
- 暴露面：公网可访问 80 / 443；这是 Web 应用的预期暴露。绝不放行其他端口。
- 新费用：无。
- 验证：`DescribeSecurityGroupAttribute` 出现新规则，再检查 `/healthz` 和首页。
- 失败处理：汇报并停止。

拒绝 → 不改变任何状态。

## 执行（一个动作，按需对 80 / 443 各执行一次）

```bash
aliyun ecs AuthorizeSecurityGroup --RegionId <region> --SecurityGroupId <sg-id> \
  --Permissions.1.IpProtocol tcp --Permissions.1.PortRange 80/80 \
  --Permissions.1.SourceCidrIp 0.0.0.0/0 --Permissions.1.Policy accept
```

`443/443` 同理。幂等：规则已存在时视为成功。随后验证并记录审计（`workflow.md`）。
