---
name: m-crack
description: "破解与授权绕过：校验点定位、字节 patch、Frida hook、keygen、注册表与时间回拨、VMP/Themida 对抗。"
---

# m-crack · 破解 / 授权 / DRM

被读到时：主人要在 `.work` 副本上去掉试用、激活、卡密、序列号、在线校验。

## 铁律

先在副本上做：`cp target.exe target.work`。原件不动。所有 patch 都打 `target.work`。

## 一、定位校验点（四条路，按命中率排）

**1. 字符串交叉引用（最快，60%）**

```bash
strings -n 6 target.work | grep -iE "invalid|expired|trial|激活|授权|序列号|wrong key"
```
找到 "License invalid" 之类 → `X` 交叉引用 → 上溯到比较点 → 那就是唯一分支。

**2. API 断点（40%）**

| 场景 | 断点 |
|---|---|
| 读注册表授权 | `RegOpenKeyExW` `RegQueryValueExW` |
| 读授权文件 | `CreateFileW` `ReadFile` |
| 时间炸弹 | `GetLocalTime` `GetSystemTimeAsFileTime` `time` `GetTickCount64` |
| 网络校验 | `WinHttpSendRequest` `InternetReadFile` `send` `recv` |
| 加密 | `CryptDecrypt` `BCryptDecrypt` |

x64dbg：`bp RegQueryValueExW`，命中后看栈上 `lpValueName`，跟进去。

**3. 特征字节（30%）**

```
cmp eax, 1        → 83 F8 01
test eax, eax     → 85 C0
je/jne 主分支     → 74/75 xx
```
搜 `test eax,eax` 附近跟 `jnz` 的模式，改成 `nop` 或反转跳转。

**4. 报错对话框（兜底）**

`MessageBoxW` 断点，回溯栈到调用者，那个函数里的条件跳转就是校验结果。

## 二、四种打法

### A. 字节 patch

```
原始：  0F 84 8A 00 00 00      je  +0x8A      （相等就跳过失败分支）
改后：  90 90 90 90 90 90      nop ×6
或反转：0F 85 8A 00 00 00      jne +0x8A
```

算文件偏移：`文件偏移 = RVA - 节.VirtualAddress + 节.PointerToRawData`

```python
import pefile
pe = pefile.PE('target.work'); rva = 0x1234
print(hex(pe.get_offset_from_rva(rva)))
```

打补丁：

```python
data = bytearray(open('target.work','rb').read())
data[0x1234:0x1234+6] = b'\x90'*6
open('target.work','wb').write(data)
```

### B. Frida 运行时 hook

```javascript
// hook 校验函数：入参照旧，返回值强制 1
const addr = Module.findBaseAddress('app.exe').add(0x1A3F20);
Interceptor.attach(addr, {
  onEnter(args) { console.log('[chk] arg0=', args[0].toInt32(), 'arg1=', args[1].readUtf8String()); },
  onLeave(ret) { console.log('[chk] ret=', ret.toInt32()); ret.replace(ptr(1)); }
});
```

启动：`frida -f app.exe -l hook.js --runtime=v8`

### C. 注册机（keygen）

从反编译里把算法抄出来，逐轮对齐：

```python
def keygen(name: str) -> str:
    s = 0x1337
    for ch in name:
        s = (s * 31 + ord(ch)) & 0xFFFFFFFF
    out = []
    for i in range(4):
        out.append(f"{(s >> (8*i)) & 0xFF:02X}")
    return "-".join(out)
```

验证方式：把生成的码喂回程序，看是否进主界面；不一致就对比中间值（在 IDA 里给循环变量改名，逐步 print）。

### D. 注册表 / 时间

```powershell
# 试用起始时间戳重置
$k = 'HKCU:\Software\AppX'
Set-ItemProperty -Path $k -Name TrialStart -Value ([int][double]::Parse((Get-Date -UFormat %s)))
# 让程序写不回去：把键的 ACL 改成只读
$acl = Get-Acl $k
$acl.SetAccessRuleProtection($true,$false)
$rule = New-Object System.Security.AccessControl.RegistryAccessRule("$env:USERNAME","SetValue","Deny")
$acl.AddAccessRule($rule); Set-Acl $k $acl
```

时间回拨更稳的做法是 hook：`frida -f app.exe -l hook_time.js`，把 `GetLocalTime` 伪造成固定日期。

## 三、保护对抗

| 保护 | 打法 |
|---|---|
| UPX | `upx -d target.work` |
| ASPack / PECompact | `x64dbg` 跑 ESP 定律 → OEP → `Scylla` dump + 修 IAT |
| VMProtect | 不脱 VM，改打"结果"：hook VM 出口的返回寄存器，或直接 patch VM 之后的比较 |
| Themida | 同上；优先找 `VM Exit` 后的 `cmp`，别碰虚拟化段 |
| .NET 混淆 | `de4dot` → `dnSpy` 改 IL → `Save Module` |
| 反调试 | `ScyllaHide` 插件勾全；或 patch `IsDebuggerPresent` / `NtQueryInformationProcess` 返回 0 |
| 完整性自校验 | 找 CRC 比较点，让两边都读原始文件；或改校验函数直接返回 true |

## 四、验收

1. patch 后程序启动、功能可用；
2. 断点再打一次，确认不再进失败分支；
3. 记录：文件偏移、原始字节、改后字节、验证命令。
