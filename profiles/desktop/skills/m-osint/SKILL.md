---
name: m-osint
description: "OSINT 信息收集：子域枚举、邮件收割、Shodan/Censys、GitHub dorking、证书透明性、历史 DNS、社交图谱。"
---

# m-osint · OSINT / 信息收集

被读到时：主人在做侦察，要子域、邮箱、资产、暴露面、员工信息、技术栈。

## 顺序

目标名 → 子域 → 资产/暴露面 → 邮箱/员工 → 代码泄露 → 汇总

## 一、子域枚举

```bash
# 证书透明性（crt.sh 最稳，不依赖爆破）
curl -s "https://crt.sh/?q=%25.$DOMAIN&output=json" | jq -r '.[].name_value' | sort -u
# 被动 + 主动
subfinder -d $DOMAIN -all
amass enum -passive -d $DOMAIN
# 爆破（字典小，先被动后爆破）
ffuf -u "https://FUZZ.$DOMAIN" -w subdomains.txt -mc 200,301,302,403
```

## 二、暴露面

```bash
# Shodan / Censys（有 key 时）
curl -s "https://api.shodan.io/shodan/host/$IP?key=$KEY" | jq .
# 无 key 用公开镜像
# Censys: https://search.censys.io/api/v2/hosts/$IP
```

## 三、邮箱与员工

```bash
# 邮箱格式推断 + 收割
theHarvester -d $DOMAIN -b all
# LinkedIn 收割（用 hunter.io / 手工）
# 邮箱格式：先找到已知员工，推格式 first.last@domain
```

## 四、代码泄露

```bash
# GitHub dorking
site:github.com "domain.com" password
site:github.com "domain.com" api_key
# 用 trufflehog 扫组织
trufflehog github --org=$ORG
# grep.app / sourcegraph 公开代码搜索
```

## 五、历史与元数据

```bash
# 历史 DNS（securitytrails / 已归档）
# whois 与注册信息
whois $DOMAIN
# 证书与 ASN
dig +short $DOMAIN A
```

## 六、验收

- 子域清单（去重、去通配符）
- 暴露面清单（IP + 端口 + 服务版本）
- 邮箱格式 + 员工名单
- 泄露的 key/凭据（有就列出，标注来源）

工具都取最新版，不写死版本号。
