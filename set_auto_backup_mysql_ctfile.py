#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诚通网盘 MySQL 自动备份配置工具（加强版）
功能：
1. 安装：配置 rclone + 生成备份脚本 + 添加 cron
2. 卸载：删除备份脚本、cron 任务、rclone 配置（可选）
3. 备份后校验文件大小是否一致
"""

import os
import subprocess
import getpass
import shutil
import re
import sys
from datetime import datetime

SCRIPT_VERSION = "2025-12-29 v2.1"

BACKUP_SCRIPT_PATH = "/usr/local/bin/mysql-auto-backup.sh"
CRON_PATH = "/etc/cron.d/mysql-auto-backup"
RCLONE_REMOTE_NAME = "ctfile"


def run_cmd(cmd, check=True, capture_output=False, text=True):
    """统一执行命令的辅助函数"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check,
            capture_output=capture_output, text=text
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {cmd}")
        print(e.stderr if e.stderr else "无错误输出")
        raise


def is_root():
    return os.geteuid() == 0


def uninstall():
    print("\n=== 卸载自动备份功能 ===\n")
    
    files_to_remove = [
        (BACKUP_SCRIPT_PATH, "备份执行脚本"),
        (CRON_PATH, "定时任务配置")
    ]
    
    print("即将删除以下文件：")
    for path, desc in files_to_remove:
        if os.path.exists(path):
            print(f"  - {path} ({desc})")
        else:
            print(f"  - {path} （不存在）")
    
    confirm = input("\n确认要删除以上文件？(y/N): ").strip().lower()
    if confirm != 'y':
        print("已取消卸载")
        return
    
    removed = 0
    for path, _ in files_to_remove:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"已删除: {path}")
                removed += 1
            except Exception as e:
                print(f"删除 {path} 失败: {e}")
    
    # 可选删除 rclone 配置（比较危险，谨慎操作）
    if input("\n是否同时删除 rclone 中名为 'ctfile' 的远程配置？(y/N): ").strip().lower() == 'y':
        try:
            run_cmd(f"rclone config delete {RCLONE_REMOTE_NAME}", check=False)
            print("已删除 rclone 配置 'ctfile'")
        except Exception as e:
            print("删除 rclone 配置失败（可能原本就不存在）")
    
    print(f"\n卸载完成，共删除 {removed} 个文件。")
    print("如需完全清理，请检查备份目录下的 .gz 文件和日志（默认不删除）")


