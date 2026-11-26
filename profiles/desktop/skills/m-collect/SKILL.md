---
name: m-collect
description: "收集/Collection：截屏、键盘记录、数据库导出、邮件收割、剪贴板、音频视频、浏览器数据。"
---

# m-collect · 收集 / Collection

被读到时：主人要在目标上收集数据：截图、键击、数据库、邮件、浏览器。

## 顺序

定要什么 → 定位存储位置 → 收集 → 打包带出（配合 m-exfil）

## 一、截屏与键击

```bash
# 截屏（Sliver 内置）
> screenshot
# 键击（自写 keylogger 或现成框架）
# Windows：SetWindowsHookEx / GetAsyncKeyState
# Linux：读 /dev/input 或 xinput
```

## 二、浏览器数据

```bash
# 浏览器历史/密码/Cookie（DPAPI 解密见 m-net）
# Chrome 位置：%LOCALAPPDATA%\Google\Chrome\User Data\Default\
# Login Data（密码，SQLite + DPAPI）、Cookies、History
```

## 三、数据库导出

```bash
# MySQL / PostgreSQL / MSSQL 整库导出
mysqldump -h TARGET -u user -p db > db.sql
pg_dump -h TARGET -U user db > db.sql
```

## 四、邮件与剪贴板

```bash
# 邮件：PST/OST 文件直接拷贝，或走 Exchange API
# 剪贴板：读 Clipboard API
```

## 五、验收

- 收集到的文件落地，能打开
- 分类整理（密码类/数据类/邮件类）
- 配合 m-exfil 安全带出

工具：Sliver 内置 + 系统命令 + 目标自带的数据库客户端。不引入额外特征。
