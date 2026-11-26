# 恢复：Nginx

当 Nginx 异常时适用。**重载/重启前必须先校验配置。**

## 第 1 步 — 校验配置（只读）

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 --CommandContent "$(printf '%s' 'nginx -t 2>&1' | base64)"
aliyun ecs DescribeInvocations --RegionId <region> --InvokeId <invoke-id> --IncludeOutput true
```

- **`nginx -t` 失败** → 停止。不重载/重启。返回错误位置和处理建议。这是硬性关卡。
- **`nginx -t` 通过** → 进入确认关卡。

## 第 2 步 — 确认关卡

- 对象：ECS `<ecs-id>` 上的 Nginx。
- 动作：重载（优先）或重启 Nginx。
- 中断：重载近乎为零；重启短暂。
- 版本变化：无。
- 新费用：无。
- 验证：`/healthz` 和首页。
- 失败处理：汇报并停止。

拒绝 → 不改变任何状态。

## 第 3 步 — 执行（一个白名单命令，仅在 `nginx -t` 通过后）

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 --CommandContent "$(printf '%s' 'nginx -t && systemctl reload nginx && systemctl is-active nginx' | base64)"
```

幂等。随后验证并记录审计（`workflow.md`）。
