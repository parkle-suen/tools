#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诚通网盘 数据库 + Gitea 自动备份配置工具（加强版 - 支持7z加密 + Docker）
修复版 v3.2 - 2025-12-30 支持 Docker 容器
"""
import os
import subprocess
import getpass
import shutil
import re
import sys
import json
from datetime import datetime

SCRIPT_VERSION = "2025-12-30 v3.2"
BACKUP_SCRIPT_PATH = "/usr/local/bin/auto-backup-mysql-gitea.sh"
CRON_PATH = "/etc/cron.d/auto-backup-mysql-gitea"
RCLONE_REMOTE_NAME = "ctfile"
ENCRYPT_PASSWORD = r"zbaQ#,Xy,Nkq*fg*zmdaV,%ZTV]LsWGdFF]gPJDYn]rzm^%uiY+n>wZRnmYQ_!Q%p~#hq*iWs#mythJNn,tc-kGTuyWU}HieAy^v"
NTFY_URL = "http://192.168.0.169:8125"
NTFY_TOPIC = "169"

def run_cmd(cmd, check=True, capture_output=False, text=True, shell=False):
    """统一命令执行入口"""
    try:
        result = subprocess.run(
            cmd, shell=shell, check=check,
            capture_output=capture_output, text=text
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {' '.join(cmd) if isinstance(cmd,list) else cmd}")
        if e.stderr:
            print(e.stderr.strip())
        raise

def is_root():
    return os.geteuid() == 0

def check_required_commands():
    # 只检查宿主机真正需要的命令（mysqldump 和 gitea 现在在容器内）
    required = ["7z", "jq"]
    missing = [cmd for cmd in required if not shutil.which(cmd)]
   
    if missing:
        print("缺少以下必要命令，请先安装：")
        print(", ".join(missing))
        print("\n安装建议（Debian/Ubuntu）：")
        print(" sudo apt update")
        print(" sudo apt install p7zip-full jq")
        print(" # rclone 将由本脚本自动安装")
        sys.exit(1)

def send_ntfy(title, message, priority=3):
    """发送 ntfy 通知"""
    try:
        payload = {
            "topic": NTFY_TOPIC,
            "title": title,
            "message": message,
            "priority": priority
        }
        cmd = [
            "curl", "-s", "-o", "/dev/null",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            NTFY_URL
        ]
        subprocess.run(cmd, check=False, capture_output=True)
    except Exception:
        pass

def install():
    print(f"\n=== 自动备份配置向导（MySQL + Gitea → 7z加密 → 城通网盘） {SCRIPT_VERSION} ===\n")
    check_required_commands()
    if not is_root():
        print("警告：强烈建议使用 root 执行此配置脚本\n")

    # ── 第一步：配置 rclone ────────────────────────────────────────────
    print("【1】 城通网盘 WebDAV 配置")
    webdav_url = input(" WebDAV 完整地址 [https://webdav.ctfile.com]: ").strip() or "https://webdav.ctfile.com"
    ct_user = input(" 城通账号（邮箱/手机号）: ").strip()
    ct_pass = getpass.getpass(" 城通密码: ")
    remote_dir = input(" 上传目标目录（留空=根目录）: ").strip().rstrip('/')
    remote_path = f"{remote_dir}/" if remote_dir else ""

    if not shutil.which("rclone"):
        print("\n安装 rclone...")
        run_cmd("curl https://rclone.org/install.sh | bash", shell=True)

    print("\n正在创建/更新 rclone 配置...")
    obscure_pass = run_cmd(["rclone", "obscure", ct_pass], capture_output=True).stdout.strip()
    run_cmd([
        "rclone", "config", "create", RCLONE_REMOTE_NAME, "webdav",
        f"url={webdav_url}", "vendor=other",
        f"user={ct_user}", f"pass={obscure_pass}"
    ])

    # ── 第二步：选择备份内容 ──────────────────────────────────────────
    print("\n【2】 选择要自动备份的内容（可多选）")
    print(" 1 = 只备份 MySQL")
    print(" 2 = 只备份 Gitea")
    print(" 3 = 同时备份 MySQL + Gitea")
    choice = input("\n请选择 (1/2/3): ").strip()
    backup_mysql = choice in ("1", "3")
    backup_gitea = choice in ("2", "3")
    if not (backup_mysql or backup_gitea):
        print("未选择任何备份类型，退出。")
        return

    # ── 第三步：公共设置 ───────────────────────────────────────────────
    print("\n【3】 公共备份设置")
    backup_dir = input(" 本地备份文件存放目录（绝对路径）: ").strip().rstrip('/')
    os.makedirs(backup_dir, exist_ok=True)
    keep_days_str = input(" 本地保留几天备份文件？（0=不删除） [7]: ") or "7"
    keep_days = int(keep_days_str) if keep_days_str.isdigit() else 7
    schedule = input(" 每天执行时间 HH:MM [03:00]: ").strip() or "03:00"
    if not re.match(r'^\d{1,2}:\d{2}$', schedule):
        schedule = "03:00"
    hour, minute = map(int, schedule.split(':'))

    # ── 第四步：Docker MySQL 设置 ─────────────────────────────────────
    mysql_section = ""
    if backup_mysql:
        print("\n【4】 Docker MySQL 备份设置")
        mysql_container = input(" MySQL 容器名: ").strip()
        db_user = input(" MySQL 用户名 [root]: ").strip() or "root"
        db_pass = getpass.getpass(" MySQL 密码: ")
        mysql_section = f'''
MYSQL_CONTAINER="{mysql_container}"
MYSQL_USER="{db_user}"
MYSQL_PASS='{db_pass}'
'''

    # ── 第五步：Docker Gitea 设置 ─────────────────────────────────────
    gitea_section = ""
    if backup_gitea:
        print("\n【5】 Docker Gitea 备份设置")
        gitea_container = input(" Gitea 容器名: ").strip()
        gitea_user = input(" Gitea 容器内运行用户 [git]: ").strip() or "git"
        gitea_section = f'''
GITEA_CONTAINER="{gitea_container}"
GITEA_USER="{gitea_user}"
'''

    # ── 生成备份脚本 ──────────────────────────────────────────────────
    delete_old_cmd = f'find "$BACKUP_DIR" -type f -name "backup-*.7z" -mtime +{keep_days} -delete' if keep_days > 0 else ''

    script_content = f'''#!/bin/bash
# 自动备份 Docker MySQL + Gitea 到城通网盘（加密7z） - v{SCRIPT_VERSION.split()[-1]}
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
BACKUP_DIR="{backup_dir}"
ENCRYPT_PASS="{ENCRYPT_PASSWORD}"
RCLONE_REMOTE="{RCLONE_REMOTE_NAME}:{remote_path}"
NTFY_URL="{NTFY_URL}"
NTFY_TOPIC="{NTFY_TOPIC}"
mkdir -p "$BACKUP_DIR"
exec > >(tee -a "$BACKUP_DIR/backup.log") 2>&1
log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}}
fail_notify() {{
    local title="$1"
    local msg="$2"
    curl -s -o /dev/null -H "Content-Type: application/json" \\
        -d '{{"topic":"'$NTFY_TOPIC'","title":"'$title'","message":"'$msg'","priority":4}}' \\
        "$NTFY_URL"
}}
log "=== 备份任务开始 ==="
{ mysql_section if backup_mysql else "" }
{ gitea_section if backup_gitea else "" }
backup_files=()
has_error=0

# ── MySQL 备份（Docker） ─────────────────────────────────────────────
if [ -n "${{MYSQL_CONTAINER:-}}" ]; then
    MYSQL_7Z="$BACKUP_DIR/backup-mysql-$(date +%Y%m%d-%H%M%S).7z"
    log "开始 Docker MySQL 备份 → $MYSQL_7Z"
    
    if docker exec -i "$MYSQL_CONTAINER" mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASS" --all-databases --single-transaction --quick --set-gtid-purged=OFF | 7z a -t7z -mhe=on -p"$ENCRYPT_PASS" -si "$MYSQL_7Z" >/dev/null 2>&1
    then
        backup_files+=("$MYSQL_7Z")
        log "MySQL 备份成功"
    else
        log "ERROR: Docker MySQL 备份失败"
        has_error=1
    fi
fi

# ── Gitea 备份（Docker） ─────────────────────────────────────────────
if [ -n "${{GITEA_CONTAINER:-}}" ]; then
    GITEA_7Z="$BACKUP_DIR/backup-gitea-$(date +%Y%m%d-%H%M%S).7z"
    log "开始 Docker Gitea dump → $GITEA_7Z"
    
    if docker exec -u "$GITEA_USER" "$GITEA_CONTAINER" gitea dump --file - | 7z a -t7z -mhe=on -p"$ENCRYPT_PASS" -si "$GITEA_7Z" >/dev/null 2>&1
    then
        backup_files+=("$GITEA_7Z")
        log "Gitea 备份成功"
    else
        log "ERROR: Docker Gitea dump 失败"
        has_error=1
    fi
fi

# ── 上传与校验 ──────────────────────────────────────────────────────
for file in "${{backup_files[@]}}"; do
    if [ ! -f "$file" ]; then
        log "文件已丢失，跳过: $file"
        continue
    fi
    LOCAL_SIZE=$(stat -c %s "$file" 2>/dev/null || stat -f %z "$file" 2>/dev/null || echo 0)
    log "上传 $file (大小: $LOCAL_SIZE bytes)"
    
    if rclone copy "$file" "$RCLONE_REMOTE" --progress 2>>"$BACKUP_DIR/backup.log"
    then
        REMOTE_SIZE=$(rclone size "$RCLONE_REMOTE$(basename "$file")" --json 2>/dev/null | jq -r '.bytes' 2>/dev/null || echo "0")
        if [ "$LOCAL_SIZE" = "$REMOTE_SIZE" ] && [ "$REMOTE_SIZE" != "0" ]; then
            log "上传校验成功: $file"
        else
            log "！！！上传校验失败！！！ $file (本地:$LOCAL_SIZE ≠ 远程:$REMOTE_SIZE)"
            has_error=1
        fi
    else
        log "rclone 上传失败: $file"
        has_error=1
    fi
done

# 清理旧文件
{delete_old_cmd}
log "=== 本次备份结束 ==="
if [ $has_error -eq 1 ]; then
    fail_notify "备份异常" "服务器备份任务完成但出现错误，请检查 $BACKUP_DIR/backup.log"
fi
exit $has_error
'''

    with open(BACKUP_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(BACKUP_SCRIPT_PATH, 0o755)

    cron_content = f"""# MySQL & Gitea 自动备份（Docker） - {datetime.now().strftime('%Y-%m-%d')}
{minute} {hour} * * * root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin {BACKUP_SCRIPT_PATH}
"""
    with open(CRON_PATH, "w", encoding="utf-8") as f:
        f.write(cron_content)

    print("\n" + "="*78)
    print("Docker 版配置完成！（v3.2）")
    print(f"备份脚本： {BACKUP_SCRIPT_PATH}")
    print(f"定时任务： {CRON_PATH}")
    print(f"日志文件： {backup_dir}/backup.log")
    print("\n建议立即手动测试：")
    print(f" sudo {BACKUP_SCRIPT_PATH}")
    print("="*78)

def uninstall():
    print("卸载指引：")
    print(f" sudo rm -f {BACKUP_SCRIPT_PATH}")
    print(f" sudo rm -f {CRON_PATH}")
    print(f" rclone config delete {RCLONE_REMOTE_NAME} # 可选")

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("--uninstall", "-u", "uninstall"):
        uninstall()
    else:
        install()

if __name__ == "__main__":
    if not is_root():
        print("建议使用 root 或 sudo 执行本脚本\n")
    main()