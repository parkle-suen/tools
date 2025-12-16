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

# 安装主要工具（移除旧的 tldr 包，避免冲突）
packages = [
    "fish",          # fish shell
    "fd-find",       # fd-find (命令为 fdfind，需要重命名)
    "bat",           # bat (命令为 batcat，需要重命名)
    "moreutils",     # 提供更多实用工具
    "htop",          # htop
    "micro",         # micro 编辑器
    "nano",          # nano 编辑器
    "ripgrep",       # ripgrep (rg)
    "git",           # git
    "python3-pip",   # pip for Python 3w
    "curl",          # curl"
]

print("安装主要包...")
run_command(f"sudo apt install -y {' '.join(packages)}")

# 安装官方 Python 版 tldr（推荐，最成熟，支持自动缓存更新）
print("安装官方 Python 版 tldr（避免旧包 git 分支问题）...")
run_command("pip3 install --user --upgrade tldr")

# 安装 Python 常用命令行美化库
# rich：最强一站式（彩色、表格、进度条、Markdown、语法高亮）
# tabulate：如果你需要额外表格功能（rich 已内置强大表格，通常够用）
print("安装 Python 常用终端美化库（优先 rich）...")
run_command("pip3 install --user --upgrade rich")
# 如果你觉得 rich 的表格不够用，再取消下面注释安装 tabulate
# run_command("pip3 install --user --upgrade tabulate")

# 其他可选好用库（取消注释安装）：
# run_command("pip3 install --user --upgrade tqdm")  # 进度条神器
# run_command("pip3 install --user --upgrade colorama")  # Windows 颜色支持
# run_command("pip3 install --user --upgrade requests beautifulsoup4")  # 网络爬虫常用

# 处理 fd 重命名
fd_link = "/usr/local/bin/fd"
if not os.path.exists(fd_link):
    print("创建 fd -> fdfind 符号链接...")
    run_command("sudo ln -s $(which fdfind) /usr/local/bin/fd")

# 处理 bat 重命名
bat_link = "/usr/local/bin/bat"
if not os.path.exists(bat_link):
    print("创建 bat -> batcat 符号链接...")
    run_command("sudo ln -s $(which batcat) /usr/local/bin/bat")

# Python 版 tldr 会自动下载/更新缓存，无需手动 --update
# 第一次运行 tldr tar 时会自动拉取最新页面
print("tldr 安装完成！首次使用如 'tldr tar' 会自动下载缓存。")

print("所有工具安装完成！")
print("建议将 fish 设置为默认 shell: sudo chsh -s $(which fish) $USER")
print("Python 库建议：rich 超级强大，几乎所有美化需求都能满足（包括漂亮表格）！")
print("注意：pip --user 安装的命令在 ~/.local/bin，确保它在 PATH 中（大多数现代 Ubuntu 已自动添加）。")
print("如果命令未找到，可运行: echo 'export PATH=\"$PATH:$HOME/.local/bin\"' >> ~/.bashrc && source ~/.bashrc")