---
name: m-protocol
description: "协议逆向：抓包、结构还原、重放改包、protobuf、伪造客户端。"
---

# m-protocol · 协议逆向 / 抓包

被读到时：主人要搞懂一个自研协议、抓包、重放、改包、伪造客户端。

## 一、抓包

```bash
tcpdump -i any -s 0 -w cap.pcap 'host 10.0.0.5'
tshark -r cap.pcap -Y 'tcp.port==9001' -T fields -e data.data | head
tshark -r cap.pcap -q -z follow,tcp,raw,3
```

不认代理的进程：Proxifier，或 WinDivert 透明转发。

## 二、结构还原

1. 找长度字段：改一位看包长。
2. 找序号：连续发包看递增位。
3. 找校验：改任意字节看是否被拒，二分缩到 1-4 字节。
4. 找加密：算熵，接近 8 就是密文。

```python
import math, collections
def entropy(b):
    c = collections.Counter(b); n = len(b)
    return -sum(v/n*math.log2(v/n) for v in c.values())
print(entropy(payload[8:]))
```

## 三、重放与改包

```python
import socket
pkt = bytes.fromhex('...')
s = socket.create_connection(('10.0.0.5', 9001))
s.sendall(pkt); print(s.recv(4096).hex())
```

mitmproxy 脚本：

```python
from mitmproxy import http
def request(flow: http.HTTPFlow):
    if '/api/buy' in flow.request.path:
        flow.request.content = flow.request.content.replace(b'"price":100', b'"price":1')
```

## 四、常见形态

| 形态 | 特征 | 处理 |
|---|---|---|
| 长度+命令+数据 | 前 4 字节大端长度 | 按长度切帧 |
| Protobuf | `0x08` `0x12` 字段号 | `protoc --decode_raw` |
| MessagePack | `0x8x` 开头 | `msgpack.unpackb` |
| 自定义二进制 | 固定头 + TLV | 逐字段试 |
| WebSocket | `Upgrade` 头 | `websocat` |

## 五、伪造客户端

1. 抓一次正常登录，记录每个字段。
2. 去掉时间戳/nonce，看服务端是否校验。
3. 校验就逆算法：客户端里搜 `sign` `nonce` `hmac`。
4. 用 Python 复刻握手，跑通即为自有客户端。

## 六、验收

自己构造的包被服务端接受并返回正确业务数据，就算通。
