# 最小诊断

只读，无需确认。在第一个明确可处置的故障层停下，但要收集足够证据以建议一个动作。
按短路顺序判定；同一台 ECS 上的只读检查合并成一条云助手脚本一次性取回，减少往返。

`<service_name>` 取自状态文件的 `service_name` 字段（缺失时回退 `qianwenai-app`）。

项目目录存在新鲜的 `observe_handoff.json`（来自 `qianwenai-observe`）时，先读它的 `fault_layer`
和 `symptoms` 作为诊断起点：优先验证被点名的那一层。它只是线索、不是结论，仍按下方检查独立复核后
再建议动作；线索与实测冲突时以实测为准。

## 检查

> 入口探活正常不等于应用/主机健康。症状为"变慢 / 间歇 / 偶发超时"时，不得凭探活收尾——
> 在步骤 3 的云助手脚本里取本机实时 CPU/内存/负载（`top -bn1`、`uptime`、`free -m`），据实测判定。

1. **公网入口** — 探测公网地址和 `/healthz`：

   ```bash
   curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 10 "http://<public_ip>/healthz"
   curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 10 "http://<public_ip>/"
   ```

2. **ECS 状态** — `aliyun ecs DescribeInstances`。Stopped → 很可能是启动已停止实例。

3. **应用服务 / Nginx / 端口 / 近期日志**（只读云助手）：

   > `<app_port>` 取状态文件 `app_port`；该字段为空时用 `8080`。切勿代入空串，否则端口匹配会退化成匹配任意监听端口。

   ```bash
   aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
     --ContentEncoding Base64 \
     --CommandContent "$(printf '%s' 'systemctl is-active <service_name>; systemctl is-active nginx; ss -ltnp | grep -E ":80|:<app_port>"; nginx -t 2>&1 | tail -n 3; df -h /; uptime; top -bn1 | head -n 12; free -m; journalctl -u <service_name> --since "30 min ago" --no-pager | tail -n 80' | base64)"
   aliyun ecs DescribeInvocations --RegionId <region> --InvokeId <invoke-id> --IncludeOutput true
   ```

   `<service_name>` inactive → 很可能是重启应用服务。`nginx -t` 失败 / nginx inactive → 很可能是
   Nginx 处置。

   CPU 持续接近满载 / 负载远高于核数、而探活仍正常 → 按应用服务处置排查（`recover_app.md`）。

   根分区使用率 ≥ 90%（或因无空间导致应用无法写入 / 启动）→ 很可能是磁盘清理。

   当端口在本机监听（`ss` 显示已绑定 80 / `<app_port>`）但步骤 1 的公网探测失败时，改查安全组入方向规则，
   而非直接判定服务已挂，使用 `outputs.security_group_id`（回退：从 `DescribeInstances` 读取）：

   ```bash
   aliyun ecs DescribeSecurityGroupAttribute --RegionId <region> --SecurityGroupId <sg-id> --Direction ingress
   ```

   无放行 80 / 443 的入方向规则 → 故障是端口未放行，而非服务已死。

   端口在监听、安全组也放行、但公网仍不通时，查 EIP 是否解绑 / 欠费（优先用
   `outputs.eip_allocation_id`，缺失时用 `--AssociatedInstanceId` 反查）：

   ```bash
   aliyun vpc DescribeEipAddresses --RegionId <region> --AllocationId <eip-id>
   ```

   EIP 未绑定（`Available`）→ 很可能是重新绑定 EIP。欠费冻结 → 仅提示，超出恢复白名单。

4. **RDS（如有）** — 状态、ECS→RDS 连通性、连接压力、慢 SQL
   （`DescribeDBInstances`、`DescribeDBInstancePerformance`、`DescribeSlowLogRecords`）。应用日志
   出现 DB 超时 / 认证失败 / 拒绝 / 连接池等待 → 很可能是 RDS 相关处置。

## 输出

汇报：**故障层次 · 可能原因 · 证据 · 建议动作 · 影响**。所有证据脱敏。此阶段不执行任何恢复。

## 映射到恢复

| 诊断 | 动作 reference |
|------|----------------|
| ECS Stopped | `recover_ecs.md` |
| ECS Running 但卡死（探活/云助手均超时） | `recover_reboot.md` |
| `<service_name>` inactive / 连接池异常 | `recover_app.md` |
| Nginx 异常 | `recover_nginx.md` |
| RDS 未运行 / 连接压力 / 慢 SQL | `recover_rds.md` |
| 根分区将满（≥ 90%） | `recover_disk.md` |
| 安全组缺少 80 / 443 入方向规则 | `recover_securitygroup.md` |
| EIP 未绑定 | `recover_eip.md` |
| 根盘物理不足（清理后仍不够） | `recover_disk.md`（扩容部分） |
