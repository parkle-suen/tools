#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Java + Flutter Runner 一键构建工具
简化版 - 专注于最常用的两个 Runner
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

try:
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("\033[93m正在安装 rich...\033[0m")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run(cmd: str, capture=False, check=True):
    """运行命令"""
    kwargs = {"shell": True, "check": check, "text": True}
    if capture:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs)

def check_root():
    """检查是否为 root 权限"""
    if os.geteuid() != 0:
        console.print("[bold red]请使用 sudo 运行此脚本[/]")
        sys.exit(1)

def show_menu():
    """显示主菜单"""
    console.clear()
    console.rule("[bold magenta]🚀 Gitea Runner 一键构建工具[/]")
    
    console.print(Panel.fit(
        "[bold cyan]专注两个最常用 Runner：[/]\n\n"
        "1. [green]Java 17 Runner[/] - Spring Boot、Java 项目\n"
        "2. [green]Flutter Runner[/] - Flutter 移动应用开发\n\n"
        "✅ [yellow]专用 Runner，构建快，环境纯净[/]\n"
        "✅ [yellow]自动注册到 Gitea Actions[/]",
        title="功能说明", border_style="cyan"
    ))

def select_runner_type():
    """选择 Runner 类型"""
    console.print("\n[bold cyan]请选择要构建的 Runner 类型：[/]")
    console.print("1. Java 17 Runner (适合 Spring Boot、Java 项目)")
    console.print("2. Flutter Runner (适合 Flutter 移动应用开发)")
    
    choice = Prompt.ask("输入 1 或 2", choices=["1", "2"], default="1")
    
    if choice == "1":
        return "java", {
            "name": "Java 17",
            "version": "17",
            "description": "Java 17 + Maven + Gradle"
        }
    else:
        return "flutter", {
            "name": "Flutter",
            "version": "3.38.5",  # 固定使用稳定版本
            "description": "Flutter 3.38.5 + Android SDK"
        }

def get_gitea_info():
    """获取 Gitea 基本信息"""
    console.print("\n" + "="*50)
    console.print("[bold yellow]📋 Gitea 配置信息[/]")
    
    # 自动检测本地 IP
    try:
        result = run("hostname -I", capture=True, check=False)
        if result.stdout:
            ips = [ip.strip() for ip in result.stdout.split() if ip.strip()]
            default_url = f"http://{ips[0]}:3000/"
        else:
            default_url = "http://localhost:3000/"
    except:
        default_url = "http://localhost:3000/"
    
    console.print(f"[cyan]自动检测到本地 IP，默认 URL: {default_url}[/]")
    
    gitea_url = Prompt.ask(
        "Gitea 实例 URL (以 / 结尾)",
        default=default_url
    )
    
    if not gitea_url.endswith('/'):
        gitea_url += '/'
    
    console.print("\n[bold yellow]🔑 获取 Registration Token：[/]")
    console.print("1. 访问 Gitea 管理页面：")
    console.print(f"   [blue]{gitea_url}admin/actions/runners[/]")
    console.print("2. 点击 'Create new runner'")
    console.print("3. 复制生成的 Token\n")
    
    token = Prompt.ask("粘贴 Registration Token")
    
    runner_name = Prompt.ask("Runner 名称", default="my-runner")
    
    return {
        "url": gitea_url,
        "token": token,
        "name": runner_name
    }

def build_java_runner(version):
    """构建 Java 17 Runner"""
    console.print(Panel.fit(
        "[bold cyan]开始构建 Java 17 Runner[/]\n\n"
        "包含：OpenJDK 17 + Maven + Gradle\n"
        "适合：Spring Boot、Java 项目",
        title="Java Runner", border_style="cyan"
    ))
    
    temp_dir = Path("/tmp/java-runner-builder")
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    dockerfile_content = """FROM openjdk:17-slim

# 安装常用工具
RUN apt update && apt install -y \\
    ca-certificates curl git wget maven gradle \\
    && rm -rf /var/lib/apt/lists/*

# 验证
RUN java -version && \\
    mvn --version && \\
    gradle --version
    
# 清理
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
"""
    
    dockerfile_path = temp_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)
    
    image_name = "gitea-java-runner:17"
    
    console.print(f"[bold yellow]开始构建镜像：{image_name}[/]")
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("构建中...", total=None)
            run(f"docker build -t {image_name} -f {dockerfile_path} {temp_dir}", capture=True)
            progress.update(task, completed=True)
        
        console.print(f"[bold green]✅ Java Runner 构建成功！[/]")
        
        # 获取镜像大小
        result = run(f"docker images {image_name} --format '{{{{.Size}}}}'", capture=True)
        if result.stdout:
            console.print(f"📏 镜像大小：{result.stdout.strip()}")
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return image_name, "java-17"
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ 构建失败！[/]")
        console.print(f"错误：{e.stderr[:500] if e.stderr else '未知错误'}")
        return None, None

