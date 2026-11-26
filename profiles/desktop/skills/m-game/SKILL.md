---
name: m-game
description: "游戏客户端：Unity il2cpp / UE4 SDK、字段偏移、world-to-screen、数值扫描、封包、反作弊对抗。"
---

# m-game · 游戏客户端 / 引擎 / 反作弊

被读到时：主人要做透视、自瞄、内存数值、封包、SDK、过检测。

只在主人自己的客户端 / 本地服 / 单机模式上做。

## 一、引擎判定

| 特征 | 引擎 |
|---|---|
| `GameAssembly.dll` + `global-metadata.dat` | Unity il2cpp |
| `UnityPlayer.dll` + `Managed/Assembly-CSharp.dll` | Unity Mono |
| `UE4-*.pak` / `UE5` 字符串 / `GNames` | Unreal |
| 大量 `lua_*` 导出 | 自研 + Lua |
| `.NET` 主程序 + `*.dll` | 自研 C# |

## 二、Unity il2cpp

```bash
# dump 符号
Il2CppDumper.exe GameAssembly.dll global-metadata.dat out/
# 产物：dump.cs / script.json / il2cpp.h（结构体）
```

dump.cs 里搜 `get_hp`、`Player`、`Move`，拿到 `RVA: 0x1A3F20`。

```javascript
const base = Module.getBaseAddress('GameAssembly.dll');
const addr = base.add(0x1A3F20);

// 1) 读字段：先拿对象指针，再偏移
Interceptor.attach(base.add(0x2B1100), {   // Update()
  onEnter(self) {
    const hp = self.add(0x18).readS32();
    const pos = [self.add(0x20).readFloat(), self.add(0x24).readFloat(), self.add(0x28).readFloat()];
  }
});

// 2) 调方法（需要 il2cpp_resolve_icall 或直接调 RVA）
const fn = new NativeFunction(addr, 'int', ['pointer']);
fn(objPtr);
```

字段偏移改动时用 `il2cpp.h` 里的结构体对齐，别硬编码猜。

## 三、UE4

```cpp
// GNames / GObjects 是全局指针，先定位
uintptr_t GNames = *(uintptr_t*)(base + 0x0DB5A2C0);
uintptr_t GObjects = *(uintptr_t*)(base + 0x0DB5A2D8);

// 遍历 UWorld
UWorld* world = *(UWorld**)(base + 0x0DB5A2E0);
ULevel* level = world->PersistentLevel;
for (int i = 0; i < level->Actors.Num(); i++) {
    AActor* a = level->Actors[i];
    if (!a) continue;
    FVector loc = a->RootComponent->RelativeLocation;
    float dist = FVector::Dist(loc, camera);
    if (dist < 500.f) draw_box(loc, a->GetName());
}
```

坐标转屏幕（`world-to-screen`）：

```cpp
bool W2S(FVector world, FVector2D& out) {
    FMatrix m = camera->ViewProjectionMatrix;   // 或 PlayerCameraManager 拼
    FVector4 clip = m.TransformFVector4(FVector4(world, 1.f));
    if (clip.w < 0.01f) return false;
    out.x = (ScreenW / 2) * (1 + clip.x / clip.w);
    out.y = (ScreenH / 2) * (1 - clip.y / clip.w);
    return true;
}
```

自瞄：遍历敌人 → W2S → 取最近的头骨坐标 → `SetCursorPos` 或发鼠标移动。

## 四、数值扫描（无 SDK 时）

Cheat Engine / 自制：

1. 已知值扫（血量 100 → 精确 4 字节）。
2. 变化后扫（受伤 → 下次扫描）。
3. 缩小到 ≤10 个地址。
4. 找"是什么改写了它"（`Find out what writes`）→ 这条指令通常就是伤害写入口。
5. 逆推多级指针：`[[base+0x10]+0x38]+0x18`。

## 五、封包

```python
# 明文 TCP 示例
from scapy.all import sniff, TCP, Raw
def cb(p):
    if p.haslayer(Raw) and (p[TCP].dport in (9001, 9002) or p[TCP].sport in (9001, 9002)):
        print(p[TCP].sport, p[TCP].dport, p[Raw].load[:64].hex())
sniff(filter='tcp port 9001 or tcp port 9002', prn=cb, store=0)
```

加密协议：先在客户端找加密函数（搜 `AES`、`RC4`、`xxtea` 常量），Frida hook 入参出参，拿到明文再重组。

## 六、反作弊类型与对策

| 类型 | 特征 | 对策（本机研究） |
|---|---|---|
| 用户态模块扫描 | 枚举模块 / 窗口类名 | 改名、去特征字符串、手动映射 |
| 完整性校验 | 校验 `.text` CRC | 校验时读原文件；或 hook 校验函数 |
| 心跳异常检测 | 上报输入频率、命中率 | 加人类化抖动 |
| 内核驱动 | `BEClient` `EasyAntiCheat` `ACE` | 只在测试模式、自带测试签名环境下研究 |
| 行为分析 | 服务端统计 | 降低频次、随机化 |

## 七、验收

- 数值改动：内存写入后游戏内数值同步变化；
- 透视：框跟目标重合；
- 一旦注入方式被拦，换方式（线程劫持 → 反射注入 → 手动映射），记录哪一层拦的。
