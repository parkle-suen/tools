#!/usr/bin/env python3

import os
import subprocess
import sys

def run_command(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"命令失败: {cmd}")
        sys.exit(1)

print("开始安装常用终端工具（适用于 Ubuntu/Debian）...")

# 更新软件源
run_command("sudo apt update")

# 安装主要工具
packages = [
    "fish",          # fish shell
    "fd-find",       # fd-find (命令为 fdfind，需要重命名)
    "bat",           # bat (命令为 batcat，需要重命名)
    "moreutils",     # 提供 more（但 more 已内置，这里安装额外实用工具）
    "tldr",          # tldr
    "htop",          # htop
    "micro",         # micro 编辑器
    "nano",          # nano 编辑器
    "ripgrep",       # ripgrep (rg)
    "eza",           # eza (现代 ls 替代)
    "duf",           # duf
    "bottom",        # bottom (btm)
    "git",           # git
]

# dust 未在官方仓库中，使用 cargo 安装（需要先安装 rust/cargo）
print("安装主要包...")
run_command(f"sudo apt install -y {' '.join(packages)}")

# 安装 dust（Rust 工具，需要 cargo）
print("安装 dust（需要 cargo）...")
run_command("sudo apt install -y cargo")
run_command("cargo install du-dust")

# 处理 fd-find 重命名为 fd
fd_link = "/usr/local/bin/fd"
if not os.path.exists(fd_link):
    print("创建 fd -> fdfind 符号链接...")
    run_command("sudo ln -s $(which fdfind) /usr/local/bin/fd")

# 处理 bat 重命名为 bat（避免与系统 bat 冲突）
bat_link = "/usr/local/bin/bat"
if not os.path.exists(bat_link):
    print("创建 bat -> batcat 符号链接...")
    run_command("sudo ln -s $(which batcat) /usr/local/bin/bat")

# 更新 tldr 数据
print("更新 tldr 数据...")
run_command("tldr --update")

print("所有工具安装完成！")
print("建议将 fish 设置为默认 shell: sudo chsh -s $(which fish) $USER")