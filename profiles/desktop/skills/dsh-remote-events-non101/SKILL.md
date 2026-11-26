---
name: dsh-remote-events-non101
description: DSH Remote 网关 degraded / eventsOk false / 事件流 non-101 的定位与修复：先分清面板误报、cookie 失效、路径废弃三种假象，再用 /diagnostics 的 apiFlavor 定死因（探测超时太窄导致永远 unknown），含两处 gateway.cjs 补丁与验收命令
whenToUse: DSH Remote 网关 /health 返回 degraded、eventsOk:false、events.mux/host 的 connected:false 且 lastError 是 "Received network error or non-101 status code." 时
tags: dsh, dsh-remote, gateway, websocket, troubleshooting
---

## 何时用

DSH Remote（dsh-remote-plugin）网关 `/health` 返回 `status: degraded`、`readiness.eventsOk: false`，`events.mux/host` 的 `connected: false` 且 `lastError` 形如 `Received network error or non-101 status code.`，但设备其实能连上、能看会话。

## 先别猜，按顺序排掉三种假象

网关上「连不上」有四种完全不同的成因，必须先分清，否则会修错地方。

### 1. 面板红字 ≠ 网关故障
设置页/控制台里那句 `连不上 DSH：<message>` 来自 **dsh-console-hm** 面板，不是网关。查：

```bash
TOK=$(python -c "import json;print(json.load(open(r'C:\Users\<user>\.dsh\dsh-console-token.json'))['token'])")
curl -s "http://127.0.0.1:8899/dsh-console/info?token=$TOK"
```

`dshOk:false` 而且 `dshError` 是 `The operation was aborted due to timeout` → 是控制台插件的启动探活误报，见第 2 条，与网关无关。

### 2. cookie 是否还有效
```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "cookie: $(cat ~/.dsh-remote/dsh-upstream.cookie)" http://127.0.0.1:63753/
```
200 = cookie 有效（那就不是认证问题）；401 = cookie 失效。

### 3. 上游 WS 路径是否还存在（关键分水岭）
新版 DSH 把 WS 统一到 **`/api/remote.mux`**；`/api/events.mux`、`/api/events.host` 是**旧版路径，新版已删除**。用裸 http 升级探测确认：

```js
// /tmp/wsup.mjs —— 用 node 跑，别用 curl（curl 看不出发改帧结果）
import http from 'node:http'; import fs from 'node:fs'
const cookie = fs.readFileSync('C:/Users/<user>/.dsh-remote/dsh-upstream.cookie','utf8').trim()
const probe = (path, extra) => new Promise(r => {
  const req = http.request({ host:'127.0.0.1', port:63753, path,
    headers:{ Connection:'Upgrade', Upgrade:'websocket', 'Sec-WebSocket-Version':'13',
      'Sec-WebSocket-Key':'dGhlIHNhbXBsZSBub25jZQ==', ...extra } })
  const t = setTimeout(()=>{ r(path+': timeout'); req.destroy() }, 6000)
  req.on('upgrade',(res,s)=>{ clearTimeout(t); r(path+': UPGRADE '+res.statusCode); s.destroy() })
  req.on('response',res=>{ clearTimeout(t); r(path+': HTTP '+res.statusCode) })
  req.on('error',e=>{ clearTimeout(t); r(path+': err '+e.code) }); req.end()
})
console.log(await probe('/api/remote.mux', { cookie }))   // 期望 UPGRADE 101
console.log(await probe('/api/events.mux', { cookie }))   // 新版会 ECONNRESET / 404
```

`/api/remote.mux` 带 cookie 返回 **101** 就证明路径与认证都正常，问题在网关的路径选择上（继续看第 4 条）。

### 4. 网关到底选了哪套采集器 —— 一眼定死因
```bash
TOK=$(cat ~/.dsh-remote/token)
curl -s -H "authorization: Bearer $TOK" http://127.0.0.1:8787/diagnostics
```

看 `upstream` 三个字段：

| `apiFlavor` | `collectorFlavor` | 含义 |
|---|---|---|
| `modern` | `modern` | 正常，走 `/api/remote.mux` |
| `unknown` | `unknown` | **就是这里出问题**：探测失败，退回旧采集器连已废弃路径 |
| `legacy` | `legacy` | 真·老版 DSH |

再看 `checkedAt`：如果它停在**网关启动那一刻**、几小时没动，说明**探测失败一次后永远不会再探** —— 这是 0.8.8 的缺陷（`startCompatibleEventCollectors()` 只有 flavor 变化才重启采集器，而 unknown 不会自行改变）。

## 真凶：探测窗口比上游响应还短

`gateway.cjs` 里探测用的是 `session/list` 这个重接口，超时硬编码 `Math.min(2500, UPSTREAM_REQUEST_TIMEOUT_MS)`。与会话多的机器上 `session/list` 实测要 **3～9 秒**（861 个会话文件），2.5 秒必然超时 → `apiFlavor` 永远 `unknown` → 永远走旧采集器 → 永远 `non-101`。

