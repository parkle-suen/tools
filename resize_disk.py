#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LVM 根分区全扩展 + 创建 /d 数据分区（加强版 - 带详细配置预览）

功能：
1. 开头显示当前硬盘、LVM、根分区使用情况
2. 把卷组所有剩余空间扩展给根分区
3. 用剩余空间（理论上为0）创建新逻辑卷并挂载到 /d

强烈建议：
- 先备份重要数据
- 以 root 权限运行
"""

import subprocess
import sys
import re
import os


# 颜色定义（终端友好）
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def run_cmd(cmd, check=True, capture_output=True, silent=False):
    """执行 shell 命令"""
    if not silent:
        print(f"{Colors.OKBLUE}执行: {cmd}{Colors.ENDC}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check,
            text=True, capture_output=capture_output
        )
        if capture_output and result.stdout and not silent:
            print(result.stdout.strip())
        if result.stderr and not silent:
            print(f"{Colors.WARNING}{result.stderr.strip()}{Colors.ENDC}")
        return result.stdout.strip(), result.returncode == 0
    except subprocess.CalledProcessError as e:
        if not silent:
            print(f"{Colors.FAIL}命令失败: {cmd}\n错误: {e}{Colors.ENDC}")
        return "", False


def show_system_info():
    """显示当前系统磁盘 & LVM 配置"""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}当前系统磁盘 & LVM 配置概览{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

    # 1. 物理磁盘概览
    print(f"{Colors.OKGREEN}1. 物理磁盘信息 (lsblk){Colors.ENDC}")
    lsblk_out, _ = run_cmd("lsblk -o NAME,SIZE,TYPE,MODEL,MOUNTPOINT,FSTYPE", silent=False)
    print(lsblk_out or "（无法获取）")

    # 2. 根分区使用情况
    print(f"\n{Colors.OKGREEN}2. 根分区当前使用情况 (df -h /){Colors.ENDC}")
    df_out, _ = run_cmd("df -h /", silent=False)
    print(df_out or "（无法获取）")

    # 3. 卷组信息
    print(f"\n{Colors.OKGREEN}3. 卷组信息 (vgs){Colors.ENDC}")
    vgs_out, vgs_ok = run_cmd("vgs --noheadings --units g", silent=True)
    if vgs_ok and vgs_out:
        parts = re.split(r'\s+', vgs_out.strip())
        if len(parts) >= 7:
            vg_name = parts[0]
            vg_size = parts[4]      # VG Size
            vg_free = parts[6]      # Free PE / Size
            print(f"卷组名称: {Colors.BOLD}{vg_name}{Colors.ENDC}")
            print(f"总大小   : {Colors.BOLD}{vg_size} GiB{Colors.ENDC}")
            print(f"剩余空间 : {Colors.WARNING}{vg_free} GiB{Colors.ENDC} （可用于扩展或新分区）")
        else:
            print(vgs_out)
    else:
        print("未找到卷组信息或命令失败")

    # 4. 逻辑卷列表
    print(f"\n{Colors.OKGREEN}4. 当前逻辑卷列表 (lvs){Colors.ENDC}")
    run_cmd("lvs --units g", silent=False)

    print(f"\n{Colors.HEADER}{'-'*70}{Colors.ENDC}")
    print(f"{Colors.WARNING}总结：{Colors.ENDC}")
    if "GiB" in vg_free:
        free = float(vg_free.replace("GiB", "").strip())
        if free > 1:
            print(f"→ 你还有约 {Colors.BOLD}{free:.1f} GiB{Colors.ENDC} 的**剩余空间**可以利用")
            print(f"→ 脚本将把这部分空间**全部**扩展给根分区（/）")
        else:
            print("→ 剩余空间不足 1GiB，无需扩展")
    else:
        print("→ 无法准确读取剩余空间，请手动检查 vgs 命令")
    print(f"{Colors.HEADER}{'-'*70}{Colors.ENDC}\n")


def confirm_action(message):
    while True:
        answer = input(f"{Colors.WARNING}{message}{Colors.ENDC} (y/n): ").strip().lower()
        if answer in ('y', 'yes', ''):
            return True
        if answer in ('n', 'no'):
            return False
        print("请输入 y 或 n")


def main():
    if os.geteuid() != 0:
        print(f"{Colors.FAIL}错误：请使用 root 权限运行此脚本（sudo python3 ...）{Colors.ENDC}")
        sys.exit(1)

    print(f"\n{Colors.HEADER}=== LVM 根分区全扩展 & 创建 /d 数据分区 工具（2025加强版） ==={Colors.ENDC}")

    # 第一步：展示配置信息
    show_system_info()

    if not confirm_action("确认以上信息正确，并继续操作？（操作不可逆，强烈建议先备份）"):
        print(f"{Colors.OKBLUE}操作已取消，安全退出。{Colors.ENDC}")
        sys.exit(0)

    # 以下是原有的扩展 + 创建新分区逻辑（略微优化）
    print(f"\n{Colors.OKGREEN}开始执行第一阶段：扩展根分区到最大...{Colors.ENDC}")

    stage1_commands = [
        "lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv",
        "resize2fs /dev/ubuntu-vg/ubuntu-lv",
        "df -h /"
    ]

    for cmd in stage1_commands:
        run_cmd(cmd)

    # 检查是否还有剩余空间创建新分区
    vgs_out, _ = run_cmd("vgs --noheadings --units g", silent=True)
    free_gb = 0.0
    if vgs_out:
        parts = re.split(r'\s+', vgs_out.strip())
        if len(parts) >= 7:
            free_gb = float(parts[6].replace("GiB", "").strip())

    if free_gb < 1:
        print(f"\n{Colors.WARNING}剩余空间不足 1GiB，无法创建有意义的新分区。{Colors.ENDC}")
        print("根分区已扩展到最大，操作完成。")
        sys.exit(0)

    print(f"\n{Colors.OKGREEN}意外发现还有约 {free_gb:.1f} GiB 剩余空间，将用于创建 /d 分区...{Colors.ENDC}")

    # 第二阶段：创建新逻辑卷
    stage2_commands = [
        "lvcreate -l 100%FREE -n data-lv ubuntu-vg",
        "mkfs.ext4 -F /dev/ubuntu-vg/data-lv",
        "mkdir -p /d",
        "mount /dev/ubuntu-vg/data-lv /d"
    ]

    uuid = None
    for cmd in stage2_commands:
        out, success = run_cmd(cmd, capture_output="blkid" in cmd)
        if "blkid" in cmd and success:
            uuid = out.strip()

    if not uuid:
        print(f"{Colors.FAIL}无法获取新逻辑卷 UUID，fstab 配置失败！{Colors.ENDC}")
        print("新分区已格式化并临时挂载在 /d，可手动处理 fstab。")
        sys.exit(1)

    fstab_line = f"UUID={uuid}   /d   ext4   defaults   0   2\n"
    print(f"\n即将添加以下行到 /etc/fstab：\n{Colors.BOLD}{fstab_line.strip()}{Colors.ENDC}")

    if not confirm_action("确认添加到 fstab？（错误可能导致无法开机）"):
        print("已取消 fstab 修改。新分区已临时挂载。")
        sys.exit(0)

    with open("/etc/fstab", "a") as f:
        f.write(fstab_line)

    run_cmd("mount -a")  # 测试 fstab

    print(f"\n{Colors.OKGREEN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}操作完成！最终状态：{Colors.ENDC}")
    run_cmd("df -h / /d")
    run_cmd("lsblk -f")
    print(f"{Colors.OKGREEN}{'='*70}{Colors.ENDC}")
    print("新分区 /d 已永久挂载完成。下次重启依然有效。")


if __name__ == "__main__":
    main()