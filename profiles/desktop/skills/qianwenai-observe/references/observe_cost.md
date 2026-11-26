# 可观测·成本

**只展示真实的实际费用**——不展示预估。成本来自 BSS OpenAPI `QueryInstanceBill`（按实例的实际
账单金额）。币种为人民币（¥，国内站）。

## 来自状态文件的输入

从 `.qianwenai-deploy` 读取：`outputs.ecs_instance_ids[]`、`outputs.db_instance_id`、`region_id`、
`created_at`。用实例 ID 从账号账单中筛出本应用的行。

## 查询实际账单

按目标账期（`YYYY-MM`，支持最近 18 个月）查询按实例账单。默认查当前账期；用户指定区间时逐账期查询。

```bash
aliyun bssopenapi QueryInstanceBill --BillingCycle <YYYY-MM> --IsBillingItem false --PageSize 300
```

查某一天时加 `--Granularity DAILY --BillingDate <YYYY-MM-DD>`。

`QueryInstanceBill` 返回整个账号账期。从 `Data.Items.Item[]` 中，只保留 `InstanceID` 匹配本应用
ECS/RDS ID 的行。读取 `PretaxAmount`（应付）、`Currency`、`ProductCode`（如 `ecs`、`rds`）、
`SubscriptionType`、`BillingCycle`。把匹配行求和得到本应用实际费用，并按 `ProductCode` 给出
ECS / RDS 拆分。

参考：https://help.aliyun.com/en/user-center/developer-reference/call-api-operations-to-manage-resources-and-costs

## 本月到月底外推（可选）

用户想知道「这个月大概花多少」时，在当前账期实际账单基础上做线性外推：

```bash
aliyun bssopenapi QueryBill --BillingCycle <YYYY-MM> --Type PayAsYouGo --PageSize 300
```

按已过天数把当前账期实付金额外推到整月（`月末预计 = 已出金额 / 已过天数 * 当月总天数`）。明确标注为
**基于已出账单的外推、非账单金额**；已出实际费用仍单独如实展示。

## 暂无账单

- 该账期无匹配行（如刚部署，或账期尚未出账）→ 将成本标记为 `unknown`，原因「该账期暂无实际账单」。
  绝不退回预估、绝不编造价格。
- `QueryInstanceBill` 权限失败 → 标记成本 `unknown` 并注明缺失权限。

## 结果

成本层摘要：本应用在该账期的实际费用、按 `ProductCode` 的 ECS / RDS 拆分、币种、账期。所有数值均为
真实账单金额；绝不标注「预估」。
