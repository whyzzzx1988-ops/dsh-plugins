---
name: workbench-diy-module-pipeline
description: 在工作台 DIY 工坊里从建包到过快照（check + design check）的完整流程与踩坑清单。当要新建/改造工作台模块、面板卡片空白或显示不对、check 判据报错、design.json/readme.json 填不完整、模块装不上或热替换不生效时加载。
whenToUse: 接到工作台模块（workbench module / unit / 面板卡片）相关任务时；或 workbench_diy_install 报「当前没有调试状态」、check 判据未通过、design check 报「（待填）」或 JSON 非法时。
tags: workbench, diy, module, dsh, pipeline
---

# 工作台 DIY 模块：从建包到过快照

一次真实走完的记录（`dsh-news` 模块：从"读项目目录"改造成"读 GitHub Releases 显示 10 条版本资讯"）。踩过的坑都标了 ⚠️。

---

## 0. 开工前先判三件事（省 90% 的坑）

### 0.1 必须用「工作台 DIY」预设，不要用普通会话 ⚠️⚠️⚠️

**这是本次最贵的坑。** 工作台这版（core 1.5.2）给所有工具加了前置门禁：

```js
// core/dist/host/index.js:14843 debugPrecheckOf()
if (debugOf === void 0) return void 0;
if (held === null) return debugRefusalText("none");   // → "当前没有调试状态。"
```

没有调试态，`workbench_diy_install` / `workbench_diy_show` / `workbench_panels_show` / `workbench_modules_install` **全部**被顶回 `Error: 当前没有调试状态。`

而开调试的四把工具（`workbench_diy_debug_start` / `_pause` / `_resume` / `_stop`，见 index.js:13779-13782、25678-25682）**只在工作台 DIY 预设里暴露**。普通会话里它们连工具表都不在，`ops_discover_tools` 也找不到；调试态是 `createDebugStore()` 的**进程内存态**（index.js:3589），不落盘，外部改文件写不进去。

> 判据：工具表里有没有 `workbench_diy_debug_start`？没有 → 立刻换 DIY 预设重开，**不要**去改 profile 配置"手工安装"绕行。绕行能装上，但后面每次 build 同步、面板识别都要靠手改文件，代价远高于换个会话。

### 0.2 先看一眼现在面板里有什么

```
workbench_toolbox_open(["diy", "manage"])     # 工具包默认一把不进上下文，先开
workbench_diy_status                          # 列出已装模块、产物时间、下一步建议
workbench_diy_panel                           # 面板运行态
workbench_modules_list                        # 模块目录
```

### 0.3 判「要不要做模块」

| 主人说的 | 去向 |
|---|---|
| 有没有现成的 | 装现成的，别写 |
| 就这一次 / 我现在想看 | 直接回答，别做模块 |
| 每天看一次 / 盯着它 / 卡住告我 | 定时任务，不是模块 |
| 想在面板上一直看到 X | 做模块 |
| 只是面板空白/卡片不对 | 先修，别新建 |

---

## 1. 建包

```bash
cd <工作区>            # 形如 C:\Users\<user>\.dsh\workbench\diy
pnpm exec dsh-wb-module init <unit> --dir packages/module-<unit> \
  --template diy --description "<一句话>"
```

- `<unit>` 是模块标识（kebab-case，如 `dsh-news`），**唯一**，改它要连清单、路由、面板配置一起改。
- 只有 `diy` 一个模板。
- 建完先 `pnpm install`（工作区根），否则 `node_modules/.bin` 里没有 `jscpd`（⚠️ 根 `.bin` 只有 `dsh-wb-module`/`tsc`/`vitest`）。

**工作区根 `package.json` 里不要用 `node -e` 复杂脚本**，也不要在包里另装 `dsh-wb-module`（会出现两代二进制，静默错乱）。

---

## 2. 契约：清单 + 两个面 + 三张表

`packages/module-<unit>/package.json` 的 `dsh` 段是唯一真源：

