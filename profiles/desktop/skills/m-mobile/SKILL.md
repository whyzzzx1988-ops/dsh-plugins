---
name: m-mobile
description: "安卓与 iOS：APK 拆解、脱壳、Frida hook、证书绑定绕过、抓包。"
---

# m-mobile · 安卓 / iOS

被读到时：主人要拆 APK、脱壳、Frida hook、过证书绑定、抓包、看 iOS 包。

## 一、APK 基线

```bash
apktool d app.apk -o app_src          # 资源 + smali
jadx -d app_jadx app.apk              # Java 反编译
unzip -l app.apk | grep -E "\.so$"    # 找 native
aapt dump badging app.apk | head      # 包名/版本/权限
```

加固识别：`libjiagu.so`（360）、`libshell.so`（腾讯乐固）、`libDexHelper.so`（梆梆）、`libmobisec.so`（阿里）、`classes.dex` 只有壳。

## 二、脱壳

**FART / frida-dexdump（推荐，快）**

```bash
pip install frida-dexdump
frida-dexdump -U -f com.target.app
```

**FART（要真机 + root）**：刷入 FART，跑目标，`/data/data/pkg/fart/` 下出 dex，逐个 `jadx`。

**黑盒 dump**：内存里搜 `dex\n035` 魔数，按 `file_size` 切出来。

## 三、Frida 常用

```javascript
// 枚举模块
Process.enumerateModules().forEach(m => console.log(m.name, m.base, m.size));

// hook Java 方法
Java.perform(() => {
  const Cls = Java.use('com.target.net.Api');
  Cls.sign.implementation = function (a, b) {
    console.log('[sign] in', a, b);
    const r = this.sign(a, b);
    console.log('[sign] out', r);
    return r;
  };
});

// hook native
Interceptor.attach(Module.getExportByName('libnative.so', 'Java_com_target_Native_check'), {
  onEnter(a) { console.log('arg', a[1].toInt32()); },
  onLeave(r) { console.log('ret', r.toInt32()); r.replace(ptr(1)); }
});

// 绕 root 检测
Java.perform(() => {
  ['isRooted','checkRoot','isDeviceRooted'].forEach(n => {
    try { Java.use('com.target.util.RootUtil')[n].implementation = () => false; } catch (e) {}
  });
});
```

## 四、证书绑定绕

```javascript
// OkHttp / TrustManager 一把梭
Java.perform(() => {
  const X509TM = Java.use('javax.net.ssl.X509TrustManager');
  const TM = Java.registerClass({
    name: 'com.x.TM',
    implements: [X509TM],
    methods: {
      checkClientTrusted() {}, checkServerTrusted() {}, getAcceptedIssuers() { return []; }
    }
  });
  const SSLContext = Java.use('javax.net.ssl.SSLContext');
  const ctx = SSLContext.getInstance('TLS');
  ctx.init(null, [TM.$new()], null);
  const OkHttp = Java.use('okhttp3.OkHttpClient$Builder');
  // 具体看目标用的库，很多情况 hook X509TrustManager 的实现类更快
});
```

Native 层的绑定（BoringSSL `SSL_CTX_set_custom_verify`）：hook `SSL_verify_cert_chain` 直接 return 1。

Android 7+ 用户证书不信任：装到系统证书（root 后 `mount -o remount,rw /system`，把 `.pem` 塞进 `/system/etc/security/cacerts/<hash>.0`）或改 `network_security_config`。

## 五、抓包

```bash
# 手机代理指向 Burp，导出 Burp CA
openssl x509 -inform DER -in cacert.der -out cacert.pem
hash=$(openssl x509 -inform PEM -subject_hash_old -in cacert.pem | head -1)
adb root && adb remount
adb push cacert.pem /system/etc/security/cacerts/$hash.0
adb shell chmod 644 /system/etc/security/cacerts/$hash.0
```

无 root：`r0capture`（frida 脚本，直接在进程里 dump 明文）、`HttpCanary`、`Reqable` + VPN 模式。

## 六、iOS

- 越狱机：`frida-ios-dump` 砸壳 → `class-dump` / `Hopper` 看结构。
- 非越狱：`frida` 走 `frida-server`（需注入），或 `objection` 跑 `ios sslpinning disable`。
- Mach-O：`otool -l`、`nm -m`、`jtool2`；Swift 符号用 `swift-demangle`。

## 七、验收

- hook 命中：日志里出现真实入参；
- 脱壳成功：`jadx` 能打开且类数明显多于壳 dex；
- 抓包成功：看到业务明文 JSON。
