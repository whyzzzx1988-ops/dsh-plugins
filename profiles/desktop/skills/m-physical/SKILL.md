---
name: m-physical
description: "物理入侵/Physical：USB drop、rogue device、tailgating、badge 复制、锁具绕过、键盘记录硬件。"
---

# m-physical · 物理入侵 / Physical

被读到时：主人要做物理侧评估：USB 投递、恶意设备、尾随、门禁、锁具。

## 顺序

侦察物理环境 → 选切入点 → 投放/执行 → 回收 → 记录

## 一、USB Drop

```bash
# Rubber Ducky（按键注入）或 BadUSB（HID 攻击）
# 载荷：打开 cmd → 下载并执行 → 关闭窗口
# 散落在停车场/大厅/前台，目标捡到插入即触发
```

## 二、Rogue Device

| 设备 | 用途 |
|---|---|
| WiFi Pineapple | 伪造 AP，抓流量/中间人 |
| USB Killer | 破坏性，演练慎用 |
| Raspberry Pi 类 | 插入网口，做隐蔽跳板 |
| 恶意充电线 | 插上即建立连接 |

## 三、尾随与门禁

- tailgating：跟有权限的人一起进
- badge 复制：Proxmark3 读卡 → 克隆到空白卡
- 锁具：撬锁/开锁工具（合法演练）

## 四、硬件键盘记录

- 插在键盘 USB 口的硬件 keylogger
- 回收后读取记录

## 五、验收与还原

- 记录每个投放点的物理位置和回收时间
- 设备全部回收，不留现场
- 记录目标方是否察觉（配合蓝队评估）

只在授权的物理评估演练里做。工具：Rubber Ducky / Proxmark3 / WiFi Pineapple，都是持续维护的硬件项目。
