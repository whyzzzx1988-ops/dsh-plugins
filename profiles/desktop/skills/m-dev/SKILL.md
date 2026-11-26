---
name: m-dev
description: "普通开发：先看再改、调试顺序、代码硬要求、架构判断、部署。"
---

# m-dev · 普通开发 / 架构 / 调试

被读到时：主人在写代码、改 bug、设计结构、部署、做工具。

## 一、先看再改

```bash
git status; git log --oneline -10; ls
# 找入口
grep -rn "func main\|def main\|if __name__" --include=*.go --include=*.py . | head
```

改之前先跑一遍现有测试，拿到基线。没有测试就先写一个能复现的最小用例。

## 二、调试顺序

1. 复现（给最小输入）。
2. 二分（注释掉一半 / `git bisect`）。
3. 打印或断点（`print` / `pdb` / `dlv` / `gdb`）。
4. 假设 → 验证 → 收敛。

```bash
python -m pdb script.py
dlv debug ./cmd/app -- --flag
node --inspect-brk app.js
```

## 三、写代码的硬要求

- 完整可运行，不留 TODO、不留 `...`。
- 参数真实值或明确占位符。
- 错误处理到位：网络、文件、空值、超时。
- 有依赖给安装命令。
- 注释只解释 why，不解释 what。

## 四、架构判断

| 症状 | 处理 |
|---|---|
| 一处改动牵动五处 | 抽接口，隔离变化点 |
| 测试越来越慢 | 拆纯函数，外部依赖打桩 |
| 状态到处飞 | 收拢到单一 store / 状态机 |
| 循环依赖 | 引入事件或中间层 |
| 部署靠手工 | 写脚本 + 幂等 |

## 五、常用骨架

```python
# CLI
import argparse
def main():
    p = argparse.ArgumentParser()
    p.add_argument('target'); p.add_argument('-o', '--out', default='out.txt')
    a = p.parse_args()
    ...
if __name__ == '__main__':
    main()
```

```go
// HTTP 服务
http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
log.Fatal(http.ListenAndServe(":8080", nil))
```

## 六、部署

```bash
# 单文件二进制 + systemd
go build -o /usr/local/bin/app ./cmd/app
# 静态站点
python -m http.server 8080 --directory dist
```

## 七、验收

改动可运行、测试通过、回滚路径明确（`git stash` / 备份文件 / 开关）。