def build_flutter_runner(version):
    """构建 Flutter Runner"""
    console.print(Panel.fit(
        f"[bold cyan]开始构建 Flutter {version} Runner[/]\n\n"
        f"包含：Flutter {version} + Android SDK\n"
        f"适合：Flutter Android 应用开发",
        title="Flutter Runner", border_style="cyan"
    ))
    
    temp_dir = Path("/tmp/flutter-runner-builder")
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    dockerfile_content = f"""FROM ubuntu:22.04

# 设置环境变量避免交互
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础依赖
RUN apt update && apt install -y \\
    ca-certificates curl unzip git wget \\
    clang cmake ninja-build pkg-config \\
    openjdk-17-jdk-headless \\
    libgtk-3-dev liblzma-dev \\
    && rm -rf /var/lib/apt/lists/*

# 设置 Java 环境
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# 安装 Android SDK
RUN mkdir -p /opt/android-sdk/cmdline-tools && \\
    cd /opt/android-sdk/cmdline-tools && \\
    curl -sLO https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip && \\
    unzip -q commandlinetools-linux-11076708_latest.zip && \\
    rm commandlinetools-linux-11076708_latest.zip && \\
    mv cmdline-tools latest

ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

# 接受 Android 许可证
RUN yes | sdkmanager --licenses && \\
    sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# 安装 Flutter
ENV FLUTTER_HOME=/opt/flutter
RUN curl -sLO https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_{version}-stable.tar.xz && \\
    tar xf flutter_linux_{version}-stable.tar.xz -C /opt && \\
    rm flutter_linux_{version}-stable.tar.xz

ENV PATH="$FLUTTER_HOME/bin:$PATH"

# 设置 Flutter
RUN flutter config --no-analytics && \\
    flutter precache --android --linux --web && \\
    yes | flutter doctor --android-licenses

# 验证
RUN flutter --version && \\
    dart --version && \\
    java -version
    
# 清理
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
"""
    
    dockerfile_path = temp_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)
    
    image_name = f"gitea-flutter-runner:{version}"
    
    console.print(f"[bold yellow]开始构建镜像：{image_name}[/]")
    console.print("[cyan]注意：首次构建可能需要 10-20 分钟，请耐心等待...[/]")
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("构建中...", total=None)
            run(f"docker build -t {image_name} -f {dockerfile_path} {temp_dir}", capture=True)
            progress.update(task, completed=True)
        
        console.print(f"[bold green]✅ Flutter Runner 构建成功！[/]")
        
        # 获取镜像大小
        result = run(f"docker images {image_name} --format '{{{{.Size}}}}'", capture=True)
        if result.stdout:
            console.print(f"📏 镜像大小：{result.stdout.strip()}")
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return image_name, f"flutter-{version}"
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ 构建失败！[/]")
        console.print(f"错误：{e.stderr[:500] if e.stderr else '未知错误'}")
        return None, None

def register_runner(image_name, runner_label, gitea_info):
    """注册 Runner 到 Gitea"""
    console.print("\n" + "="*50)
    console.print("[bold yellow]📝 注册 Runner 到 Gitea[/]")
    
    # 生成容器名称
    container_name = f"gitea-runner-{runner_label}".replace(".", "-").replace(":", "-")
    
    # 检查是否已有同名容器
    result = run(f"docker ps -a --filter name=^{container_name}$ --format '{{{{.Names}}}}'", capture=True, check=False)
    
    if result.stdout and result.stdout.strip() == container_name:
        if Confirm.ask(f"已存在容器 '{container_name}'，是否删除并重新创建？", default=True):
            run(f"docker stop {container_name}", check=False)
            run(f"docker rm {container_name}", check=False)
        else:
            console.print("[yellow]跳过注册，使用现有容器[/]")
            return False, container_name
    
    # 准备标签
    labels = f"{runner_label}:docker://{image_name}"
    
    # 启动容器
    console.print(f"[cyan]启动 Runner 容器：{container_name}[/]")
    
    docker_cmd = f"""docker run -d \\
  --name {container_name} \\
  --restart unless-stopped \\
  --network host \\
  -e GITEA_INSTANCE_URL="{gitea_info['url']}" \\
  -e GITEA_RUNNER_REGISTRATION_TOKEN="{gitea_info['token']}" \\
  -e GITEA_RUNNER_NAME="{gitea_info['name']}" \\
  -e GITEA_RUNNER_LABELS="{labels}" \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  gitea/act_runner:latest"""
    
    try:
        run(docker_cmd, capture=True)
        console.print(f"[bold green]✅ Runner 注册成功！[/]")
        
        console.print("\n[bold cyan]📊 Runner 信息：[/]")
        console.print(f"容器名称：{container_name}")
        console.print(f"镜像标签：{runner_label}")
        console.print(f"Gitea URL：{gitea_info['url']}")
        
        return True, container_name
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Runner 注册失败！[/]")
        console.print(f"错误：{e.stderr[:500] if e.stderr else '未知错误'}")
        return False, container_name

