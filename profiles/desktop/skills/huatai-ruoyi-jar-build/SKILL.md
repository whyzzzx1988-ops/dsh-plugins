---
name: huatai-ruoyi-jar-build
description: 在华泰海事 huatai_gg_mgr（RuoYi-TDesign）上拉取 dev 最新代码并本地 clean package 出可执行 jar，含 JDK17 覆盖、settings 指定、必须 clean 的坑、git 凭据助手缺失的绕法、profile 占位符机制、产物校验清单。
whenToUse: 收到「打包 jar」「重新打个包」「拉最新代码打一下」这类只做本地构建、不做镜像/部署的任务时加载。
tags: java, maven, ruoyi, huatai, build, jar, git-credential
---

# 华泰海事 huatai_gg_mgr 本地打 jar

只做本地打包。不建镜像、不推 Harbor、不部署 K8s、不上传 xftp —— 除非主人另外说。

## 一、环境事实（已逐条实测，别凭印象改）

| 项 | 值 | 坑 |
|---|---|---|
| 工程根 | `D:/workproject/gitlab/huataiserv/huatai_gg/huatai_gg_mgr` | 用户口头常写成 `D:\workproject\gitlab\huatai\huatai_gg\...`，**实际是 `huataiserv`** |
| 分支 | `dev` | |
| 系统 JAVA_HOME | `C:\Program Files\Java\jdk1.7.0_80`（**JDK7**） | 不覆盖必炸，先 `export JAVA_HOME="D:/Program Files/Java/jdk-17"` |
| JDK17 | `D:/Program Files/Java/jdk-17` | 实测 `java 17.0.6` LTS |
| Maven | `D:/maven/apache-maven-3.6.3/bin/mvn.cmd` | |
| settings | `D:/maven/apache-maven-3.6.3/conf/settings_ruoyiai.xml` | 必须带 `-s`，私有仓地址在这个文件里 |
| 产物 | `ruoyi-admin/target/ruoyi-admin.jar` | `ruoyi-admin/pom.xml:149` 的 `finalName=${project.artifactId}`，约 248 MB |
| git | `2.56.0.windows.4.niugit`，来自 `winuxcmd/opt/niugit` | `git branch --show-current` 可用；但 **PATH 里没有 GCM**（见下） |

**模块数量别搞混**：根 `pom.xml` 只有 4 个 `<module>`（ruoyi-admin / ruoyi-common / ruoyi-extend / ruoyi-modules），
它们是聚合模块，展开后 reactor 共 **40 个**。看构建日志要认「Reactor Summary」那一段，不是根 pom 的 module 数。

## 二、标准流程

### 1. 拉代码（先看凭据）

```bash
cd "D:/workproject/gitlab/huataiserv/huatai_gg/huatai_gg_mgr"
git status --short          # 确认工作区干净，未跟踪文件不要动
git branch --show-current   # 应为 dev
git log -1 --format="%h %ad %s" --date=iso
```

**坑（2026-11-25 实测）**：这个 DSH/MSYS 环境的 git 没挂 credential helper，
`git fetch` 直接报

```
warning: Ignoring unavailable SSL backend 'openssl'; using 'schannel' instead
error: failed to execute prompt script (exit code 1)
fatal: could not read Username for 'http://gitlab.huatai1993.com': No such file or directory
```

但 Windows 凭据库里明明有 `LegacyGeneric:target=git:http://gitlab.huatai1993.com`（用户 `huatai`），
`cmdkey /list` 能看到。

`git -c credential.helper=manager` **也不行**，报 `git: 'credential-manager' is not a git command`
—— 因为这把 git 的 exec-path 在 `winuxcmd/opt/niugit/mingw64/libexec/git-core`，PATH 里根本没有 GCM。
GCM 实体在 `C:/Program Files/Git/mingw64/bin/git-credential-manager.exe`（同目录还有
`git-credential-helper-selector.exe`）。

**两种绕法，都实测 exit 0，都不改全局配置：**

单条命令（临时用）：

```bash
git -c credential.helper='!f() { "C:/Program Files/Git/mingw64/bin/git-credential-manager.exe" "$@"; }; f' fetch origin dev
```

脚本里批量用（更简洁，环境变量只作用于当前 shell）：

```bash
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=credential.helper
export GIT_CONFIG_VALUE_0='!"C:/Program Files/Git/mingw64/bin/git-credential-manager.exe"'
git ls-remote origin refs/heads/dev   # 验证：应输出 776365de... refs/heads/dev
```

拉完核对：

```bash
git rev-parse HEAD origin/dev           # 两个 sha 应一致
git rev-list --count HEAD..origin/dev   # 应为 0，大于 0 才需要 pull
```

注意 `.git/packed-refs` 里的 `origin/dev` 可能是旧值（本次是 `d213a762`），
`.git/refs/remotes/origin/dev` 是新值 —— **以 `git rev-parse origin/dev` 为准**，别去 cat packed-refs 下结论。

### 2. 判断要不要重打

```bash
ls -l --time-style=full-iso ruoyi-admin/target/ruoyi-admin.jar
git log -1 --format="%ad" --date=iso
```

jar 时间早于最新提交时间就必须重打（实测案例：jar 12:37，提交 20:29，差 8 小时）。
**「BUILD SUCCESS 过」不代表产物是新的**，每次都按时间对一遍。

### 3. 打包

