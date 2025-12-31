#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键构建 Flutter + act-latest 全能 Runner 镜像 + 可选注册 Runner（支持三种 Flutter 来源）
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
console.print("[bold green]三种 Flutter 获取方式：本地目录 / 远程 git clone / 官方 tar.xz 下载[/]\n")

console.print(Panel(
    "三种方式说明：\n"
    "1. 本地目录：已下载解压好的 Flutter 目录（最快）\n"
    "2. 远程 git clone：从 GitHub 下载（网络需稳定）\n"
    "3. 官方 tar.xz 下载：脚本自动下载稳定版 zip 包（推荐！避开 git 坑）\n\n"
    "官方下载示例链接：https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.3-stable.tar.xz\n"
    "输入版本号（如 3.24.3），脚本自动构造链接下载",
    title="获取方式说明", style="bold cyan"
))

# 1. 选择 Flutter 来源
source_choice = Prompt.ask(
    "选择 Flutter 来源",
    choices=["本地目录", "远程 git clone", "官方 tar.xz 下载"],
    default="官方 tar.xz 下载"
)

local_flutter_path = None
channel = "stable"
version = "latest"

if source_choice == "本地目录":
    local_flutter_path = Prompt.ask(
        "本地 Flutter 目录完整路径（推荐 /opt/flutter-stable）",
        default="/opt/flutter-stable"
    )
    local_flutter_path = Path(local_flutter_path).resolve()
    if not local_flutter_path.exists() or not (local_flutter_path / "bin/flutter").exists():
        console.print(f"[bold red]路径 {local_flutter_path} 不存在或不是 Flutter 目录！[/]")
        sys.exit(1)
    console.print(f"[green]使用本地 Flutter：{local_flutter_path}[/]")

elif source_choice == "远程 git clone":
    channel = Prompt.ask("Flutter 频道", choices=["stable", "beta", "master"], default="stable")
    version_input = Prompt.ask(f"具体版本（留空用最新）", default="")
    version = version_input if version_input else "latest"
    console.print(f"[green]将 git clone {channel}/{version}[/]")

else:  # 官方 tar.xz 下载
    version = Prompt.ask(
        "Flutter 版本号（如 3.24.3，留空用最新稳定版）",
        default=""
    )
    if not version:
        version = "latest"
    console.print(f"[green]将自动下载官方 tar.xz：Flutter {version} stable[/]")

image_name = Prompt.ask("最终镜像名称", default=f"my-act-flutter:{channel}")

console.print(f"\n[bold yellow]即将构建：{image_name}[/]")
console.print(f"Flutter 来源：{source_choice}")
if source_choice == "远程 git clone":
    console.print(f"channel={channel}, version={version}")
elif source_choice == "官方 tar.xz 下载":
    console.print(f"version={version}")

if not Confirm.ask("确认开始构建？", default=True):
    sys.exit(0)

# 临时构建目录
temp_dir = Path("/tmp/flutter_act_builder")
temp_dir.mkdir(parents=True, exist_ok=True)
dockerfile_path = temp_dir / "Dockerfile"

flutter_copy_dest = temp_dir / "flutter"

if source_choice == "本地目录":
    console.print("[cyan]复制本地 Flutter 到构建上下文...[/]")
    run(f"cp -r {local_flutter_path} {flutter_copy_dest}")

elif source_choice == "官方 tar.xz 下载":
    console.print("[cyan]下载官方 Flutter tar.xz...（视网络情况）[/]")
    if version == "latest":
        # 最新稳定版链接（需要先查最新版本号，这里简化用一个示例，实际可动态获取）
        console.print("[yellow]最新版链接需手动确认，建议指定版本号[/]")
        download_url = Prompt.ask("请输入完整 tar.xz 下载链接", default="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.3-stable.tar.xz")
    else:
        download_url = f"https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_{version}-stable.tar.xz"

    tar_file = temp_dir / f"flutter_{version}.tar.xz"
    run(f"wget -O {tar_file} {download_url}")
    console.print("[cyan]解压 Flutter...[/]")
    run(f"tar xf {tar_file} -C {temp_dir}")
    run(f"mv {temp_dir}/flutter {flutter_copy_dest}")
    tar_file.unlink(missing_ok=True)  # 清理 tar 包

else:  # git clone 方式
    pass  # 后面 Dockerfile 处理

# 生成 Dockerfile
if source_choice in ["本地目录", "官方 tar.xz 下载"]:
    dockerfile_content = f"""FROM ghcr.io/catthehacker/ubuntu:act-latest

RUN apt-get update && apt-get install -y \\
    clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY flutter /opt/flutter

ENV FLUTTER_HOME=/opt/flutter
ENV PATH="${{FLUTTER_HOME}}/bin:${{PATH}}"

RUN flutter precache --universal --android --ios --web --linux && \\
    flutter doctor --android-licenses --accept-all && \\
    flutter create --platforms=android temp_app && \\
    cd temp_app && flutter pub get && flutter build apk --debug && rm -rf temp_app

RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
"""
else:
    dockerfile_content = f"""FROM ghcr.io/catthehacker/ubuntu:act-latest

RUN apt-get update && apt-get install -y \\
    ca-certificates curl git libcurl4-openssl-dev \\
    && update-ca-certificates \\
    && git config --global http.postBuffer 524288000 \\
    && git config --global http.sslVersion tlsv1.2 \\
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \\
    clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev \\
    && rm -rf /var/lib/apt/lists/*

ARG FLUTTER_CHANNEL={channel}
ARG FLUTTER_VERSION={version}
ENV FLUTTER_HOME=/opt/flutter
RUN git clone https://github.com/flutter/flutter.git -b ${{FLUTTER_CHANNEL}} --depth 1 ${{FLUTTER_HOME}} && \\
    cd ${{FLUTTER_HOME}} && \\
    if [ "${{FLUTTER_VERSION}}" != "latest" ]; then \\
        git fetch --depth 1 origin tag ${{FLUTTER_VERSION}} && \\
        git checkout FETCH_HEAD; \\
    fi && \\
    ${{FLUTTER_HOME}}/bin/flutter precache --universal --android --ios --web --linux && \\
    ${{FLUTTER_HOME}}/bin/flutter doctor --android-licenses --accept-all

ENV PATH="${{FLUTTER_HOME}}/bin:${{PATH}}"

RUN flutter create --platforms=android temp_app && \\
    cd temp_app && flutter pub get && flutter build apk --debug && rm -rf temp_app

RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
"""

dockerfile_path.write_text(dockerfile_content)

console.print("[bold cyan]开始构建镜像...[/]")

try:
    run(f"docker build -t {image_name} -f {dockerfile_path} {temp_dir}")
    console.print("[bold green]构建完成！[/]")
except subprocess.CalledProcessError as e:
    console.print(f"[bold red]构建失败：{e}[/]")
    sys.exit(1)

# 清理
dockerfile_path.unlink(missing_ok=True)
if source_choice == "官方 tar.xz 下载":
    run(f"rm -rf {temp_dir}/flutter*")
try:
    temp_dir.rmdir()
except:
    pass

console.print(Panel(
    f"镜像构建成功！\n\n"
    f"镜像：{image_name}\n"
    f"Flutter 来源：{source_choice}\n\n"
    f"使用方式：在 Runner labels 中添加：\n"
    f"  flutter-{channel}:docker://{image_name}\n\n"
    f"Flutter 项目 workflow：runs-on: flutter-{channel}\n\n"
    f"查看镜像：docker images | grep {image_name.split(':')[0]}",
    title="构建完成！", style="bold green"
))