```json
"dsh": {
  "client": {
    "platform": "web",
    "inject": ["@dsh-workbench/core"],
    "external": ["@dsh-workbench/core/client", "@deepseek-ai/dsh-client-ui-primitives"]
  },
  "workbench": {
    "apiVersion": 3,
    "unit": "dsh-news",
    "title": { "zh": "…", "en": "…" },
    "card": { "order": 90 },
    "tools": [
      { "name": "dsh-news_run",      "writes": false, "key": "run" },
      { "name": "dsh-news_add_note", "writes": true,  "key": "addNote" }
    ],
    "host": { "inject": [] }
  },
  "workbenchFaces": { "host": "src/host.ts", "client": "src/client.tsx" }
}
```

三条硬规矩：

1. **工具名只有一个来源**。清单里写 `tools`，跑 `dsh-wb-module sync` 生成 `src/declared-tools.ts`，代码里引用 `DECLARED_TOOLS`，**不要手写字符串**。
2. **`writes:true` 的工具必须走审批**。宿主侧用 `writeApprovalOf`，卡片侧用 `useHostWrite`。声明了写却不接入审批 → `seam` 判据不过。
3. **不要声明 `dsh.bundle`**。私有包声明了会被 `combo` 判据拦（装载只走 profile 依赖）。

两个面：
- `src/host.ts` — `defineUnitHostPlugin`，`routes` / `registerTools` / `actions` / `factsOf`
- `src/client.tsx` — 卡片组件，`inject: ['workbenchUnits']`

---

## 3. 写代码的推荐分层

照 `dsh-news` 的结构，判据最友好：

```
src/
  model/          纯函数，零副作用 ← 全部要有同名 __tests__/*.test.ts
    <feature>.ts    常量 + 类型 + parse/state 函数
    phase.ts        五态收敛（见下）
  host/
    <feature>.ts    fetch / 读写，注入 options 便于测试
  components/
    <Feature>Body.tsx        按 state.kind 分态渲染
    <Feature>Body.module.css 只用已验证令牌
    OverviewCard.tsx         组装：h() 调 Body + 其他 Section
  messages.ts      zh/en 两套 key
```

### 3.1 五态收敛抽公共函数（否则 jscpd 必挂）⚠️

每个数据源都有 `idle / loading / error` 三个分支长得一模一样。**第二个数据源出现时就抽**：

```ts
// src/model/phase.ts
export type Phase = 'idle' | 'loading' | 'ready' | 'error'
export interface PhaseInput { phase: Phase; error?: { code: string; message: string } }
export type PhaseState = { kind: 'idle' } | { kind: 'error'; detail: string } | null

export function settledPhaseOf(input: PhaseInput): PhaseState {
  if (input.phase === 'idle') return { kind: 'idle' }
  if (input.phase === 'error') {
    const e = input.error
    return { kind: 'error', detail: e === undefined ? '' : `${e.code}: ${e.message}` }
  }
  return null
}
```

调用侧两行：

```ts
const settled = settledPhaseOf(input)
if (settled !== null) return settled
```

⚠️ 连续两次插入 `import { settledPhaseOf } from './phase'` 会 `TS2300 Duplicate identifier`——只留顶部一行。

### 3.2 数据源规范

```ts
export const RELEASES_ROUTE = '<unit>/<feature>'      // 路由前缀固定 "<unit>/"
export const RELEASES_TIMEOUT_MS = 12_000             // 必须有超时
```

宿主侧 fetch 要带齐：`User-Agent`（模块名）、`Accept`、`AbortSignal.timeout(...)`、非 2xx 抛 `` `GitHub API ${status} ${statusText}` ``。

**降级比报错重要**：模块级缓存 `let cached`，请求失败但有缓存 → 返回旧数据 + `stale: true`，卡片显示「网络不可用 · 显示缓存」。这条会进 `design.json` 的 states。

⚠️ 时间注入写成 `now: () => number`（即 `Date.now`），不要 `() => new Date()`——后者 `fetchedAt` 会 `TS2322`。

### 3.3 CSS 令牌只认清单里的 ⚠️

