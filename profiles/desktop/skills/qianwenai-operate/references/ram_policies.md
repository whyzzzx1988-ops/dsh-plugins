# qianwenai-operate 的 RAM 权限

诊断与验证用只读权限；恢复动作用写权限（仅限确认后的动作）。

## 所需权限

| Action | 类型 | 用途 |
|--------|------|------|
| `ecs:DescribeInstances` | 读 | 诊断/验证时的 ECS 状态 |
| `ecs:DescribeInvocations` | 读 | 读取云助手结果 |
| `ecs:DescribeSecurityGroupAttribute` | 读 | 入方向规则检查（80 / 443 是否放行） |
| `ecs:DescribeDisks` | 读 | 取根盘 ID（扩容前置） |
| `vpc:DescribeEipAddresses` | 读 | EIP 绑定状态诊断 |
| `rds:DescribeDBInstances` | 读 | RDS 状态（RDS 拓扑） |
| `rds:DescribeDBInstancePerformance` | 读 | RDS 性能（RDS 拓扑） |
| `rds:DescribeSlowLogRecords` | 读 | 慢 SQL（RDS 拓扑） |
| `ecs:StartInstance` | 写 | 启动已停止的 ECS |
| `ecs:RebootInstance` | 写 | 重启卡死的 ECS |
| `ecs:AuthorizeSecurityGroup` | 写 | 放行 80 / 443 入方向规则 |
| `ecs:ResizeDisk` | 写 | 根盘扩容（清理后仍不足） |
| `vpc:AssociateEipAddress` | 写 | 重新绑定解绑的 EIP |
| `ecs:RunCommand` | 写 | 执行白名单恢复命令（应用 / Nginx） |

## 权限 JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInvocations",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeDisks",
        "vpc:DescribeEipAddresses",
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstancePerformance",
        "rds:DescribeSlowLogRecords",
        "ecs:StartInstance",
        "ecs:RebootInstance",
        "ecs:AuthorizeSecurityGroup",
        "ecs:ResizeDisk",
        "vpc:AssociateEipAddress",
        "ecs:RunCommand"
      ],
      "Resource": "*"
    }
  ]
}
```

## 权限失败处理

写动作出现 `Forbidden.RAM` → 在写操作前停止，汇报缺失权限，不执行恢复。读动作失败 → 汇报未知项并
继续其余诊断。
