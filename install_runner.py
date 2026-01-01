#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Popular Runner 一键注册工具
全标签版 - 一个 Runner 支持所有热门镜像（ubuntu-latest + java-8/11/17 + flutter-stable）
修复版：镜像拉取失败不中断注册
"""
import os
import sys
import subprocess
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
    console.rule("[bold magenta]🚀 Gitea Runner 一键注册工具（全标签版）[/]")
   
    console.print(Panel.fit(
        "[bold cyan]一个 Runner 将支持以下 5 种编译环境：[/]\n\n"
        "• [green]ubuntu-latest[/] - catthehacker/ubuntu:act-latest (基础 Ubuntu 环境，兼容大多数 Actions)\n"
        "• [green]java-8[/]        - eclipse-temurin:8-jdk-jammy (预装纯净 JDK 8)\n"
        "• [green]java-11[/]       - eclipse-temurin:11-jdk-jammy (预装纯净 JDK 11)\n"
        "• [green]java-17[/]       - eclipse-temurin:17-jdk-jammy (预装纯净 JDK 17)\n"
        "• [green]flutter-stable[/] - ghcr.io/cirruslabs/flutter:stable (完整 Flutter + Android SDK)\n\n"
        "✅ [yellow]只需一个持久 Runner 容器[/]\n"
        "✅ [yellow]所有标签一次性注册，未使用标签无影响[/]\n"
        "✅ [yellow]预拉取镜像失败不会中断注册（job 执行时自动拉取）[/]\n"
        "✅ [yellow]持久化卷已启用，避免配置丢失[/]",
        title="功能说明", border_style="cyan"
    ))

def get_gitea_info():
    """获取 Gitea 基本信息"""
    console.print("\n" + "="*50)
    console.print("[bold yellow]📋 Gitea 配置信息[/]")
   
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
   
    runner_name = Prompt.ask("Runner 名称", default="multi-runner")
   
    return {
        "url": gitea_url,
        "token": token,
        "name": runner_name
    }

def pull_image(image_name):
    """拉取现成镜像（返回是否成功）"""
    console.print(f"[bold yellow]开始拉取镜像：{image_name}[/]")
   
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("拉取中...", total=None)
            run(f"docker pull {image_name}", capture=True)
            progress.update(task, completed=True)
       
        console.print(f"[bold green]✅ 镜像拉取成功！[/]")
       
        result = run(f"docker images {image_name} --format '{{{{.Size}}}}'", capture=True)
        if result.stdout:
            console.print(f"📏 镜像大小：{result.stdout.strip()}")
       
        return True
       
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ 拉取失败：{image_name}[/]")
        console.print(f"错误：{e.stderr[:500] if hasattr(e, 'stderr') and e.stderr else '未知错误'}")
        console.print("[yellow]此镜像将在首次 job 执行时自动拉取，无需担心。[/]")
        return False

def register_runner(gitea_info):
    """注册 Runner 到 Gitea（所有标签）"""
    console.print("\n" + "="*50)
    console.print("[bold yellow]📝 注册 Runner 到 Gitea[/]")
   
    container_name = "gitea-multi-runner"
    volume_name = "gitea-runner-data-multi"
   
    # 检查并清理同名容器
    result = run(f"docker ps -a --filter name=^{container_name}$ --format '{{{{.Names}}}}'", capture=True, check=False)
    if result.stdout.strip() == container_name:
        if Confirm.ask(f"已存在容器 '{container_name}'，是否删除并重新创建？", default=True):
            run(f"docker stop {container_name}", check=False)
            run(f"docker rm {container_name}", check=False)
        else:
            console.print("[yellow]跳过注册，使用现有容器[/]")
            return False, container_name
   
    # 所有标签（可在此处增删）
    labels = (
        "ubuntu-latest:docker://catthehacker/ubuntu:act-latest,"
        "java-8:docker://eclipse-temurin:8-jdk-jammy,"
        "java-11:docker://eclipse-temurin:11-jdk-jammy,"
        "java-17:docker://eclipse-temurin:17-jdk-jammy,"
        "flutter-stable:docker://ghcr.io/cirruslabs/flutter:stable"
    )
   
    # 创建持久化卷
    run(f"docker volume create {volume_name}", check=False)
   
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
  -v {volume_name}:/data \\
  gitea/act_runner:latest"""
   
    try:
        run(docker_cmd, capture=True)
        console.print(f"[bold green]✅ Runner 注册成功！[/]")
       
        console.print("\n[bold cyan]📊 Runner 信息：[/]")
        console.print(f"容器名称：{container_name}")
        console.print(f"持久化卷：{volume_name}")
        console.print("支持标签：ubuntu-latest, java-8, java-11, java-17, flutter-stable")
        console.print(f"Gitea URL：{gitea_info['url']}")
       
        return True, container_name
       
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Runner 注册失败！[/]")
        console.print(f"错误：{e.stderr[:500] if hasattr(e, 'stderr') and e.stderr else '未知错误'}")
        return False, container_name

