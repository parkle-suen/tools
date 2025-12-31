#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键构建 Flutter + act-latest 全能 Runner 镜像 + 可选注册 Runner（2025 版）
"""

import os
import sys
import subprocess
import time
from pathlib import Path

try:
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.console import Console
except ImportError:
    print("\033[93m正在安装 rich...\033[0m")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.console import Console

console = Console()

def run(cmd: str, capture=False):
    kwargs = {"shell": True, "check": True, "text": True}
    if capture:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs)

if os.geteuid() != 0:
    console.print("[bold red]请使用 sudo 或 root 权限运行此脚本[/]")
    sys.exit(1)

console.rule("[bold magenta]Flutter + act-latest 全能 Runner 镜像构建 & Runner 注册工具[/]")
console.print("[bold green]目标：一键构建集成 Flutter 的 act-latest 镜像，可选立即注册 Runner[/]\n")

# 默认值
DEFAULT_FLUTTER_CHANNEL = "stable"
DEFAULT_FLUTTER_VERSION = "3.24.3"
DEFAULT_IMAGE_NAME = f"my-act-flutter:{DEFAULT_FLUTTER_CHANNEL}"

console.print(Panel(
    "此脚本将自动执行以下步骤：\n"
    "1. 生成临时 Dockerfile\n"
    "2. 构建自定义镜像（基于 act-latest + 指定 Flutter 版本）\n"
    "3. 验证构建结果\n"
    "4. 可选：立即注册/更新 Gitea Runner（使用新镜像）\n\n"
    "Flutter 项目使用方式：runs-on: flutter-stable（或你指定的 tag）\n",
    title="功能说明", style="bold cyan"
))

# 1. 用户输入 Flutter 配置
channel = Prompt.ask(
    "Flutter 频道",
    choices=["stable", "beta", "master"],
    default=DEFAULT_FLUTTER_CHANNEL
)

version = Prompt.ask(
    f"Flutter 具体版本（留空使用 {channel} 最新）",
    default=""
)

if not version:
    version = "latest"
    console.print(f"[green]将使用 {channel} 频道的最新版本[/]")
else:
    console.print(f"[green]将使用指定版本：{version}[/]")

# 2. 用户指定镜像名称
image_name = Prompt.ask(
    "最终镜像名称（格式：repository:tag）",
    default=DEFAULT_IMAGE_NAME
)

console.print(f"\n[bold yellow]即将构建镜像：{image_name}[/]")
console.print(f"Flutter：{channel} / {version if version != 'latest' else '最新'}")
console.print("[yellow]构建过程首次约 5–20 分钟，后续 tag 很快[/]")

if not Confirm.ask("确认开始构建镜像？", default=True):
    console.print("[yellow]已取消[/]")
    sys.exit(0)

# 3. 生成临时 Dockerfile
temp_dir = Path("/tmp/flutter_act_builder")
temp_dir.mkdir(parents=True, exist_ok=True)
dockerfile_path = temp_dir / "Dockerfile"

dockerfile_content = f"""FROM ghcr.io/catthehacker/ubuntu:act-latest

