# Aliyun CLI 安装与凭证检查

本 Skill 使用阿里云国内站（aliyun.com）。价格为人民币（¥）。

## 安装（需 3.x）

```bash
# macOS
brew install aliyun-cli && brew upgrade aliyun-cli
# Linux
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz && sudo mv aliyun /usr/local/bin/

aliyun version   # 确认 3.x
```

## 命令形态

所有查询用驼峰原生形态直连 OpenAPI（含 `aliyun cms DescribeMetricList`、
`DescribeMonitoringAgentStatuses`），不依赖插件。

参数形态、时间格式、响应解析等易错点见 `api_gotchas.md`。

## 凭证检查（仅查状态）

```bash
aliyun configure list
```

- **绝不**读取、回显、打印或索要 AK/SK/STS Token。
- 本会话内**绝不**用 `aliyun configure set` 写入字面凭证值。
- 若无有效配置集，停止并请用户在本会话**之外**配置凭证（终端 `aliyun configure` 或环境变量）。
  待 `aliyun configure list` 显示有效配置集后再继续。

## 地域

每条调用使用 `.qianwenai-deploy` 中的 `region_id`。

## 参考

- CLI 文档：https://help.aliyun.com/zh/cli/
- AccessKey 管理：https://ram.console.aliyun.com/manage/ak