def show_usage_guide(runner_type, runner_label, image_name, container_name):
    """显示使用指南"""
    console.print("\n" + "="*50)
    
    if runner_type == "java":
        title = "Java 17 Runner"
        example_workflow = f"""name: Java CI

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: {runner_label}
    steps:
      - uses: actions/checkout@v4
      - run: mvn clean package
      - run: java -jar target/*.jar --version
      
  test:
    runs-on: {runner_label}
    steps:
      - uses: actions/checkout@v4
      - run: mvn test"""
    else:
        title = "Flutter Runner"
        example_workflow = f"""name: Flutter Build

on:
  push:
    branches: [ main ]

jobs:
  build-android:
    runs-on: {runner_label}
    steps:
      - uses: actions/checkout@v4
      - run: flutter pub get
      - run: flutter build apk --release
      - uses: actions/upload-artifact@v4
        with:
          name: app-release
          path: build/app/outputs/flutter-apk/*.apk

  doctor:
    runs-on: {runner_label}
    steps:
      - uses: actions/checkout@v4
      - run: flutter doctor -v"""
    
    console.print(Panel.fit(
        f"[bold green]🎉 {title} 就绪！[/]\n\n"
        f"📦 镜像：{image_name}\n"
        f"🏷️  标签：{runner_label}\n"
        f"📁 容器：{container_name}",
        title="构建完成", border_style="green"
    ))
    
    console.print("\n[bold cyan]📝 使用方法：[/]")
    console.print(f"1. 在项目根目录创建：.gitea/workflows/build.yml")
    console.print(f"2. 在 workflow 中使用：runs-on: {runner_label}")
    console.print(f"3. 示例 workflow 内容：")
    
    console.print(f"\n[bold yellow]{example_workflow}[/]")
    
    console.print("\n[bold cyan]🔧 管理命令：[/]")
    console.print(f"查看日志：docker logs -f {container_name}")
    console.print(f"重启：docker restart {container_name}")
    console.print(f"停止：docker stop {container_name}")
    console.print(f"删除：docker rm {container_name}")
    console.print(f"查看所有 Runner：docker ps --filter name=gitea-runner")

def main():
    """主函数"""
    try:
        # 检查权限
        check_root()
        
        # 显示菜单
        show_menu()
        
        # 选择 Runner 类型
        runner_type, config = select_runner_type()
        
        console.print(f"\n[green]已选择：{config['name']} Runner[/]")
        console.print(f"描述：{config['description']}")
        
        # 确认构建
        if not Confirm.ask("\n确认开始构建？", default=True):
            console.print("[yellow]已取消[/]")
            return
        
        # 获取 Gitea 信息
        gitea_info = None
        if Confirm.ask("是否立即注册到 Gitea？", default=True):
            gitea_info = get_gitea_info()
        
        # 构建镜像
        console.print("\n" + "="*50)
        console.print(f"[bold cyan]开始构建 {config['name']} Runner...[/]")
        
        if runner_type == "java":
            image_name, runner_label = build_java_runner(config["version"])
        else:  # flutter
            image_name, runner_label = build_flutter_runner(config["version"])
        
        if not image_name:
            console.print("[red]构建失败，程序退出[/]")
            return
        
        # 注册 Runner
        container_name = None
        if gitea_info:
            success, container_name = register_runner(image_name, runner_label, gitea_info)
            
            if success and container_name:
                # 显示使用指南
                show_usage_guide(runner_type, runner_label, image_name, container_name)
            else:
                console.print("[yellow]💡 你可以稍后手动注册：[/]")
                console.print(f"镜像：{image_name}")
                console.print(f"标签：{runner_label}")
        else:
            console.print("\n[bold green]✅ 镜像构建完成！[/]")
            console.print(f"镜像名称：{image_name}")
            console.print(f"Runner 标签：{runner_label}")
            console.print("\n[cyan]📝 后续手动注册命令：[/]")
            console.print(f"docker run -d \\")
            console.print(f"  --name gitea-runner \\")
            console.print(f"  --restart unless-stopped \\")
            console.print(f"  -e GITEA_INSTANCE_URL=\"你的Gitea地址\" \\")
            console.print(f"  -e GITEA_RUNNER_REGISTRATION_TOKEN=\"你的Token\" \\")
            console.print(f"  -e GITEA_RUNNER_LABELS=\"{runner_label}:docker://{image_name}\" \\")
            console.print(f"  -v /var/run/docker.sock:/var/run/docker.sock \\")
            console.print(f"  gitea/act_runner:latest")
        
        console.print("\n" + "="*50)
        console.print("[bold green]🎯 任务完成！[/]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]错误：{e}[/]")
        sys.exit(1)

if __name__ == "__main__":
    main()
