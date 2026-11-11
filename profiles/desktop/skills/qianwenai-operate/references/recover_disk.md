# 恢复：回收磁盘空间

适用于根分区将满、应用无法写入或启动的情况。仅做安全、非破坏性的回收——绝不触碰应用数据或数据库。

## 先检查（只读）

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 \
  --CommandContent "$(printf '%s' 'df -h /; du -xh --max-depth=1 /var/log 2>/dev/null | sort -rh | head; journalctl --disk-usage' | base64)"
aliyun ecs DescribeInvocations --RegionId <region> --InvokeId <invoke-id> --IncludeOutput true
```

## 确认门

- 目标：ECS `<ecs-id>`（`<region>`）的根分区。
- 动作：截断轮转日志、vacuum journal、清理构建缓存。根据检查结果说明预计可回收空间。
- 中断：无。
- 版本变化：无。
- 数据安全：不触碰应用目录、数据库、证书。
- 验证：`df -h /` 有可用空间；应用可再次写入 / 启动。
- 若失败：汇报并停止。

拒绝 → 不做任何变更。

## 执行（一条白名单命令）

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 \
  --CommandContent "$(printf '%s' 'journalctl --vacuum-size=200M; truncate -s 0 /var/log/nginx/*.log 2>/dev/null; rm -rf /tmp/qianwenai-* /root/.cache/pip /usr/local/share/.cache/yarn 2>/dev/null; df -h /' | base64)"
```

幂等。绝不在应用目录或任何数据路径下执行 `rm`。随后验证并记录审计条目（`workflow.md`）。

## 清理后仍不足 → 扩容根盘（有费用，强确认）

仅当上面的清理执行后 `df -h /` 仍接近写满、且根盘物理容量确实不够时适用。扩容会**增加费用**，需强确认。

取根盘 ID：

```bash
aliyun ecs DescribeInstances --RegionId <region> --InstanceIds '["<ecs-id>"]'
```

从实例的系统盘读取 `DiskId`（或用 `aliyun ecs DescribeDisks --InstanceId <ecs-id>`）。

### 确认关卡

- 对象：ECS `<ecs-id>` 的根盘 `<disk-id>`。
- 动作：扩容到 `<new-size>` GB（`ResizeDisk`）。
- 中断：在线扩容通常无需重启；扩容后需在实例内扩展文件系统才能生效。
- 版本变化：无。
- 新费用：**是**——磁盘按更大容量计费。明确告知预计变化。
- 验证：`DescribeDisks` 显示新容量；实例内扩展文件系统后 `df -h /` 出现可用空间。
- 失败处理：汇报并停止。

拒绝 → 不做任何变更。

### 执行（一个动作）

```bash
aliyun ecs ResizeDisk --RegionId <region> --DiskId <disk-id> --NewSize <new-size> --Type online
```

扩容云盘后，文件系统扩展在实例内进行（`growpart` + `resize2fs`/`xfs_growfs`），走 `RunCommand`
白名单并单独确认。随后验证并记录审计（`workflow.md`）。
