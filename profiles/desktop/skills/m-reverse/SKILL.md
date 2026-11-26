---
name: m-reverse
description: "二进制逆向：PE/ELF/Mach-O/.NET 分析、脱壳识别、函数定位、结构体还原。"
---

# m-reverse · 二进制逆向

被读到时：主人要分析、定位、还原一个二进制（PE / ELF / Mach-O / .NET / APK 里的 so）。

## 顺序

1. 基线：`file` `strings -n 6` `checksec` `pefile` 看节表 / 导入表 / 编译语言。
2. 壳识别：节名（`.vmp0` `.themida` `.aspack` `UPX0`）、入口点熵、`Die` 或 `ExeInfoPE` 交叉验证。
3. 语言指纹：MSVC / MinGW / Go（`go1.` 版本串）/ Rust（`rustc` 路径串）/ .NET（`BSJB` 签名）/ Qt / Electron（`app.asar`）。
4. 定位：字符串 → 交叉引用 → 关键函数；`xrefs` 走调用链；参数结构从调用约定反推。
5. 还原：写脚本重放算法（Python），或直接 patch，或 hook 观察。

## 通用命令

```bash
file target.work
strings -n 6 -a target.work | grep -iE "license|trial|serial|activate|hwid|expire|error|fail"
objdump -d -M intel target.work | less
python -c "import pefile;pe=pefile.PE('target.work');print(hex(pe.OPTIONAL_HEADER.ImageBase));[print(hex(s.VirtualAddress),s.Name) for s in pe.sections]"
```

radare2 一把梭：

```
r2 -A target.work
afl                   # 函数表
izz~license           # 字符串
axt @ str.license     # 谁引用了它
pdf @ main
```

## IDA / Ghidra 要点

- IDA：`Shift+F12` 字符串，`X` 交叉引用，`F5` 反编译，`Alt+T` 搜字节，`Ctrl+S` 看段。
- Ghidra：`Search → For Strings`，`References → Show References to`，`Decompile` 窗口右键 `Edit Function Signature` 改签名让伪代码变干净。
- 结构体：在 `Local Types` 里按反编译出来的偏移建 struct，之后整个函数可读性翻倍。

## .NET

```bash
# dnSpy / ILSpy 直接看；命令行：
ilspycmd target.work -o out_dir
# 混淆（ConfuserEx / .NET Reactor）先脱：
de4dot target.work -o target.clean.exe
```

## Go / Rust

- Go：`go tool nm`、`redress -src`、字符串里的 `main.` 前缀、`gopclntab` 解析出函数名。
- Rust：符号基本保留，`strings | grep -i panicked` 找 `src/` 路径。

## 结构体还原示例

反编译看到 `*(int*)(arg + 0x18)`，就建：

```c
typedef struct {
    void*   vtable;      // +0x00
    char    name[16];    // +0x08
    int     hp;          // +0x18
    int     max_hp;      // +0x1c
    float   pos[3];      // +0x20
} Actor;                 // size 0x30
```

## 验收

- 定位到的那条指令，改前 / 改后各跑一次，行为差异可观察；
- 或 hook 打印的入参返回值，跟静态推断对得上。

## 报告口径

一句结论（找到了什么）→ 证据链（哪个地址、哪条指令、为什么是它）→ 复现命令一行一条。
