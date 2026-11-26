# 可观测·应用

评估应用是否可达、服务是否正常。所有云助手命令均为**只读**。

## 公网可用性

探测公网地址和 `/healthz`：

```bash
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 10 "http://<public_ip>/healthz"
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 10 "http://<public_ip>/"
```

记录 HTTP 状态、当前响应时间、失败原因（超时 / 连接拒绝 / 5xx）。

- 2xx/3xx → 应用层 `healthy`。
- 5xx，或应用起来但有错误 → `degraded`。
- 连接拒绝 / 超时 → `unavailable`。

## 服务与端口检查（云助手，只读）

在 ECS 上跑一段只读脚本并取回结果：

> `<app_port>` 取状态文件 `app_port`；该字段为空时用 `8080`。切勿代入空串，否则匹配模式会退化成匹配任意监听端口。

```bash
aliyun ecs RunCommand --RegionId <region> --Type RunShellScript --InstanceId.1 <ecs-id> \
  --ContentEncoding Base64 \
  --CommandContent "$(printf '%s' 'systemctl is-active <service_name>; systemctl is-active nginx; ss -ltnp | grep -E ":80|:<app_port>" || true' | base64)"
```

再轮询：

```bash
aliyun ecs DescribeInvocations --RegionId <region> --InvokeId <invoke-id> --IncludeOutput true
```

检查：`<service_name>` active、`nginx` active（当 `nginx_mode` 使用它时），以及应用端口 / 80 端口
在监听。`<service_name>` 取状态文件的 `service_name`，缺失时回退 `qianwenai-app`。

## 日志摘要（只读）

把近期应用日志和 Nginx 错误日志汇总成主要错误类型——不要贴原始日志。只读 tail，例如：

```bash
journalctl -u <service_name> --since '1 hour ago' --no-pager | tail -n 200
tail -n 200 /var/log/nginx/error.log
```

汇报前对 AccessKey、Token、密码、连接串密码、Cookie 脱敏。只报主要错误类别和计数，不含字面密文。

## 结果

把探活 + 服务 + 日志合并为一个应用层状态，附证据（状态码、响应时间、哪个服务挂了、主要错误类型）。

探活只证明入口可达，不单独作为应用健康结论；须结合 ECS 层云监控 CPU/内存数据点一并判定，取最严。
