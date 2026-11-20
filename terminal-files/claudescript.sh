#!/bin/bash
# capture.sh - snapshot how the vendor image sets up the Pi Terminal hardware
OUT=/tmp/pi-terminal-capture; rm -rf "$OUT"; mkdir -p "$OUT/etc"; cd "$OUT" || exit 1
K=$(uname -r)

# System
cat /etc/os-release > os-release.txt; uname -a > uname.txt
tr -d '\0' < /proc/device-tree/model > model.txt

# Boot config, plus overlays that no package installed (= added by the vendor)
cp -a /boot/config.txt /boot/cmdline.txt .
mkdir overlays
for f in /boot/overlays/*.dtbo; do dpkg -S "$f" >/dev/null 2>&1 || cp "$f" overlays/; done

# The live device tree: exactly how the hardware is configured right now
dtc -I fs -O dts /proc/device-tree > live-device-tree.dts 2>/dev/null

# Drivers and devices
lsmod > lsmod.txt; dmesg > dmesg.txt
cat /proc/bus/input/devices > input-devices.txt
ip -details link > ip-link.txt
ls -l /dev/tty* /dev/rtc* /dev/spidev* /dev/i2c-* /dev/fb* /dev/dri/* > devices.txt 2>&1
for b in /dev/i2c-*; do echo "== $b"; i2cdetect -y "${b##*-}"; done > i2c-scan.txt 2>&1
dkms status > dkms.txt 2>&1
find /lib/modules/$K \( -path '*/extra/*' -o -path '*/updates/*' \) > extra-modules.txt
cp -a /etc/modules /etc/modprobe.d /etc/modules-load.d etc/ 2>/dev/null

# PCA9557 (relay / DO / DI / LED / buzzer) as the vendor image leaves it
{ echo -n "config 0x03: "; i2cget -y 1 0x18 0x03; echo -n "output 0x01: "; i2cget -y 1 0x18 0x01; } > pca9557.txt 2>&1

# Files that aren't from any package, and package config files that were edited
cat /var/lib/dpkg/info/*.list | sort -u > /tmp/owned.txt
find /etc /boot /usr/local /opt /lib/firmware /usr/share/fonts -type f 2>/dev/null | sort > /tmp/all.txt
comm -23 /tmp/all.txt /tmp/owned.txt > unowned-files.txt
debsums -ce > changed-conffiles.txt 2>/dev/null
cat unowned-files.txt changed-conffiles.txt | grep -v '^/boot/' | tar czf files.tar.gz -T - 2>/dev/null

# What runs at boot
systemctl list-unit-files --state=enabled > enabled-units.txt
cp -a /etc/rc.local . 2>/dev/null
for u in $(cut -d: -f1 /etc/passwd); do crontab -l -u "$u" 2>/dev/null | sed "s/^/$u: /"; done > crontabs.txt
tar czf home-config.tar.gz /home/*/.config/autostart /home/*/.config/lxsession /home/*/.config/lxpanel \
    /home/*/.fonts /home/*/.local/share/fonts 2>/dev/null

# Packages
apt-mark showmanual > apt-manual.txt; apt-mark showhold > apt-hold.txt; dpkg -l > dpkg-l.txt
pip3 list > pip3.txt 2>&1

# CM4 bootloader config (stored on the CM4 itself, so a new card keeps it, but record it)
{ rpi-eeprom-config; vcgencmd bootloader_version; } > eeprom.txt 2>&1

tar czf "/home/${SUDO_USER:-pi}/pi-terminal-capture.tar.gz" -C /tmp pi-terminal-capture
chown "${SUDO_USER:-pi}:" "/home/${SUDO_USER:-pi}/pi-terminal-capture.tar.gz"
echo "Saved ~/pi-terminal-capture.tar.gz"