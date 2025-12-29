#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诚通网盘 数据库 + Gitea 自动备份配置工具（加强版 - 支持7z加密）
修复版 v3.1 - 2025-12-29
"""

import os
import subprocess
import getpass
import shutil
import re
import sys
import json
from datetime import datetime

SCRIPT_VERSION = "2025-12-29 v3.1"

BACKUP_SCRIPT_PATH = "/usr/local/bin/auto-backup-mysql-gitea.sh"
CRON_PATH = "/etc/cron.d/auto-backup-mysql-gitea"
RCLONE_REMOTE_NAME = "ctfile"
ENCRYPT_PASSWORD = r"zbaQ#,Xy,Nkq*fg*zmdaV,%ZTV]LsWGdFF]gPJDYn]rzm^%uiY+n>wZRnmYQ_!Q%p~#hq*iWs#mythJNn,tc-kGTuyWU}HieAy^v"    



# ntfy 配置（家庭内网使用 http）
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
    required = ["7z", "mysqldump", "gitea", "jq"]  # 新增 jq 用于解析 rclone json
    missing = [cmd for cmd in required if not shutil.which(cmd)]
    
    if missing:
        print("缺少以下必要命令，请先安装：")
        print(", ".join(missing))
        print("\n安装建议（Debian/Ubuntu）：")
        print("  sudo apt update")
        print("  sudo apt install p7zip-full mysql-client gitea jq")
        print("  # rclone 将由本脚本自动安装")
        sys.exit(1)


def send_ntfy(title, message, priority=3):
    """发送 ntfy 通知（失败时使用较高优先级）"""
    try:
        payload = {
            "topic": NTFY_TOPIC,
            "title": title,
            "message": message,
            "priority": priority  # 1~5，3=默认，4=高，5=紧急
        }
        cmd = [
            "curl", "-s", "-o", "/dev/null",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            NTFY_URL
        ]
        subprocess.run(cmd, check=False, capture_output=True)
    except Exception:
        pass  # 通知失败不影响主流程


def install():
    print(f"\n=== 自动备份配置向导（MySQL + Gitea → 7z加密 → 城通网盘） {SCRIPT_VERSION} ===\n")

    check_required_commands()

    if not is_root():
        print("警告：强烈建议使用 root 执行此配置脚本\n")

    # ── 第一步：配置 rclone ────────────────────────────────────────────
    print("【1】 城通网盘 WebDAV 配置（必须先完成）")
    webdav_url = input("  WebDAV 完整地址 [https://webdav.ctfile.com]: ").strip() or "https://webdav.ctfile.com"
    print(f" WebDAV 完整地址 [{webdav_url}]: ").strip()
    ct_user = input("  城通账号（邮箱/手机号）: ").strip()
    ct_pass = getpass.getpass("  城通密码: ")
    remote_dir = input("  上传目标目录（留空=根目录）: ").strip().rstrip('/')
    remote_path = f"{remote_dir}/" if remote_dir else ""

    # 安装 rclone
    if not shutil.which("rclone"):
        print("\n安装 rclone...")
        run_cmd("curl https://rclone.org/install.sh | bash", shell=True)

    # 配置 remote
    print("\n正在创建/更新 rclone 配置...")
    obscure_pass = run_cmd(["rclone", "obscure", ct_pass], capture_output=True).stdout.strip()
    run_cmd([
        "rclone", "config", "create", RCLONE_REMOTE_NAME, "webdav",
        f"url={webdav_url}", "vendor=other",
        f"user={ct_user}", f"pass={obscure_pass}"
    ])

    # ── 第二步：选择备份内容 ──────────────────────────────────────────
    print("\n【2】 选择要自动备份的内容（可多选）")
    print("  1 = 只备份 MySQL")
    print("  2 = 只备份 Gitea")
    print("  3 = 同时备份 MySQL + Gitea")
    choice = input("\n请选择 (1/2/3): ").strip()

    backup_mysql = choice in ("1", "3")
    backup_gitea = choice in ("2", "3")

    if not (backup_mysql or backup_gitea):
        print("未选择任何备份类型，退出。")
        return

    # ── 第三步：公共设置 ───────────────────────────────────────────────
    print("\n【3】 公共备份设置")
    backup_dir = input("  本地备份文件存放目录（绝对路径）: ").strip().rstrip('/')
    os.makedirs(backup_dir, exist_ok=True)

    keep_days_str = input("  本地保留几天备份文件？（0=不删除） [7]: ") or "7"
    keep_days = int(keep_days_str) if keep_days_str.isdigit() else 7

    schedule = input("  每天执行时间 HH:MM [03:00]: ").strip() or "03:00"
    if not re.match(r'^\d{1,2}:\d{2}$', schedule):
        schedule = "03:00"
    hour, minute = map(int, schedule.split(':'))

    # ── 第四步：MySQL 设置 ─────────────────────────────────────────────
    mysql_section = ""
    if backup_mysql:
        print("\n【4】 MySQL 备份设置")
        db_host = input("  主机 [localhost]: ") or "localhost"
        db_port = input("  端口 [3306]: ") or "3306"
        db_name = input("  数据库名（all=全部）: ").strip()
        db_user = input("  用户名: ").strip()
        db_pass = getpass.getpass("  密码: ")
        mysql_section = f"""
