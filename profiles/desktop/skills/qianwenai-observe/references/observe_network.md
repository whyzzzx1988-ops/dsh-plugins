# 可观测·公网与暴露面

评估 EIP 公网入口和安全组暴露面。全部只读。优先用状态文件的 `outputs.eip_allocation_id`；缺失时用
`--AssociatedInstanceId <ecs-id>` 反查。

## EIP 状态与带宽

```bash
aliyun vpc DescribeEipAddresses --RegionId <region> --AllocationId <eip-id>
```

读取 `Status`（`InUse` / `Available` / …）、绑定实例、带宽上限、`ChargeType`。

- 未绑定实例（`Available`）或欠费冻结 → `unavailable`，公网探活会失败。
- 已绑定且正常 → 继续看带宽。

带宽时间序列（命名空间 `acs_vpc_eip`）：

```bash
aliyun cms DescribeMetricList --Namespace acs_vpc_eip \
  --MetricName net_tx.rate --Dimensions '[{"instanceId":"<eip-id>"}]' \
  --StartTime <start> --EndTime <end> --Period 60
```

对 `net_rx.rate` 重复。出/入带宽持续贴近上限或丢包 → `degraded`。

## 安全组暴露面（只读）

```bash
aliyun ecs DescribeSecurityGroupAttribute --RegionId <region> --SecurityGroupId <sg-id> --Direction ingress
```

- 无放行 80 / 443 入方向规则 → 公网不可达的可能原因，标注为风险。
- 22（SSH）/ 3306（MySQL）对 `0.0.0.0/0` 开放 → 暴露面风险，`degraded` 并给出收敛建议。

## 结果

并入应用/可用性层证据：EIP 状态与带宽余量、暴露面风险项。EIP 未绑定或安全组缺 80/443 时，提议用
`qianwenai-operate` 处置。