# 修复 GnuTLS TLS 问题：切换到 OpenSSL + 更新证书
RUN apt-get update && apt-get install -y \\
    ca-certificates curl git libcurl4-openssl-dev \\
    && update-ca-certificates \\
    && git config --global http.sslVersion tlsv1.2 \\
    && rm -rf /var/lib/apt/lists/*

# 安装 Flutter 额外依赖
RUN apt-get update && apt-get install -y \\
    clang cmake ninja-build pkg-config \\
    libgtk-3-dev liblzma-dev \\
    && rm -rf /var/lib/apt/lists/*

# 安装 Flutter（加 --verbose 看进度，--depth 1 浅克隆）
ARG FLUTTER_CHANNEL={channel}
ARG FLUTTER_VERSION={version}
ENV FLUTTER_HOME=/opt/flutter
RUN git config --global http.postBuffer 524288000 \\
    && git clone --verbose https://github.com/flutter/flutter.git -b ${{FLUTTER_CHANNEL}} --depth 1 ${{FLUTTER_HOME}} && \\
    cd ${{FLUTTER_HOME}} && \\
    if [ "${{FLUTTER_VERSION}}" != "latest" ]; then \\
        git fetch --depth 1 origin tag ${{FLUTTER_VERSION}} && \\
        git checkout FETCH_HEAD; \\
    fi && \\
    ${{FLUTTER_HOME}}/bin/flutter precache --universal --android --ios --web --linux && \\
    ${{FLUTTER_HOME}}/bin/flutter doctor --android-licenses --accept-all

ENV PATH="${{FLUTTER_HOME}}/bin:${{PATH}}"

# 预热
RUN flutter create --platforms=android temp_app && \\
    cd temp_app && flutter pub get && flutter build apk --debug && rm -rf temp_app

# 清理
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
"""

dockerfile_path.write_text(dockerfile_content)

console.print(Panel(
    f"Dockerfile 已生成：{dockerfile_path}\n"
    "构建命令预览：docker build -t {image_name} ...\n",
    title="步骤 1/4：Dockerfile 准备完成", style="bold green"
))

# 4. 构建镜像
console.print("[bold cyan]步骤 2/4：开始构建镜像（请耐心等待）...[/]")
with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
    task = progress.add_task("构建中（首次可能较慢）...", total=None)
    try:
        run(f"docker build -t {image_name} -f {dockerfile_path} {temp_dir}")
        progress.update(task, completed=True)
        console.print("[bold green]构建完成！[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]构建失败！请检查网络或日志[/]")
        console.print(e)
        sys.exit(1)

# 清理临时文件
dockerfile_path.unlink(missing_ok=True)
try:
    temp_dir.rmdir()
except:
    pass

# 5. 验证镜像
console.print("[bold cyan]步骤 3/4：验证镜像...[/]")
images = run(f"docker images {image_name.split(':')[0]}", capture=True).stdout
console.print(Panel(
    f"已构建镜像：\n{images}\n"
    f"大小正常（约 5–10GB）说明成功。",
    title="验证成功", style="bold green"
))

# 6. 可选：立即注册/更新 Runner
console.print("\n[bold cyan]步骤 4/4：是否现在注册/更新 Gitea Runner？[/]")
console.print("[yellow]推荐使用 host 网络模式 + 新镜像[/]")

if Confirm.ask("立即注册 Runner？", default=True):
    # 清理旧 runner
    existing = run("docker ps -a --filter name=^gitea-runner$ --format '{{.Names}}'", capture=True).stdout.strip()
    if existing:
        if Confirm.ask("检测到旧 runner，是否删除并重新注册？", default=True):
            run("docker stop gitea-runner || true")
            run("docker rm gitea-runner || true")
            run("rm -rf /data/gitea_runner/data/.runner*")

    # 创建数据目录
    runner_dir = Path("/data/gitea_runner")
    runner_dir.mkdir(parents=True, exist_ok=True)
    (runner_dir / "data").mkdir(exist_ok=True)
    (runner_dir / "cache").mkdir(exist_ok=True)

    gitea_url = Prompt.ask("Gitea URL（推荐本地）", default="http://127.0.0.1:3000/")
    if not gitea_url.endswith('/'):
        gitea_url += '/'

    console.print("\n[bold yellow]获取 Token：[/]")
    console.print(f"打开 {gitea_url} → 管理员 → Actions → Runners → Create runner → 复制 Token")
    token = Prompt.ask("粘贴 Token")

    runner_name = Prompt.ask("Runner 名称", default="flutter-act-runner")

    use_host = Confirm.ask("使用 host 网络模式？（强烈推荐）", default=True)
    network_cmd = "--network host" if use_host else ""

    # Labels：包含新构建的 Flutter 镜像
    flutter_label = f"flutter-{channel}:docker://{image_name}"
    labels = (
        "ubuntu-latest:docker://ghcr.io/catthehacker/ubuntu:act-latest,"
        f"{flutter_label},"
        "native:host"
    )

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

    console.print("等待注册...")
    time.sleep(10)
    success = False
    for _ in range(40):
        logs = run("docker logs gitea-runner 2>&1", capture=True).stdout
        if "Runner registered successfully" in logs:
            console.print("[bold green]Runner 注册成功！[/]")
            success = True
            break
        time.sleep(5)

    if not success:
        console.print("[yellow]注册可能仍在进行：docker logs -f gitea-runner[/]")

console.print(Panel(
    f"操作完成！\n\n"
    f"镜像：{image_name}\n"
    f"Runner 已就绪（如果选择注册）\n\n"
    f"Flutter 项目使用：\n"
    f"  runs-on: flutter-{channel}\n\n"
    f"查看镜像：docker images | grep {image_name.split(':')[0]}\n"
    f"查看 Runner 日志：docker logs -f gitea-runner\n"
    f"后续更新 Flutter：重新跑脚本 → 指定新版本 + 新 tag 即可",
    title="全部完成！", style="bold green"
))