MYSQL_HOST="{db_host}"
MYSQL_PORT="{db_port}"
MYSQL_DB="{db_name}"
MYSQL_USER="{db_user}"
MYSQL_PASS='{db_pass}'
"""

    # ── 第五步：Gitea 设置 ─────────────────────────────────────────────
    gitea_section = ""
    if backup_gitea:
        print("\n【5】 Gitea 备份设置")
        gitea_work_dir = input("  Gitea 工作目录（通常是 /var/lib/gitea）: ").strip() or "/var/lib/gitea"
        gitea_section = f"""
GITEA_WORK_DIR="{gitea_work_dir}"
"""

    # ── 生成备份脚本 ──────────────────────────────────────────────────
    delete_old_cmd = f'find "$BACKUP_DIR" -type f -name "backup-*.7z" -mtime +{keep_days} -delete' if keep_days > 0 else ''

    script_content = f'''#!/bin/bash
# 自动备份 MySQL + Gitea 到城通网盘（加密7z） - v{SCRIPT_VERSION.split()[-1]}
set -euo pipefail

# 环境变量（cron 缺少完整 PATH 时容易出问题）
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

# ── MySQL 备份 ───────────────────────────────────────────────────────
if [ -n "${{MYSQL_DB:-}}" ]; then
    MYSQL_FILE="$BACKUP_DIR/tmp-mysql-$MYSQL_DB-$(date +%Y%m%d-%H%M%S).sql"
    MYSQL_7Z="$BACKUP_DIR/backup-mysql-$(date +%Y%m%d-%H%M%S).7z"
    
    log "开始 MySQL 备份 → $MYSQL_7Z"
    
    if mysqldump -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" \\
        {'--all-databases' if db_name.lower() == 'all' else '--databases "$MYSQL_DB"'} \\
        --single-transaction --quick --set-gtid-purged=OFF > "$MYSQL_FILE" 2>>"$BACKUP_DIR/backup.log"
    then
        if 7z a -t7z -mhe=on -p"$ENCRYPT_PASS" "$MYSQL_7Z" "$MYSQL_FILE" >/dev/null 2>&1
        then
            rm -f "$MYSQL_FILE"
            backup_files+=("$MYSQL_7Z")
            log "MySQL 备份成功"
        else
            log "ERROR: 7z 压缩 MySQL 失败"
            has_error=1
        fi
    else
        log "ERROR: mysqldump 失败"
        has_error=1
        rm -f "$MYSQL_FILE"
    fi
fi

# ── Gitea 备份 ───────────────────────────────────────────────────────
if [ -n "${{GITEA_WORK_DIR:-}}" ]; then
    GITEA_TMP_ZIP="$BACKUP_DIR/tmp-gitea-dump-$(date +%Y%m%d-%H%M%S).zip"
    GITEA_7Z="$BACKUP_DIR/backup-gitea-$(date +%Y%m%d-%H%M%S).7z"
    
    log "开始 Gitea dump → $GITEA_7Z"
    
    cd "$GITEA_WORK_DIR" || {{ log "无法进入 Gitea 工作目录"; has_error=1; }}
    
    if gitea dump --file "$GITEA_TMP_ZIP" >/dev/null 2>>"$BACKUP_DIR/backup.log"
    then
        if [ -f "$GITEA_TMP_ZIP" ]; then
            if 7z a -t7z -mhe=on -p"$ENCRYPT_PASS" "$GITEA_7Z" "$GITEA_TMP_ZIP" >/dev/null 2>&1
            then
                rm -f "$GITEA_TMP_ZIP"
                backup_files+=("$GITEA_7Z")
                log "Gitea 备份成功"
            else
                log "ERROR: 7z 压缩 Gitea 失败"
                has_error=1
            fi
        else
            log "ERROR: gitea dump 没有生成 zip 文件"
            has_error=1
        fi
    else
        log "ERROR: gitea dump 命令失败"
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
        # 使用 jq 更可靠地获取远程大小
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

    # 添加 cron 任务（带 PATH）
    cron_content = f"""# MySQL & Gitea 自动备份 - {datetime.now().strftime('%Y-%m-%d')}
{minute} {hour} * * * root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin {BACKUP_SCRIPT_PATH}
"""

    with open(CRON_PATH, "w", encoding="utf-8") as f:
        f.write(cron_content)

    print("\n" + "="*78)
    print("配置完成！（修复加强版 v3.1）")
    print(f"备份脚本：  {BACKUP_SCRIPT_PATH}")
    print(f"定时任务：  {CRON_PATH}")
    print(f"日志文件：  {backup_dir}/backup.log")
    print(f"加密密码：  128 个 '1'（可自行编辑脚本修改）")
    print("\n建议立即测试一次：")
    print(f"  sudo {BACKUP_SCRIPT_PATH}")
    print("\n卸载方式：")
    print(f"  sudo rm {BACKUP_SCRIPT_PATH}")
    print(f"  sudo rm {CRON_PATH}")
    print(f"  rclone config delete {RCLONE_REMOTE_NAME}   # 如不需要")
    print("="*78)


def uninstall():
    print("卸载指引：")
    print(f"  sudo rm -f {BACKUP_SCRIPT_PATH}")
    print(f"  sudo rm -f {CRON_PATH}")
    print(f"  rclone config delete {RCLONE_REMOTE_NAME}  # 可选")
    print("  # 记得检查 crontab 是否还有残留任务")


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("--uninstall", "-u", "uninstall"):
        uninstall()
    else:
        install()


if __name__ == "__main__":
    if not is_root():
        print("建议使用 root 或 sudo 执行本脚本\n")
    main()