```bash
export JAVA_HOME="D:/Program Files/Java/jdk-17"
"D:/maven/apache-maven-3.6.3/bin/mvn.cmd" -s "D:/maven/apache-maven-3.6.3/conf/settings_ruoyiai.xml" clean package -Dmaven.test.skip=true
```

（上面是单行；写成多行续行时反斜杠只能有一个 `\`。）

- 40 个 reactor 模块，约 3.5 分钟（实测 03:32），结尾 `BUILD SUCCESS` + 全模块 SUCCESS。
- **`clean` 绝对不能省**。省了会这样炸：

```
程序包org.dromara.common.core.constant不存在
程序包org.dromara.common.core.utils不存在
找不到符号  类 DictService
```

  根因**不是代码坏了**，是模块间依赖取到了 target 里的旧 class。全量 clean 一次就过。
  （曾因此误判业务代码有问题，白查半小时 —— 见到这个报错先 clean，别去翻 java 文件。）

- 生产包加 `-Pprod`。

### 4. profile 机制（为什么必须重新打包才能换 profile）

`pom.xml` 定义了三个 profile：`local` / `dev` / `prod`，其中 **`dev` 带 `<activeByDefault>true</activeByDefault>`**
（`pom.xml:88-91`），所以不带 `-P` 就是 dev。

`ruoyi-admin/src/main/resources/application.yml:67` 写的是：

```yaml
  profiles:
    active: @profiles.active@
```

这是 **Maven 资源过滤占位符**（`@...@`），构建时被 pom 里的 `<profiles.active>` 属性替换成字面量，
打进 jar 就是死值。所以：

- 想换 profile，**只能加 `-Pprod` 重新打包**，运行时 `--spring.profiles.active=prod` 也能盖，但 jar 里那个值不会变；
- 别指望改 yml 源文件里的 dev —— 那里根本没有 dev，是占位符。

### 5. 校验产物（必须做，别看 BUILD SUCCESS 就交）

```bash
rm -rf /tmp/jarchk && mkdir -p /tmp/jarchk && cd /tmp/jarchk
"D:/Program Files/Java/jdk-17/bin/jar" xf "D:/workproject/gitlab/huataiserv/huatai_gg/huatai_gg_mgr/ruoyi-admin/target/ruoyi-admin.jar" META-INF/MANIFEST.MF BOOT-INF/classes/application.yml
cat META-INF/MANIFEST.MF
grep -n -A2 "profiles" BOOT-INF/classes/application.yml | head
```

期望：

```
Main-Class: org.springframework.boot.loader.launch.JarLauncher
Start-Class: org.dromara.DromaraApplication
Build-Jdk-Spec: 17
Spring-Boot-Version: 3.4.4
```

以及 `application.yml` 里 `spring.profiles.active: dev`（第 67 行附近，应该是**字面量 dev/prod，不是 `@profiles.active@`**）。
若还是 `@profiles.active@`，说明资源过滤没生效，jar 是坏的，别交。

打完删掉 `/tmp/jarchk`。

## 三、交付时要说清的三件事

1. **产物路径 + 大小 + 构建时间**
2. **对应哪个 commit**（`git log -1 --format="%h %s"`），不然没人知道这个 jar 是哪版代码
3. **profile 是 dev 还是 prod** —— dev 包直连开发库，别误发生产

## 四、既有脚本

`script/bin/pull_and_build.sh`（10152 字节）+ `pull_and_build.bat`（1285 字节），
封装「探活 VPN/DNS → `git fetch` → 非快进检查 → `git pull --ff-only` → 打包 → 校验 jar 内 profile」。

默认值（脚本第 24-37 行，与上面完全一致）：
`BRANCH=dev`、`BUILD_JAVA_HOME=D:/Program Files/Java/jdk-17`、`MVN_CMD=D:/maven/apache-maven-3.6.3/bin/mvn.cmd`、
`MVN_SETTINGS=.../settings_ruoyiai.xml`、`PROFILE=dev`、`JAR_REL=ruoyi-admin/target/ruoyi-admin.jar`。

用法：

```bash
bash script/bin/pull_and_build.sh --once              # 只探活一次，没恢复退出码 2
bash script/bin/pull_and_build.sh                     # 守护模式，循环等网络恢复
bash script/bin/pull_and_build.sh --profile prod      # 打 prod 包
bash script/bin/pull_and_build.sh --dry-run           # 只探活+打印将执行的命令
```

它的网络判据是 `git ls-remote` 成功（DNS 只写日志）。**注意它用系统 git，同样会撞上面那个凭据坑** ——
跑之前先确认能 fetch，或先把 `GIT_CONFIG_*` 那三个环境变量 export 出去再跑。

本次（2026-11-25）没走脚本，是手工 fetch + 手工 mvn，因为要先确认 HEAD 是否已是最新。

## 五、同类任务清单

- [ ] 工作区干净、分支是 dev、未跟踪文件一个没动（本工程常驻 4 个未跟踪文件：两个 SQL + 两个构建脚本，别误删）
- [ ] fetch 成功且 `git rev-parse HEAD` == `git rev-parse origin/dev`
- [ ] jar 时间 >= 最新提交时间（否则重打）
- [ ] `clean package` 一次过，没有 common-core / DictService 的 class 缺失报错
- [ ] MANIFEST 四项对（Main-Class / Start-Class / Build-Jdk-Spec=17 / Spring-Boot-Version=3.4.4）
- [ ] jar 内 profile 是**字面量** dev 或 prod，不是 `@profiles.active@`
- [ ] 临时解包目录 `/tmp/jarchk` 已清理