- 工作台 1.5.2 **没有** `--wb-color-*`（只有 `--wb-len-*` / `--wb-dur-*` / `--wb-font-*`）。
- 颜色用 dsh 主题别名：`--dsw-alias-border-l1`（边框）、`--dsw-alias-label-tertiary`（弱化文字）、`--dsw-alias-label-primary`、`--dsw-alias-bg-layer-1..3` 等。
- 查真实清单：

```bash
grep -o "dsw-alias-[a-z0-9-]*" <core>/client.js | sort -u
```

挂了 `--wb-color-border` 这类幻觉令牌 → `style` 判据报「样式归属 2 条…不在令牌清单」。

### 3.4 外链只用 kit 的 Link

```ts
h(Link, { href: release.url }, t('<unit>.releaseOpen'))
```

`Link` 自带新窗口 + `rel` + 箭头，别自己写 `→`、别自己加 `target`。`kit.components` 里确认有：`Link` / `StateBlock` / `Rows` / `Row` / `CenteredState` / `EmptyState`。

### 3.5 提示文案一律进 messages.ts

`src/messages.ts` zh/en 两套，key 形如 `'<unit>.<name>'`。**别在组件里写中文**，否则 `cards` 判据的 zh/en 双跑会露出裸键名。

---

## 4. 工具链循环（每次改完 src 都跑）

```bash
cd packages/module-<unit>
../../node_modules/.bin/dsh-wb-module build     # 先生成产物
../../node_modules/.bin/tsc --noEmit            # 类型
../../node_modules/.bin/vitest run              # 测试
../../node_modules/.bin/dsh-wb-module check     # 15 条判据（读产物！）
```

⚠️ **check 必须在 build 之后跑**，它读 `dist/host.js` 与 `client.js`。改完 src 直接 check = 校验旧产物，白跑。

⚠️ `jscpd` 不在 `check` 里，单独跑：

```bash
./node_modules/.bin/jscpd src scripts     # 先确认包内装了 node_modules
```

目标：`Found 0 clones`。

### 15 条判据速查（`dsh-wb-module check --list`）

| 判据名 | 名字 | 常见失败原因 |
|---|---|---|
| contracts | 模块契约 | 单元 id 重复 / 面文件不存在 / 清单与代码注册对不上 |
| protocol | 模块声明协议 | apiVersion 不是 3 / 静态半有生字段 |
| combo | 不声明 dsh.bundle | 私有包声明了 → 删 |
| bundles | 模块产物边界 | 宿主产物混进浏览器代码 / 浏览器产物内联 CSS |
| source | 源码边界与零注释 | **源码里有注释**（连 `//` 说明都算）/ 手写原子写 |
| seam | 执行缝（写入域） | 直接 `child_process` / 声明 writes 没接审批 |
| arch | 模块架构 | 层序违规 / 没有 `arch.config.mjs` |
| lint | 代码卫生 | eslint error |
| primitives | dsh 原语 | dsh 包没进 `external` |
| kit | 工作台 kit 面 | peer 下限低于实际用的 API |
| cards | 卡片渲染 | 8 态 × zh/en 抛异常 / 空白 / 显示 `undefined` / 裸键名 |
| standalone | 独立构建 | 工作区有 core 源码时才有意义 |
| markers | 公开包无内部标识 | 公开包里出现私网 IP / 内部域名 |
| style | 样式归属 | 定义 `wb-*` 规则 / 令牌名不在清单 / 手写表单 |
| alias | 不指向工作台 | src 里有 `@/` |

**总计 12 通过 · 3 不适用 · 0 未通过** 是私有包工作区里的正常终态（不适用的三条：`combo` / `standalone` / `markers`）。

### 两条最反直觉的判据 ⚠️

1. **`source`：源码零注释**。任何 `//` 说明都会被判违规，注释只允许出现在 `**/*.md`。
2. **`arch`：每个实现文件必须有同名配对测试**。`src/model/foo.ts` 必须有 `src/model/__tests__/foo.test.ts`，而且**必须被真的 import 到**（无人引用的文件算死文件）。同理组件被 import 了但入口到不了 → 报「死代码」。