def install():
    print(f"\n=== 诚通网盘 MySQL 自动备份配置向导（{SCRIPT_VERSION}） ===\n")
    print("本工具将帮你完成以下操作：")
    print("1. 配置 rclone WebDAV（城通网盘）")
    print("2. 生成每天自动备份+压缩+上传+校验脚本")
    print("3. 添加系统定时任务（cron）\n")

    if not is_root():
        print("警告：建议使用 root 或具有 sudo 权限的用户运行此脚本")
        print("部分操作可能需要手动提升权限\n")

    # ── 收集信息 ─────────────────────────────────────────────────────
    print("【1】 MySQL 连接信息")
    db_host = input("  MySQL 主机 [localhost]: ").strip() or "localhost"
    db_port = input("  端口 [3306]: ").strip() or "3306"
    db_name = input("  数据库名（all=全部）: ").strip()
    if not db_name:
        print("必须指定数据库名或 all")
        return 1
    db_user = input("  用户名: ").strip()
    db_pass = getpass.getpass("  密码（不可见）: ")

    print("\n【2】 本地存储设置")
    backup_dir = input("  备份文件存放目录（建议绝对路径）: ").strip().rstrip('/')
    os.makedirs(backup_dir, exist_ok=True)
    keep_days_str = input("  本地保留几天备份（0=不删除）[7]: ").strip() or "7"
    keep_days = int(keep_days_str) if keep_days_str.isdigit() else 7

    print("\n【3】 定时执行时间")
    schedule = input("  每天执行时间 HH:MM [03:00]: ").strip() or "03:00"
    if not re.match(r'^\d{1,2}:\d{2}$', schedule):
        schedule = "03:00"
    hour, minute = map(int, schedule.split(':'))

    print("\n【4】 城通网盘 WebDAV（VIP必须）")
    webdav_url = input("  WebDAV 地址 [https://webdav.ctfile.com]: ").strip() or "https://webdav.ctfile.com"
    ct_user = input("  城通账号（邮箱/手机号）: ").strip()
    ct_pass = getpass.getpass("  城通密码（不可见）: ")
    remote_dir = input("  上传到网盘的目录（留空=根目录）: ").strip().rstrip('/')
    remote_path = f"{remote_dir}/" if remote_dir else ""

    # ── 安装 rclone ──────────────────────────────────────────────────
    if not shutil.which("rclone"):
        print("\n正在安装 rclone...")
        run_cmd("curl https://rclone.org/install.sh | bash")

    # ── 配置 rclone ──────────────────────────────────────────────────
    print("\n配置 rclone remote...")
    obscure_pass = subprocess.check_output(["rclone", "obscure", ct_pass]).decode().strip()
    run_cmd(f"rclone config create {RCLONE_REMOTE_NAME} webdav "
            f"url={webdav_url} vendor=other "
            f"user={ct_user} pass={obscure_pass}")

    # ── 生成备份脚本 ─────────────────────────────────────────────────
    db_name_safe = "all" if db_name.lower() == "all" else db_name.replace('"', '\\"')
    delete_old = f'find "$BACKUP_DIR" -type f -name "*.gz" -mtime +{keep_days} -delete' if keep_days > 0 else ''

    script_content = f"""#!/bin/bash
set -euo pipefail

BACKUP_DIR="{backup_dir}"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILE_PREFIX="mysql-{db_name_safe}"
FILENAME="${{FILE_PREFIX}}-${{DATE}}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"
LOG="$BACKUP_DIR/backup.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份..." >> "$LOG"

# 备份
mysqldump -h {db_host} -P {db_port} -u {db_user} -p'{db_pass}' \\
    {'--all-databases' if db_name.lower() == 'all' else f'--databases "{db_name}"'} \\
    --single-transaction --quick --set-gtid-purged=OFF | gzip > "$FILEPATH" 2>> "$LOG"

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份失败！" >> "$LOG"
    exit 1
fi

LOCAL_SIZE=$(stat -c %s "$FILEPATH" 2>/dev/null || stat -f %z "$FILEPATH" 2>/dev/null || echo 0)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成，大小: ${{LOCAL_SIZE}} bytes" >> "$LOG"

# 上传
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传到城通网盘..." >> "$LOG"
rclone copy "$FILEPATH" {RCLONE_REMOTE_NAME}:"{remote_path}" --progress >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] rclone 上传命令失败" >> "$LOG"
    exit 1
fi

# 校验文件大小
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 正在校验上传文件大小..." >> "$LOG"
REMOTE_INFO=$(rclone size {RCLONE_REMOTE_NAME}:"{remote_path}{FILENAME}" --json 2>/dev/null || echo '{{ "count": 0, "size": 0 }}')

REMOTE_SIZE=$(echo "$REMOTE_INFO" | grep -oP '(?<="size": )\d+' || echo 0)

if [ "$LOCAL_SIZE" = "$REMOTE_SIZE" ] && [ "$REMOTE_SIZE" != "0" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传校验成功，大小一致: $REMOTE_SIZE bytes" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ！！！上传可能失败！！！" >> "$LOG"
    echo "本地: $LOCAL_SIZE bytes, 远程: $REMOTE_SIZE bytes" >> "$LOG"
    # 可以在这里加通知逻辑（钉钉、企业微信等）
fi

# 清理旧文件
{delete_old}
"""

    with open(BACKUP_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(BACKUP_SCRIPT_PATH, 0o755)

    # 添加 cron
    cron_content = f"{minute} {hour} * * * root {BACKUP_SCRIPT_PATH}\n"
    with open(CRON_PATH, "w", encoding="utf-8") as f:
        f.write(f"# MySQL 自动备份到城通网盘 - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(cron_content)

    print("\n" + "="*60)
    print("配置完成！")
    print(f"备份脚本：{BACKUP_SCRIPT_PATH}")
    print(f"定时任务：{CRON_PATH}")
    print(f"日志位置：{backup_dir}/backup.log")
    print("\n建议第一次手动测试：")
    print(f"  sudo {BACKUP_SCRIPT_PATH}")
    print("\n卸载方法：")
    print(f"  sudo python3 {sys.argv[0]} --uninstall")
    print("="*60)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--uninstall", "-u", "uninstall"):
        if is_root():
            uninstall()
        else:
            print("卸载操作建议使用 root 执行")
            print("或使用：sudo python3", sys.argv[0], "--uninstall")
    else:
        install()


if __name__ == "__main__":
    if not is_root():
        print("建议使用 root 或 sudo 执行本脚本\n")
    main()