先量一下真实耗时再决定放宽多少：
```bash
cat > /tmp/probe.mjs <<'EOF'
import fs from 'node:fs'
const cookie = fs.readFileSync('C:/Users/<user>/.dsh-remote/dsh-upstream.cookie','utf8').trim()
const t0 = Date.now()
const r = await fetch('http://127.0.0.1:63753/api/session/list', {
  method:'POST', headers:{'content-type':'application/json', cookie},
  body: JSON.stringify({type:'client-request', rpcId:crypto.randomUUID(),
    method:'session/list', payload:{ args: { _request:{} } }}),   // 注意：args 必须是单层对象，不能是数组
})
console.log('status', r.status, 'ms', Date.now()-t0)
EOF
node /tmp/probe.mjs
```

## 两处补丁（`node_modules/dsh-remote-plugin/gateway.cjs`）

改前备份；两处都改完 `node --check gateway.cjs`。

**A. 放宽探测超时**（根因修复）
```js
// 找：const signal = AbortSignal.timeout(Math.min(2500, UPSTREAM_REQUEST_TIMEOUT_MS))
const signal = AbortSignal.timeout(Math.min(UPSTREAM_API_FLAVOR_PROBE_TIMEOUT_MS, UPSTREAM_REQUEST_TIMEOUT_MS))
```
```js
// 在 const UPSTREAM_API_FLAVOR_RECHECK_MS = ... 那行后面加
const UPSTREAM_API_FLAVOR_PROBE_TIMEOUT_MS = durationEnv('DSH_REMOTE_FLAVOR_PROBE_TIMEOUT_MS', 20_000, 2_000, 5 * 60_000)
```
（`durationEnv` 已在 gateway.cjs 里定义，别自己写解析。）

**B. 加口味看门狗**（防止 unknown 永久冻结）
```js
// 在 startCompatibleEventCollectors() 函数结束（eventCollectors.host = startEventCollector('host') 之后的 } 之后）插入
const COLLECTOR_FLAVOR_WATCH_MS = durationEnv('DSH_REMOTE_FLAVOR_WATCH_MS', 20_000, 5_000, 5 * 60_000)
let collectorFlavorWatchTimer = null
function startCollectorFlavorWatchdog() {
  if (collectorFlavorWatchTimer) return
  collectorFlavorWatchTimer = setInterval(() => {
    try { if (upstreamApiFlavor === 'unknown') void detectUpstreamApiFlavor(true).catch(() => {}) } catch {}
  }, COLLECTOR_FLAVOR_WATCH_MS)
  collectorFlavorWatchTimer.unref?.()
}
```
```js
// 启动处：找 "void startCompatibleEventCollectors()"（在 gateway worker 启动块里），下面加
startCollectorFlavorWatchdog()
```

## 生效与验收

```bash
# 1. 重启网关（插件重载不一定重启网关进程）
powershell.exe -NoProfile -Command "Stop-Process -Id (Get-Content 'C:\Users\<user>\.dsh-remote\plugin-gateway.pid') -Force"
sleep 30

# 2. 看口味是否定下来
TOK=$(cat ~/.dsh-remote/token)
curl -s -H "authorization: Bearer $TOK" http://127.0.0.1:8787/diagnostics
# 期望: upstream.apiFlavor="modern", collectorFlavor="modern",
#       events.mux/host 的 connected=true, lastError=""

# 3. 看整体健康
curl -s "http://127.0.0.1:8787/health?probe=fresh"
# 期望: status="ready", readiness={ok:true, upstreamOk:true, eventsOk:true}
```

**稳定性判据**：等 60 秒再查一次，`reconnects` **数字不变**才算稳（增长说明还在重连）。

## 附带修：面板红字（dsh-console-hm）

如果第 1 条里 `dshOk:false`，是 `lib/index.js` 的 `dshOk` 只在启动时置位一次、`/sessions` 成功时不回写的缺陷。修法：加 `markDshOk()/markDshFail()/probeDshAuto()`，在 `/sessions` 成功分支、启动重试、`getInfo()` 里都回写状态。改完不需要重启宿主，用 `plugin_manager set_plugin` 对 `include:dsh-console` 先 `enabled:false` 再 `enabled:true` 即可热重载，验证：

```bash
curl -s "http://127.0.0.1:8899/dsh-console/info?token=$TOK"   # 期望 dshOk:true, dshError:""
```

## 坑

- **别对整个 `node_modules` 做无界 grep**，120s 超时；先 `grep -rn "关键词" . --include=*.cjs`。
- **`~/.dsh-remote/plugin-gateway.pid` 里的 PID 可能已过期**，先用 `Get-Process -Id` 确认还活着再 Stop。
- **网关跑的是 `D:\Program Files\nodejs\node.exe`（v22.20.0）**，不是你 shell 里的 node 24。同一段 fetch 在两个版本上耗时差很大，测耗时要用网关那个 node：`"/d/Program Files/nodejs/node.exe" /tmp/probe.mjs`。
- **launch token 是进程内内存 Map**，无法从磁盘取回，别浪费时间。
- curl 的 `-o` 重定向在 MSYS 下 `/tmp` 与 Windows python 看到的路径不同；要解析 JSON 就用 `cygpath -w /tmp/x.json` 转成 Windows 路径再传给 python。
- 网关重启后 supervisor（PID 44952）不会自动拉起新网关？实测会 —— `plugin-gateway.pid` 会变回同一个 8804 值前先确认进程启动时间已更新。