---

## 5. 三张表：design.json / readme.json

`design.json` 与 `readme.json` 里的 `（待填）` 不清零，`pnpm selfcheck` 与 `design check` 不会过。

### design.json 五段（缺一不过）

```json
{
  "unit": "dsh-news",
  "name": "…",
  "oneLine": "…",
  "panel":  [ { "sees": "…", "from": "…" } ],
  "states": {
    "idle":       { "sees": "…", "canDo": "…", "agentCan": "…" },
    "loading":    { … }, "ready": { … }, "empty": { … }, "unreadable": { … }
  },
  "config": [ { "key": "limit", "where": "prefs", "default": 5, "choices": [1,5,10,20,50], "clamp": 50 } ],
  "capabilities": [ { "tool": "dsh-news_run", "writes": false, "when": "…" } ],
  "linkage": [ { "change": "点刷新", "then": "…" } ],
  "datasource": { "endpoint": "…", "headers": [], "auth": "匿名", "failure": "…", "timeoutMs": 12000, "probe": "curl …" },
  "writes": [],
  "acceptance": [ { "text": "…", "checked": true } ]
}
```

### readme.json 的**字数上限是 70 字/条** ⚠️

`do` / `data` / `trouble` 每条超过 70 字就报「…超长」。拆条，不要删信息。

### ⚠️ 手改这两个 JSON 极易留尾随逗号

```json
"text": "…",
},          ← 这个逗号让 JSON 非法
```

报错形如 `✖ readme.json 不是合法 JSON：Unexpected token ']'`。**改完必须**：

```bash
node -e "JSON.parse(require('fs').readFileSync('readme.json','utf8'))" && echo OK
```

### 渲染与验收

```bash
dsh-wb-module design check     # 三张表空不空、README 是否最新
dsh-wb-module design render    # 生成 DEVELOPING.md 的那段 + 重新生成 README.md
dsh-wb-module design accept    # 勾选验收清单（acceptance 逐条 checked）
```

顺序：**先 check 清零 → 再 render**。render 之前 README/DEVELOPING 永远是"落后"的。

⚠️ `README.md` 是 `readme.json` 生成的，**不要手改**，下次 render 会覆盖。

---

## 6. 装到自己机器上（profile 同步）

```bash
workbench_diy_status unit=<unit>     # 看"安装否 / 产物时间 / 下一步建议"
workbench_diy_install unit=<unit>    # 首次装
```

⚠️ **profile 里是实体拷贝，不是软链**。即便 profile `package.json` 写着 `"link:../../workbench/diy/packages/module-<unit>"`，`C:\Users\<user>\.dsh\profiles\desktop\node_modules\@dsh-workbench\module-<unit>` 仍是**独立文件**，build 之后要手动同步：

```bash
cd packages/module-<unit>
P=/c/Users/<user>/.dsh/profiles/desktop/node_modules/@dsh-workbench/module-<unit>
cp dist/host.js client.js package.json CHANGELOG.md README.md DEVELOPING.md "$P/"
```

⚠️ 同步后 `workbench_diy_status` 会短暂报 **「产物比运行中的实例新：热替换没有生效」**——**这是正常中间态**，等 5–10 秒再查，通常会变成「均已生效」。别急着判定失败、别重复安装。

### 面板显示配置

```
C:\Users\<user>\.dsh\workbench\workspaces\<workspace-id>\panels\config.json
{"shown":["dsh-news","hello"],"hidden":[],"order":["dsh-news","hello"]}
```

⚠️ 装新模块时**不要**把原有模块挪进 `hidden`，加进 `shown` 就行。改前备份 `config.json.bak`。

---

## 7. 验收：直接打路由，不要靠"看页面"

宿主 API 前缀 **`/workbench/api`**（core `index.js:44`）。

```bash
curl -s "http://127.0.0.1:<port>/workbench/api/<unit>/<feature>" | head -c 300
```

