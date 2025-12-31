#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Act Runner 独立部署脚本（2025 开发版 - act-latest 全能 + Flutter 首次安装）
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from rich import print
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

# 依赖检查
try:
    import rich
except ImportError:
    print("\033[93m安装 rich...\033[0m")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])

from rich.console import Console
console = Console()

def run(cmd: str):
    return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

if os.geteuid() != 0:
    console.print("[bold red]请使用 sudo 或 root 权限运行此脚本[/]")
    sys.exit(1)

console.rule("[bold magenta]Gitea Act Runner 独立部署 v1.1（act-latest 全能版）[/]")

console.print(Panel(
    "[bold yellow]推荐使用 --network host 模式（代理/DNS 环境最稳）[/]\n"
    "GITEA_INSTANCE_URL 建议：http://127.0.0.1:3000/ 或 http://192.168.0.169:3000/\n"
    "Flutter 支持：使用 act-latest 镜像，首次任务自动下载 Flutter SDK（后续缓存）\n"
    "所有项目公用一套 runner（JDK17 + Android + Node + Flutter 等）",
    title="使用提示", style="bold yellow"
))
console.print("### 脚本文件末尾有示例workflow<首次安装版> ###")

# 清理旧 runner
existing_runner = subprocess.getoutput("docker ps -a --filter name=^gitea-runner$ --format '{{.Names}}'").strip()
if existing_runner == "gitea-runner":
    if Confirm.ask("检测到已存在 gitea-runner，是否停止/删除并重新注册？", default=True):
        run("docker stop gitea-runner || true")
        run("docker rm gitea-runner || true")
        run("rm -rf /data/gitea_runner/data/.runner*")  # 清理旧注册凭证

runner_dir = Path("/data/gitea_runner")
runner_dir.mkdir(parents=True, exist_ok=True)
(runner_dir / "data").mkdir(exist_ok=True)
(runner_dir / "cache").mkdir(exist_ok=True)

gitea_url = Prompt.ask("Gitea 完整 URL（推荐宿主机本地地址）", default="http://127.0.0.1:3000/")
if not gitea_url.endswith('/'):
    gitea_url += '/'

console.print("\n[bold yellow]获取 Token（组织级/全局/仓库级均可）：[/]")
console.print(f"1. 打开 {gitea_url} → 管理员 → Site Administration → Actions → Runners")
console.print("2. 选择对应级别 → Create runner → 复制 Token\n")
token = Prompt.ask("粘贴 Registration Token")

runner_name = Prompt.ask("Runner 名称", default="all-in-one-runner")

# Labels：以 act-latest 为主，Flutter 在 workflow 里首次安装
labels = (
    "ubuntu-latest:docker://ghcr.io/catthehacker/ubuntu:act-latest,"
    "ubuntu-24.04:docker://ghcr.io/catthehacker/ubuntu:act-24.04,"
    "native:host"
)

console.print(f"\n[green]将使用 labels（act-latest 全能版）：{labels}[/]")
console.print("[green]Flutter 项目：在 workflow 首次运行时自动安装 Flutter SDK，后续缓存[/]")

network_choice = Confirm.ask("是否使用 host 网络模式？（强烈推荐：代理环境最稳）", default=True)
network_cmd = "--network host" if network_choice else ""

cmd = f"""
docker run -d \\
  --name gitea-runner \\
  --restart unless-stopped \\
  {network_cmd} \\
  -e GITEA_INSTANCE_URL="{gitea_url}" \\
  -e GITEA_RUNNER_REGISTRATION_TOKEN="{token}" \\
  -e GITEA_RUNNER_NAME="{runner_name}" \\
  -e GITEA_RUNNER_LABELS="{labels}" \\
  -v /data/gitea_runner/data:/data \\
  -v /data/gitea_runner/cache:/cache \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  gitea/act_runner:latest daemon
""".strip()

console.print("正在启动 Runner...")
run(cmd)

console.print("等待注册完成...")
time.sleep(10)
for _ in range(40):
    logs = subprocess.getoutput("docker logs gitea-runner 2>&1")
    if "Runner registered successfully" in logs or "level=info msg=\"Runner is running\"" in logs:
        console.print("[bold green]Runner 注册成功！[/]")
        break
    time.sleep(5)
else:
    console.print("[yellow]注册可能仍在进行，可查看：docker logs -f gitea-runner[/]")

console.print(Panel(
    f"Runner 已部署成功！\n"
    f"URL: {gitea_url}\n"
    f"名称: {runner_name}\n"
    f"主镜像: act-latest（JDK17 + Android + Node + ...）\n"
    f"Flutter 支持：首次任务自动下载 SDK，后续缓存\n"
    f"日志：docker logs -f gitea-runner\n"
    f"建议 workflow runs-on: ubuntu-latest",
    title="部署完成", style="bold green"
))

# name: Flutter Build APK

# on: [push]

# jobs:
#   build:
#     runs-on: ubuntu-latest  # 使用 act-latest 镜像
#     steps:
#       - uses: actions/checkout@v4

#       - name: Setup Flutter
#         uses: subosito/flutter-action@v2
#         with:
#           flutter-version: '3.24.3'  # 你想要的版本
#           channel: 'stable'
#           cache: true  # 启用缓存，第二次以后超快

#       - name: Install dependencies
#         run: flutter pub get

#       - name: Build APK
#         run: flutter build apk --release

#       - name: Upload artifact
#         uses: actions/upload-artifact@v4
#         with:
#           name: app-release.apk
#           path: build/app/outputs/flutter-apk/app-release.apk