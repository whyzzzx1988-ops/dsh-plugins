---
name: m-crypto
description: "密码学：算法识别、XOR/AES 还原、哈希爆破、证书生成、签名校验。"
---

# m-crypto · 密码学 / 加解密 / 证书

被读到时：主人要解一段密文、还原算法、破口令、做证书、看签名。

## 先认算法

| 特征 | 可能是 |
|---|---|
| 长度 16/24/32 整数倍、无结构 | AES / SM4 分组 |
| 每次密文长度不固定、头部带 nonce | 流式（ChaCha20 / AES-GCM） |
| 纯十六进制、长度 = 明文 | XOR / 单字节替换 |
| Base64 里出现 `+` `/` `=` | Base64 包装，先解一层 |
| 一段 32/64 位十六进制混在请求里 | MD5 / SHA256 签名 |

工具：

```bash
# 识别
python3 -c "import binascii;d=open('c.bin','rb').read();print(len(d), binascii.hexlify(d[:32]))"
# 常见编码
echo 'xxx' | base64 -d | xxd | head
```

## XOR

```python
data = open('c.bin','rb').read()
best = max(range(256), key=lambda k: sum(32 <= (b^k) < 127 for b in data))
print(best, bytes(b ^ best for b in data)[:120])
```

多字节 key：先按 key 长度分块，对每列做单字节统计。

## AES

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
key = bytes.fromhex('...')      # 16/24/32 字节
iv  = bytes.fromhex('...')
pt  = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(open('c.bin','rb').read()), 16)
print(pt)
```

ECB 判定：把明文分块加密，两块相同 → 密文也相同。`python -c` 里比对 16 字节块重复即可。

## 哈希 / 口令

```bash
hashcat -m 0     md5.txt rockyou.txt      # MD5
hashcat -m 1000  ntlm.txt rockyou.txt     # NTLM
hashcat -m 1800  shadow.txt rockyou.txt   # sha512crypt
hashcat -m 22000 wifi.hc22000 rockyou.txt # WPA
john --format=raw-md5 --wordlist=rockyou.txt h.txt
```

加盐的：`hashcat -m 1420`（sha256($salt.$pass)）之类，先确认拼接顺序。

## 证书

```bash
# 自签一套（本地测试）
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab CA"
openssl req -newkey rsa:2048 -nodes -keyout srv.key -out srv.csr -subj "/CN=lab.local"
openssl x509 -req -in srv.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out srv.crt -days 825
# 看证书链
openssl s_client -connect host:443 -showcerts </dev/null
```

## 签名校验

RSA：`openssl dgst -sha256 -verify pub.pem -signature sig.bin data.bin`
ECDSA 的 `r,s` 从 DER 或 raw 里拆，注意 `s` 是否做了 low-s 规范化。

## 验收

解出来的明文能读、能对上已知结构（JSON / 文件头 / 协议字段），才算通了。对不上就把中间值打出来逐轮比对，别猜。