期望：`{"ok":true, …真实数据…}`。四类路由都该是 200：`<feature>` / `notes` / `prefs` / `overview`。

拿到真数据才算做完；页面看起来对但路由 500 = 没做完。

---

## 8. 踩坑清单（速查）

### shell / 环境

| 坑 | 现象 | 解法 |
|---|---|---|
| `node -e "...=>..."` | `SyntaxError: Unexpected token ','` | MSYS 吞了 `=>`，改用单引号包整个脚本：`node -e 'fetch(...).then(...)'` |
| 重定向到 `/tmp/x.json` | 文件"写成功"但读不到 | Windows 上没有 `/tmp`，写到工作区相对路径 |
| `cmd //c "dir xxx"` | 输出被截断 | 用 `ls -la` |
| 包内无 node_modules | 找不到 `jscpd` | 在工作区根 `pnpm install --ignore-scripts` |

### 构建

| 坑 | 现象 | 解法 |
|---|---|---|
| 改完 src 直接 check | 判据全过但页面没变 | 先 `build` 再 `check` |
| 两个 `import` 同一符号 | `TS2300 Duplicate identifier` | 只留顶部一行 |
| `useLongTask(unitId)` | `TS2345` | 签名是对象：`useLongTask({unit, workspace})` |
| 时间注入用 `() => new Date()` | `TS2322` | 用 `() => Date.now()` |
| CSS 用 `--wb-color-*` | `style` 判据报令牌不在清单 | 换 `--dsw-alias-*` |
| 源码写注释 | `source` 判据报零注释违规 | 注释移进 `.md` |
| 新增 model 文件没测试 | `arch` 判据报无同名配对测试 | 补 `__tests__/<name>.test.ts` |
| 两处 idle/error 分支复制 | jscpd 报重复 | 抽 `settledPhaseOf` |
| 重写组件误删 `RunSection` | 判据报「注册了长任务但产物里没有 useLongTask」 | 恢复引用，别只删不补 |

### 文档

| 坑 | 现象 | 解法 |
|---|---|---|
| 手改 readme.json 留尾随逗号 | `Unexpected token ']'` | 每次改完 `node -e "JSON.parse(…)"` 验一遍 |
| readme 某条超 70 字 | `design check` 报超长 | 拆成两条，别删信息 |
| 先 render 后 check | README 永远"落后" | 先 check 清零再 render |
| 手改 README.md | 下次 render 被覆盖 | 只改 readme.json |

### 安装 / 面板

| 坑 | 现象 | 解法 |
|---|---|---|
| 用普通会话调 install | `当前没有调试状态。` | 换工作台 DIY 预设 |
| build 后没同步 profile | 面板还是旧内容 | `cp` 六个文件到 profile 模块目录 |
| 同步后立刻查状态 | 「热替换没有生效」 | 等 5–10 秒，这是正常中间态 |
| 装新模块动了 hidden | 原模块消失 | 只往 `shown` 加，不动别人 |

---

## 9. 完工标准（缺一不算完）

```
✔ tsc --noEmit 干净
✔ vitest run 全过
✔ jscpd 0 clones
✔ dsh-wb-module build 成功
✔ dsh-wb-module check → 0 未通过
✔ dsh-wb-module design check → 三张表齐全、README/DEVELOPING 最新
✔ 设计表 acceptance 逐条 checked
✔ 路由实测返回真实数据（不是空壳）
✔ profile 已同步、面板 shown 含本模块
```

九条全绿再交付。缺 `design` 那两条最容易被忘——它不影响功能，但模块"看起来半成品"。

---

## 10. 一句话版本

> 用 DIY 预设开、`init` 建包、清单定契约、model/host/components 三层写、每个实现文件配同名测试、零注释、令牌只用清单里的；build→check→test→jscpd 四连；design.json/readme.json 把 `（待填）` 清干净（每条 ≤70 字、别留尾随逗号）再 render；装的时候记得 profile 是实体拷贝要手 `cp`；最后直接 curl 路由看真数据。
