---
name: m-inject
description: "注入与内存：DLL 注入七种方式、内存读写、MinHook/Frida、反调试、驱动与内核。"
---

# m-inject · 注入 / 进程 / 内存 / 驱动

被读到时：主人要做 DLL 注入、内存读写、进程 hook、驱动、反调试、反虚拟机。

## 一、注入方式对表

| 方式 | 适用 | 关键 API | 备注 |
|---|---|---|---|
| CreateRemoteThread | 通用 | `OpenProcess` → `VirtualAllocEx` → `WriteProcessMemory` → `CreateRemoteThread` | 最稳，最容易被 EDR 盯 |
| APC 注入 | 有线程的进程 | `QueueUserAPC` | 需要目标线程 alertable |
| 线程劫持 | 反注入较强的目标 | `SuspendThread` → `GetThreadContext` → 改 RIP → `ResumeThread` | 不新建线程 |
| Early Bird | 进程刚创建 | `CreateProcess(SUSPENDED)` + APC | 抢在 EDR 加载前 |
| 反射式 | 无文件 | 手工解析 PE 头，自己映射 | 不落盘，`LoadLibrary` 不出现 |
| SetWindowsHookEx | 有消息循环的 GUI | `WH_CBT` | 老办法，现代系统受限 |
| 进程镂空 | 伪装合法进程 | `NtUnmapViewOfSection` | 特征明显 |

## 二、最小可用注入器（C++，x64）

```cpp
#include <windows.h>
#include <cstdio>

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) { wprintf(L"usage: injector <pid> <dll>\n"); return 1; }
    DWORD pid = (DWORD)_wtoi(argv[1]);
    const wchar_t* dll = argv[2];

    HANDLE h = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!h) { wprintf(L"OpenProcess failed %lu\n", GetLastError()); return 1; }

    SIZE_T len = (wcslen(dll) + 1) * sizeof(wchar_t);
    LPVOID remote = VirtualAllocEx(h, nullptr, len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    WriteProcessMemory(h, remote, dll, len, nullptr);

    HANDLE t = CreateRemoteThread(h, nullptr, 0,
        (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW"),
        remote, 0, nullptr);
    if (!t) { wprintf(L"CreateRemoteThread failed %lu\n", GetLastError()); return 1; }

    WaitForSingleObject(t, INFINITE);
    DWORD code = 0; GetExitCodeThread(t, &code);
    wprintf(L"LoadLibraryW returned 0x%llX\n", (unsigned long long)code);
    VirtualFreeEx(h, remote, 0, MEM_RELEASE);
    CloseHandle(t); CloseHandle(h);
    return code ? 0 : 2;
}
```

编译：`cl /EHsc /O2 injector.cpp`（MSVC）或 `x86_64-w64-mingw32-g++ -O2 -o injector.exe injector.cpp`

## 三、内存读写模板（Python）

```python
import ctypes, ctypes.wintypes as w

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = w.HANDLE

class PROCESSENTRY32(ctypes.Structure):
    pass

def open_proc(pid):
    h = k32.OpenProcess(0x1F0FFF, False, pid)   # ALL_ACCESS
    if not h: raise ctypes.WinError(ctypes.get_last_error())
    return h

def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buf.raw

def write(h, addr, data: bytes):
    n = ctypes.c_size_t()
    if not k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n)):
        raise ctypes.WinError(ctypes.get_last_error())
    return n.value

# 例：读 4 字节 → 加 100 → 写回
h = open_proc(12345)
hp = int.from_bytes(read(h, 0x7FF6A0001234, 4), 'little')
write(h, 0x7FF6A0001234, (hp + 100).to_bytes(4, 'little'))
print('hp', hp, '->', hp + 100)
```

进程名找 PID：

```python
import subprocess, re
out = subprocess.run(['tasklist','/fo','csv'], capture_output=True, text=True).stdout
pid = [int(l.split('","')[1]) for l in out.splitlines() if 'game.exe' in l][0]
```

## 四、Hook

**MinHook（推荐）**

```cpp
#include "MinHook.h"
typedef int (WINAPI* tDealDamage)(void* self, void* target, int dmg);
tDealDamage oDeal = nullptr;

int WINAPI hkDeal(void* self, void* target, int dmg) {
    return oDeal(self, target, dmg * 10);   // 伤害 ×10
}

MH_Initialize();
MH_CreateHook((LPVOID)0x1401A3F20, &hkDeal, (LPVOID*)&oDeal);
MH_EnableHook(MH_ALL_HOOKS);
```

**Frida（不用编译）**

```javascript
const f = Module.getExportByName('game.exe', 'DealDamage');
Interceptor.attach(f, {
  onEnter(a) { this.dmg = a[2].toInt32(); },
  onLeave(r) { r.replace(ptr(this.dmg * 10)); }
});
```

**特征码定位**（模块更新后偏移会变）：

```javascript
// 扫 48 8B 89 ?? ?? ?? ?? E8 找函数头
const base = Module.getBaseAddress('game.exe');
const pat = '48 8B 89 ?? ?? ?? ?? E8';
const hit = Memory.scanSync(base, 0x2000000, pat)[0];
console.log('fn @', hit.address, '+', hit.address.sub(base));
```

## 五、反调试 / 反虚拟机绕

| 检查 | 绕法 |
|---|---|
| `IsDebuggerPresent` | patch 返回 0；或 frida `Interceptor.replace` |
| `NtQueryInformationProcess(ProcessDebugPort)` | 同上 |
| `PEB.BeingDebugged` | `Memory.writeU8(peb+2, 0)` |
| 时间差检测 | hook `QueryPerformanceCounter` 返回正常间隔 |
| 硬件断点检测 | 用软件断点（int3）+ 恢复原字节 |
| VM 检测（CPUID / vmtoolsd 进程 / MAC 前缀） | 改 VMX 配置、改 MAC、隐藏进程名 |

## 六、驱动 / 内核

只做本机测试：
1. 关驱动签名强制（测试模式）：`bcdedit /set testsigning on` + 重启。
2. `WDM` 或 `KMDF` 骨架，`IoCreateDevice` + `IRP_MJ_DEVICE_CONTROL` 处理读写。
3. 用户态 `DeviceIoControl` 调 `MmCopyVirtualMemory` 读目标进程。
4. 用完 `bcdedit /set testsigning off`。

## 验收

注入成功 = 目标进程模块列表里出现目标 DLL（`Process Explorer` 或 `CreateToolhelp32Snapshot` 枚举）；hook 生效 = 行为改变可观测（数值变化、日志打印）。
