#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Act Runner 独立部署脚本（2025 版）
支持 Flutter 项目（使用预置镜像 + label）
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

console.rule("[bold magenta]Gitea Act Runner 独立部署 v1.0[/]")

console.print(Panel(
    "[bold yellow]推荐使用 --network host 模式（代理/DNS 环境最稳）[/]\n"
    "GITEA_INSTANCE_URL 建议：http://127.0.0.1:3000/ 或 http://192.168.0.169:3000/\n"
    "Flutter 项目支持：已包含 flutter:stable 等 label",
    title="使用提示", style="bold yellow"
))

existing_runner = subprocess.getoutput("docker ps -a --filter name=^gitea-runner$ --format '{{.Names}}'").strip()
if existing_runner == "gitea-runner":
    if Confirm.ask("检测到已存在 gitea-runner，是否升级/重新注册？", default=True):
        run("docker stop gitea-runner || true")
        run("docker rm gitea-runner || true")
        run("rm -rf /data/gitea_runner/data/.runner*")  # 清理旧凭证

runner_dir = Path("/data/gitea_runner")
runner_dir.mkdir(parents=True, exist_ok=True)
(runner_dir / "data").mkdir(exist_ok=True)
(runner_dir / "cache").mkdir(exist_ok=True)

gitea_url = Prompt.ask("Gitea 完整 URL（推荐宿主机本地地址）", default="http://127.0.0.1:3000/")
if not gitea_url.endswith('/'):
    gitea_url += '/'

console.print("\n[bold yellow]获取 Token：[/]")
console.print(f"1. 打开 {gitea_url} → 管理员 → Site Administration → Actions → Runners")
console.print("2. 选择 [全局/组织/仓库] → Create runner → 复制 Token\n")
token = Prompt.ask("粘贴 Registration Token")

runner_name = Prompt.ask("Runner 名称", default="dev-runner")

# Flutter 支持：添加常用 Flutter label
labels = (
    "ubuntu-latest:docker://node:20-bullseye,"
    "ubuntu-24.04:docker://node:20,"
    "flutter:stable:docker://cirrusci/flutter:stable,"  # Flutter 官方稳定版
    "flutter:beta:docker://cirrusci/flutter:beta,"
    "native:host"
)

console.print(f"\n[green]将使用 labels：{labels}[/]")

network_choice = Confirm.ask("是否使用 host 网络模式？（推荐：代理环境最稳）", default=True)
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
for _ in range(30):
    logs = subprocess.getoutput("docker logs gitea-runner 2>&1")
    if "Runner registered successfully" in logs:
        console.print("[bold green]Runner 注册成功！[/]")
        break
    time.sleep(5)
else:
    console.print("[yellow]注册可能仍在进行，可查看：docker logs -f gitea-runner[/]")

console.print(Panel(
    f"Runner 已部署！\n"
    f"URL: {gitea_url}\n"
    f"名称: {runner_name}\n"
    f"Flutter 支持：使用 runs-on: flutter:stable\n"
    f"日志：docker logs -f gitea-runner",
    title="部署完成", style="bold green"
))