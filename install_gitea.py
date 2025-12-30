#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea + PostgreSQL 一键部署脚本（2025 开发友好版）
只负责 Gitea 和 PG，默认使用 bridge 网络
PG 暴露 5433:5432 端口，便于 pgAdmin 等外部连接
"""

import os
import sys
import subprocess
from pathlib import Path
from rich import print
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn

# 依赖安装（简化版）
print("\033[93m检查 Python 环境...\033[0m")
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

console.rule("[bold magenta]Gitea + PostgreSQL 一键部署 v1.0（默认 bridge 网络）[/]")

region = Prompt.ask("部署地区", choices=["china", "global"], default="global")
if region == "china":
    gitea_image = "gitea/gitea:latest-rootless"
    docker_mirror = "--registry-mirror=https://mirror.ccs.tencentyun.com"
else:
    gitea_image = "gitea/gitea:latest"
    docker_mirror = ""

domain = Prompt.ask("对外访问域名或 IP", default="localhost")
port = IntPrompt.ask("Gitea HTTP 端口", default=3000)
gitea_url = f"http://{domain}:{port}"
if not gitea_url.endswith('/'):
    gitea_url += '/'

console.print(Panel("开始部署 Gitea + PostgreSQL（默认 bridge 网络）", style="bold green"))

compose_content = f'''version: "3.8"

# networks:  # ← 全部注释，使用默认 bridge 网络
#   gitea:
#     external: false

services:
  server:
    image: {gitea_image}
    container_name: gitea
    restart: always
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=gitea-postgres:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=gitea
      - GITEA__database__PASSWD=11111111
      - GITEA__server__ROOT_URL={gitea_url}
      - GITEA__server__HTTP_PORT=3000
    volumes:
      - /data/gitea/data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "{port}:3000"
      - "2222:22"
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    container_name: gitea-postgres
    restart: always
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=11111111
      - POSTGRES_DB=gitea
    volumes:
      - /data/gitea/postgres:/var/lib/postgresql/data
    ports:
      - "5433:5432"  # 外部连接用 localhost:5433
'''

Path("/data/gitea").mkdir(parents=True, exist_ok=True)
Path("/data/gitea/postgres").mkdir(parents=True, exist_ok=True)
Path("/data/gitea/docker-compose.yml").write_text(compose_content.strip() + "\n")

with Progress(SpinnerColumn(), TextColumn("正在启动 Gitea...")) as p:
    t = p.add_task("", total=None)
    os.chdir("/data/gitea")
    if docker_mirror:
        run(f"docker {docker_mirror} compose pull")
    run("docker compose up -d")
    p.update(t, completed=True)

console.print(Panel(
    f"部署完成！请访问 [bold cyan]{gitea_url}[/] 完成首次安装向导\n"
    f"管理员账号建议：admin / 11111111\n"
    f"[bold red]Site URL 必须填写为：{gitea_url}[/]\n\n"
    f"PostgreSQL 外部连接：localhost:5433 / 用户 gitea / 密码 11111111 / 数据库 gitea\n"
    f"所有服务默认使用 bridge 网络，容器间用容器名访问",
    title="Gitea 部署成功", style="bold green"
))