def show_usage_guide(container_name, failed_images):
    """显示使用指南"""
    console.print("\n" + "="*50)
   
    console.print(Panel.fit(
        f"[bold green]🎉 多标签 Runner 就绪！[/]\n\n"
        f"支持标签：ubuntu-latest / java-8 / java-11 / java-17 / flutter-stable\n"
        f"📁 容器：{container_name}",
        title="注册完成", border_style="green"
    ))
   
    if failed_images:
        console.print("\n[bold yellow]💡 以下镜像预拉取失败（不影响 Runner 使用）：[/]")
        for img in failed_images:
            console.print(f"[yellow]• {img}[/]")
        console.print("\n[bold cyan]建议手动拉取命令（网络恢复后执行）：[/]")
        for img in failed_images:
            console.print(f"docker pull {img}")
        console.print("\n[yellow]首次使用对应标签的 workflow 时，Runner 会自动拉取这些镜像。[/]")
   
    console.print("\n[bold cyan]📝 示例 workflow（根据项目选择 runs-on）：[/]")
    console.print("[bold yellow]# 通用 / Node / Python 等项目[/]")
    console.print("""name: General CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "运行在基础 Ubuntu 环境中"[/]""")
   
    console.print("\n[bold yellow]# Java 8 项目（JDK 8 已预装）[/]")
    console.print("""name: Java 8 CI
on: [push]
jobs:
  build:
    runs-on: java-8
    steps:
      - uses: actions/checkout@v4
      - run: mvn clean package
      - run: java -version[/]""")
   
    console.print("\n[bold yellow]# Java 11 项目（JDK 11 已预装）[/]")
    console.print("""name: Java 11 CI
on: [push]
jobs:
  build:
    runs-on: java-11
    steps:
      - uses: actions/checkout@v4
      - run: mvn clean package
      - run: java -version[/]""")
   
    console.print("\n[bold yellow]# Java 17 项目（JDK 17 已预装）[/]")
    console.print("""name: Java 17 CI
on: [push]
jobs:
  build:
    runs-on: java-17
    steps:
      - uses: actions/checkout@v4
      - run: mvn clean package
      - run: java -jar target/*.jar --version[/]""")
   
    console.print("\n[bold yellow]# Flutter 项目[/]")
    console.print("""name: Flutter Build
on: [push]
jobs:
  build-android:
    runs-on: flutter-stable
    steps:
      - uses: actions/checkout@v4
      - run: flutter pub get
      - run: flutter build apk --release[/]""")
   
    console.print("\n[bold cyan]🔧 管理命令：[/]")
    console.print(f"查看日志：docker logs -f {container_name}")
    console.print(f"重启：docker restart {container_name}")
    console.print(f"停止/删除：docker stop {container_name} && docker rm {container_name}")
    console.print("删除卷：docker volume rm gitea-runner-data-multi")  # 直接硬编码，避免变量错误
    console.print(f"查看 Runner：docker ps --filter name=gitea-multi-runner")
   
    console.print("\n[yellow]提示：若需调整标签，重新运行脚本或手动修改 GITEA_RUNNER_LABELS。[/]")

def main():
    """主函数"""
    try:
        check_root()
        show_menu()
       
        if not Confirm.ask("\n确认注册所有标签的 Runner？（支持 5 种编译环境）", default=True):
            console.print("[yellow]已取消[/]")
            return
       
        gitea_info = get_gitea_info()
       
        console.print("\n" + "="*50)
        console.print("[bold cyan]开始尝试预拉取所有镜像（失败不影响注册）...[/]")
       
        images = [
            "catthehacker/ubuntu:act-latest",
            "eclipse-temurin:8-jdk-jammy",
            "eclipse-temurin:11-jdk-jammy",
            "eclipse-temurin:17-jdk-jammy",
            "ghcr.io/cirruslabs/flutter:stable"
        ]
       
        failed_images = []
        for img in images:
            if not pull_image(img):
                failed_images.append(img)
       
        success, container_name = register_runner(gitea_info)
       
        if success:
            show_usage_guide(container_name, failed_images)
        else:
            console.print("[yellow]💡 可手动注册（若有失败镜像，请先手动拉取）：[/]")
            # （手动命令保持不变，包含新 Flutter 镜像）
       
        console.print("\n" + "="*50)
        console.print("[bold green]🎯 任务完成！[/]")
        console.print("[cyan]如有问题，欢迎随时反馈。[/]")
       
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]错误：{e}[/]")
        sys.exit(1)

if __name__ == "__main__":
    main()