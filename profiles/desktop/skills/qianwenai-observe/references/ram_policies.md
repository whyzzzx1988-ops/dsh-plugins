# qianwenai-observe 的 RAM 权限

除惰性安装云监控 agent 的 `cms:InstallMonitoringAgent` 外，权限均为只读；云助手命令均为只读检查。

## 所需权限

| Action | 用途 |
|--------|------|
| `ecs:DescribeInstances` | ECS 状态 / 规格 / 网络 |
| `ecs:RunCommand` | 运行服务/端口/内存快照脚本 |
| `ecs:DescribeInvocations` | 读取云助手命令结果 |
| `cms:DescribeMetricList` | ECS CPU / 网络 / 磁盘 / 内存时间序列 |
| `cms:DescribeMonitoringAgentStatuses` | 探测云监控插件状态 |
| `cms:InstallMonitoringAgent` | 惰性安装云监控 agent（内存趋势） |
| `ecs:DescribeSecurityGroupAttribute` | 安全组暴露面体检（80/443 放行、22/3306 暴露） |
| `ecs:DescribeInstanceHistoryEvents` | ECS 系统事件（计划维护 / 过保） |
| `ecs:DescribeSnapshots` | 系统盘快照状态 |
| `vpc:DescribeEipAddresses` | EIP 状态与带宽 |
| `bssopenapi:QueryInstanceBill` | 按实例的实际账单（成本） |
| `bssopenapi:QueryBill` | 账单总览（本月外推） |
| `rds:DescribeDBInstances` | RDS 状态（RDS 拓扑） |
| `rds:DescribeDBInstanceAttribute` | RDS 规格 / 存储（RDS 拓扑） |
| `rds:DescribeDBInstancePerformance` | RDS 性能序列（RDS 拓扑） |
| `rds:DescribeSlowLogRecords` | 慢 SQL（RDS 拓扑） |
| `rds:DescribeBackups` | RDS 备份状态（RDS 拓扑） |

## 权限 JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:RunCommand",
        "ecs:DescribeInvocations",
        "cms:DescribeMetricList",
        "cms:DescribeMonitoringAgentStatuses",
        "cms:InstallMonitoringAgent",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeSnapshots",
        "vpc:DescribeEipAddresses",
        "bssopenapi:QueryInstanceBill",
        "bssopenapi:QueryBill",
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute",
        "rds:DescribeDBInstancePerformance",
        "rds:DescribeSlowLogRecords",
        "rds:DescribeBackups"
      ],
      "Resource": "*"
    }
  ]
}
```

## 权限失败处理

任一调用出现 `Forbidden.RAM` → 把该层标记为 `unknown` 并注明缺失的 action，继续检查其他层，并在
汇报中列出缺失权限。不要中断整轮检查。
