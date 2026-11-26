---
name: m-forensics
description: "取证与反取证：Windows/Linux 痕迹、事件日志、内存镜像、时间戳伪造。"
---

# m-forensics · 取证 / 反取证 / 痕迹

被读到时：主人要查一台机器上发生了什么，或者要清掉痕迹。

## 一、Windows 取证

```ps1
Get-Process | Sort-Object CPU -Desc | Select -First 20
Get-NetTCPConnection -State Established | Select LocalPort,RemoteAddress,OwningProcess
Get-CimInstance Win32_StartupCommand | Select Name,Command,Location
schtasks /query /fo LIST /v | findstr /i "TaskName Task\ To\ Run"
```

注册表启动项：

```
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
```

事件日志（4688 进程创建、4624 登录、4625 失败、7045 服务安装）：

```ps1
Get-WinEvent -FilterHashtable @{LogName='Security';Id=4688} -MaxEvents 50 |
  Select TimeCreated,@{n='cmd';e={$_.Properties[8].Value}}
```

## 二、Linux 取证

```bash
last -ai | head -20
grep -i "accepted\|failed" /var/log/auth.log | tail -50
lsof -i -P -n | grep ESTABLISHED
ps -eo pid,ppid,user,lstart,cmd --sort=start_time | tail -20
find / -newermt '-2 hours' -type f 2>/dev/null | grep -v ^/proc | head -50
```

时间线：`find` 按 mtime 排序 + 日志时间对齐，画出"什么时候装了什么"。

## 三、内存与磁盘

```bash
winpmem_mini_x64.exe mem.raw
volatility3 -f mem.raw windows.pslist
volatility3 -f mem.raw windows.netscan
volatility3 -f mem.raw windows.malfind
sha256sum disk.img
```

磁盘先出镜像再分析，副本上做，原件留档。

## 四、反取证

| 痕迹 | 位置 |
|---|---|
| 命令历史 | `~/.bash_history`、`ConsoleHost_history.txt` |
| 事件日志 | `wevtutil cl System` |
| 预取 | `C:/Windows/Prefetch/*.pf` |
| 最近文件 | `%APPDATA%\Microsoft\Windows\Recent\` |
| 服务/任务 | `sc delete`、`schtasks /delete` |
| 浏览器 | History / Cookies / Cache |
| 网络 | `ipconfig /flushdns` |

清得越干净越可疑，日志断档本身就是特征。演练里保留最小痕迹更自然。

## 五、时间戳

```ps1
$f = Get-Item C:/path/a.exe
$f.LastWriteTime  = '2024-01-01 10:00:00'
$f.CreationTime   = '2024-01-01 10:00:00'
$f.LastAccessTime = '2024-01-01 10:00:00'
```

NTFS 还会在 $MFT 留改动记录。

## 六、验收

取证给时间线 + 关键证据（哪条日志、哪个文件、哪个 IP）。反取证指定痕迹点复查为空，并记录清过哪些。
