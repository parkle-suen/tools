#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Popular Runner 管理工具 - 模块化增强版
支持独立执行各个功能模块
"""
import os
import sys
import subprocess
import tempfile
try:
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("\033[93m正在安装 rich...\033[0m")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

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

def show_main_menu():
    """显示主菜单"""
    console.clear()
    console.rule("[bold magenta]🚀 Gitea Runner 管理工具 - 模块化增强版[/]")
    
    console.print(Panel.fit(
        "[bold cyan]📋 主要功能模块：[/]\n\n"
        "1. [green]重新完全安装注册 Runner[/] - 完整流程（包含下载和构建所有镜像）\n"
        "2. [green]仅编译安装 Flutter 增强版镜像[/] - 构建包含完整工具链的 Flutter 镜像\n"
        "3. [green]仅下载 JDK 多个版本镜像[/] - 拉取 JDK 8/11/17/21 镜像\n"
        "4. [green]仅下载 Ubuntu-Latest 镜像[/] - 拉取基础 Ubuntu 环境镜像\n"
        "5. [green]仅注册 Runner（不下载镜像）[/] - 快速注册 Runner 容器\n"
        "6. [green]管理现有 Runner[/] - 查看、重启、删除 Runner\n"
        "7. [green]退出[/]\n\n"
        "[yellow]💡 提示：您可以选择单独执行某个模块，避免重复操作[/]",
        title="功能菜单", border_style="cyan"
    ))
    
    while True:
        choice = IntPrompt.ask("请选择功能编号", default=1, choices=["1", "2", "3", "4", "5", "6", "7"])
        if 1 <= choice <= 7:
            return choice
        console.print("[red]无效的选择，请重新输入[/]")

# ==================== 模块 1: 完整安装注册 ====================
def module_complete_installation():
    """模块1：重新完全安装注册Runner（包含下载镜像）"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🔧 模块1：重新完全安装注册 Runner[/]")
    
    # 获取 Gitea 信息
    gitea_info = get_gitea_info()
    
    # 预拉取所有基础镜像
    console.print("\n[bold cyan]📥 开始预拉取所有基础镜像...[/]")
    
    all_images = [
        ("基础 Ubuntu 环境", "catthehacker/ubuntu:act-latest"),
        ("JDK 8", "eclipse-temurin:8-jdk-jammy"),
        ("JDK 11", "eclipse-temurin:11-jdk-jammy"),
        ("JDK 17", "eclipse-temurin:17-jdk-jammy"),
        ("JDK 21", "eclipse-temurin:21-jdk-jammy"),
    ]
    
    # 如果用户选择构建增强版 Flutter 镜像，则不预拉取原始镜像
    flutter_config = gitea_info.get('enhanced_config', {})
    if not flutter_config.get('enabled', False):
        flutter_tag = "stable" if gitea_info['flutter_version'] in ['latest', 'stable'] else gitea_info['flutter_version']
        all_images.append(("Flutter 基础镜像", f"ghcr.io/cirruslabs/flutter:{flutter_tag}"))
    
    failed_images = []
    for name, image in all_images:
        console.print(f"\n[yellow]正在拉取: {name}[/]")
        if not pull_single_image(image, name):
            failed_images.append((name, image))
    
    # 构建或处理 Flutter 镜像
    flutter_image = handle_flutter_image(gitea_info)
    
    # 注册 Runner
    success, container_name, flutter_label, _ = register_runner(gitea_info, flutter_image)
    
    if success:
        show_runner_summary(container_name, gitea_info['name'], flutter_label, failed_images)
    else:
        console.print("[bold red]❌ Runner 注册失败，请检查错误信息[/]")
    
    return success

# ==================== 模块 2: 仅编译 Flutter 镜像 ====================
def module_build_flutter_only():
    """模块2：仅编译安装Flutter增强版镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🔨 模块2：仅编译安装 Flutter 增强版镜像[/]")
    
    # 获取 Flutter 版本
    console.print("\n[bold yellow]Flutter 版本配置：[/]")
    flutter_version = Prompt.ask(
        "输入 Flutter 版本（如 3.35.7，或输入 stable/latest）",
        default="stable"
    ).strip().lower()
    
    if flutter_version in ['latest', 'stable']:
        flutter_tag = "stable"
    else:
        flutter_tag = flutter_version
    
    base_image = f"ghcr.io/cirruslabs/flutter:{flutter_tag}"
    
    # 配置增强版选项
    console.print("\n[bold yellow]🛠️ 增强版镜像配置：[/]")
    console.print("[cyan]原始 ghcr.io/cirruslabs/flutter 镜像缺少 Python 和 Node.js 工具[/]")
    build_enhanced = Confirm.ask("是否构建增强版 Flutter 镜像？", default=True)
    
    if not build_enhanced:
        console.print("[yellow]取消构建，返回主菜单[/]")
        return
    
    # 配置包选项
    console.print("\n[bold yellow]📦 增强版镜像配置：[/]")
    include_all = Confirm.ask("安装所有推荐的 Python 包和工具？", default=True)
    
    if not include_all:
        console.print("[cyan]选择 Python 包：[/]")
        include_requests = Confirm.ask("安装 requests 包？", default=True)
        include_semver = Confirm.ask("安装 semver 包？", default=True)
        include_yaml = Confirm.ask("安装 PyYAML 包？", default=True)
        include_jsonschema = Confirm.ask("安装 jsonschema 包？", default=True)
        include_docker = Confirm.ask("安装 Docker Python SDK？", default=True)
    else:
        include_requests = include_semver = include_yaml = include_jsonschema = include_docker = True
    
    # 构建配置
    extra_packages = []
    if include_requests: extra_packages.append("requests")
    if include_semver: extra_packages.append("semver")
    if include_yaml: extra_packages.append("pyyaml")
    if include_jsonschema: extra_packages.append("jsonschema")
    if include_docker: extra_packages.append("docker")
    
    enhanced_config = {
        "enabled": True,
        "extra_packages": extra_packages,
        "install_all": include_all
    }
    
    # 拉取基础镜像
    console.print(f"\n[cyan]首先拉取基础镜像: {base_image}[/]")
    if not pull_single_image(base_image, "Flutter 基础镜像"):
        console.print("[red]基础镜像拉取失败，无法继续构建[/]")
        return
    
    # 构建增强版镜像
    enhanced_image = build_enhanced_flutter_image(base_image, flutter_tag, enhanced_config)
    
    if enhanced_image and enhanced_image != base_image:
        console.print(f"\n[bold green]✅ Flutter 增强版镜像构建完成！[/]")
        console.print(f"[cyan]镜像标签: {enhanced_image}[/]")
        console.print(f"[cyan]镜像大小: ", end="")
        result = run(f"docker images {enhanced_image} --format '{{{{.Size}}}}'", capture=True)
        if result.stdout:
            console.print(result.stdout.strip())
        
        # 显示使用说明
        show_flutter_image_usage(enhanced_image, flutter_tag, extra_packages)

# ==================== 模块 3: 仅下载 JDK 镜像 ====================
def module_download_jdk_only():
    """模块3：仅下载JDK多个版本镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块3：仅下载 JDK 多个版本镜像[/]")
    
    jdk_images = [
        ("JDK 8 (Java 8)", "eclipse-temurin:8-jdk-jammy"),
        ("JDK 11 (Java 11)", "eclipse-temurin:11-jdk-jammy"),
        ("JDK 17 (Java 17)", "eclipse-temurin:17-jdk-jammy"),
        ("JDK 21 (Java 21)", "eclipse-temurin:21-jdk-jammy"),
    ]
    
    # 让用户选择要下载的版本
    console.print("\n[bold yellow]选择要下载的 JDK 版本：[/]")
    table = Table(title="JDK 镜像列表")
    table.add_column("编号", style="cyan")
    table.add_column("JDK 版本", style="green")
    table.add_column("镜像标签", style="yellow")
    
    for i, (name, image) in enumerate(jdk_images, 1):
        table.add_row(str(i), name, image)
    
    console.print(table)
    
    console.print("\n[cyan]输入要下载的编号（多个用逗号分隔，或输入 all 下载全部）：[/]")
    choice_input = Prompt.ask("选择", default="all").strip()
    
    if choice_input.lower() == 'all':
        selected = list(range(1, len(jdk_images) + 1))
    else:
        selected = []
        for part in choice_input.split(','):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(jdk_images):
                selected.append(int(part))
    
    if not selected:
        console.print("[red]未选择任何镜像，取消操作[/]")
        return
    
    # 下载选中的镜像
    failed = []
    for idx in selected:
        name, image = jdk_images[idx-1]
        console.print(f"\n[yellow]正在下载: {name}[/]")
        if not pull_single_image(image, name):
            failed.append((name, image))
    
    # 显示结果
    console.print("\n" + "="*50)
    if failed:
        console.print(f"[yellow]部分镜像下载失败 ({len(failed)}/{len(selected)})[/]")
        for name, image in failed:
            console.print(f"[red]❌ {name}: {image}[/]")
    else:
        console.print("[bold green]✅ 所有选中镜像下载完成！[/]")
    
    # 显示已下载的镜像
    console.print("\n[bold cyan]📋 已下载的 JDK 镜像：[/]")
    result = run("docker images eclipse-temurin* --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'", capture=True)
    if result.stdout:
        console.print(result.stdout)
    else:
        console.print("[yellow]未找到 eclipse-temurin 镜像[/]")

# ==================== 模块 4: 仅下载 Ubuntu 镜像 ====================
def module_download_ubuntu_only():
    """模块4：仅下载Ubuntu-Latest镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块4：仅下载 Ubuntu-Latest 镜像[/]")
    
    ubuntu_image = "catthehacker/ubuntu:act-latest"
    
    console.print(f"\n[cyan]准备下载镜像: {ubuntu_image}[/]")
    console.print("[yellow]这个镜像包含：[/]")
    console.print("• 完整的 Ubuntu 基础环境")
    console.print("• 预装了常用的开发工具")
    console.print("• 兼容大多数 GitHub Actions")
    
    if not Confirm.ask("\n确认下载此镜像？", default=True):
        console.print("[yellow]取消下载[/]")
        return
    
    success = pull_single_image(ubuntu_image, "Ubuntu-Latest 基础环境")
    
    if success:
        console.print("\n[bold green]✅ 镜像下载完成！[/]")
        console.print("[cyan]镜像信息：[/]")
        result = run(f"docker images {ubuntu_image} --format 'table {{.Repository}}:{{.Tag}}\\t{{.Size}}\\t{{.CreatedAt}}'", capture=True)
        if result.stdout:
            console.print(result.stdout)

# ==================== 模块 5: 仅注册 Runner ====================
def module_register_runner_only():
    """模块5：仅注册Runner（不下载镜像）"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🚀 模块5：仅注册 Runner（快速模式）[/]")
    
    console.print("[yellow]⚠️  注意：此模式假设所需镜像已存在本地[/]")
    console.print("[yellow]如果镜像不存在，job 执行时会自动拉取，但首次运行会较慢[/]")
    
    # 获取 Gitea 信息
    gitea_info = get_gitea_info()
    
    # 处理 Flutter 镜像
    flutter_image = handle_flutter_image(gitea_info)
    
    # 直接注册 Runner
    success, container_name, flutter_label, _ = register_runner(gitea_info, flutter_image)
    
    if success:
        console.print("\n[bold green]✅ Runner 注册成功！[/]")
        console.print(f"[cyan]容器名称: {container_name}[/]")
        console.print(f"[cyan]支持标签: ubuntu-latest, java-8/11/17/21, {flutter_label}[/]")
        
        # 显示管理命令
        show_runner_management_commands(container_name, gitea_info['name'])
    else:
        console.print("[bold red]❌ Runner 注册失败[/]")

# ==================== 模块 6: 管理现有 Runner ====================
def module_manage_runners():
    """模块6：管理现有Runner"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🔧 模块6：管理现有 Runner[/]")
    
    # 获取所有 Gitea Runner 容器
    result = run("docker ps -a --filter name=gitea- --format '{{.Names}}'", capture=True, check=False)
    
    containers = [c.strip() for c in result.stdout.splitlines() if c.strip()]
    
    if not containers:
        console.print("[yellow]未找到任何 Gitea Runner 容器[/]")
        return
    
    # 显示容器列表
    console.print("\n[bold cyan]📋 找到的 Runner 容器：[/]")
    table = Table(title="Runner 容器列表")
    table.add_column("编号", style="cyan")
    table.add_column("容器名称", style="green")
    table.add_column("状态", style="yellow")
    
    for i, container in enumerate(containers, 1):
        status_result = run(f"docker inspect -f '{{{{.State.Status}}}}' {container}", capture=True, check=False)
        status = status_result.stdout.strip() if status_result.stdout else "未知"
        table.add_row(str(i), container, status)
    
    console.print(table)
    
    # 选择要管理的容器
    console.print("\n[cyan]输入要管理的容器编号（或输入 0 返回）：[/]")
    choice = IntPrompt.ask("选择", default=0, choices=[str(i) for i in range(len(containers) + 1)])
    
    if choice == 0:
        return
    
    if choice < 1 or choice > len(containers):
        console.print("[red]无效的选择[/]")
        return
    
    selected_container = containers[choice - 1]
    
    # 管理选项
    console.print(f"\n[bold yellow]管理容器: {selected_container}[/]")
    console.print("1. 查看日志")
    console.print("2. 重启容器")
    console.print("3. 停止容器")
    console.print("4. 删除容器")
    console.print("5. 进入容器终端")
    console.print("6. 查看容器信息")
    console.print("7. 返回")
    
    action = IntPrompt.ask("选择操作", default=1, choices=["1", "2", "3", "4", "5", "6", "7"])
    
    if action == 1:  # 查看日志
        console.print(f"[cyan]正在显示 {selected_container} 的日志（Ctrl+C 退出）...[/]")
        try:
            run(f"docker logs -f {selected_container}")
        except KeyboardInterrupt:
            console.print("\n[yellow]日志查看已停止[/]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]错误: {e}[/]")
    
    elif action == 2:  # 重启容器
        console.print(f"[yellow]正在重启 {selected_container}...[/]")
        run(f"docker restart {selected_container}")
        console.print("[green]✅ 容器已重启[/]")
    
    elif action == 3:  # 停止容器
        if Confirm.ask(f"确认停止容器 {selected_container}？", default=False):
            run(f"docker stop {selected_container}")
            console.print("[green]✅ 容器已停止[/]")
    
    elif action == 4:  # 删除容器
        if Confirm.ask(f"确认删除容器 {selected_container}？", default=False):
            # 获取关联的卷
            volume_result = run(f"docker inspect {selected_container} --format '{{{{range .Mounts}}}}{{{{if eq .Type \"volume\"}}}}{{{{.Name}}}}{{{{end}}}}{{{{end}}}}'", 
                               capture=True, check=False)
            volume_name = volume_result.stdout.strip()
            
            run(f"docker rm -f {selected_container}")
            console.print("[green]✅ 容器已删除[/]")
            
            if volume_name:
                if Confirm.ask(f"是否同时删除关联的卷 {volume_name}？", default=True):
                    run(f"docker volume rm {volume_name}", check=False)
                    console.print(f"[green]✅ 卷 {volume_name} 已删除[/]")
    
    elif action == 5:  # 进入容器终端
        console.print(f"[cyan]正在进入 {selected_container} 的终端（输入 exit 退出）...[/]")
        try:
            run(f"docker exec -it {selected_container} /bin/bash")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]错误: {e}[/]")
    
    elif action == 6:  # 查看容器信息
        console.print(f"\n[bold cyan]容器 {selected_container} 的信息：[/]")
        run(f"docker inspect {selected_container} --format '\
状态: {{.State.Status}}\n\
创建时间: {{.Created}}\n\
镜像: {{.Config.Image}}\n\
网络模式: {{.HostConfig.NetworkMode}}\n\
重启策略: {{.HostConfig.RestartPolicy.Name}}\n'", check=False)
        
        # 显示环境变量
        console.print("\n[cyan]环境变量：[/]")
        run(f"docker inspect {selected_container} --format '{{{{range .Config.Env}}}}{{{{.}}}}\n{{{{end}}}}'", check=False)

# ==================== 公共函数（从原脚本提取） ====================
def get_gitea_info():
    """获取 Gitea 基本信息"""
    console.print("\n[bold yellow]📋 Gitea 配置信息[/]")
    
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
    
    token = Prompt.ask("粘贴 Registration Token", default="oRyijO9he0A7cNWU6YT4YiDGemOljPn64ynMkMTq")
    
    runner_name = Prompt.ask("Runner 名称", default="my-runner")
    
    console.print("\n[bold yellow]Flutter 版本配置：[/]")
    console.print("[cyan]输入版本号（如 3.35.7），默认 3.35.7（稳定推荐）[/]")
    console.print("[cyan]输入 'stable' 或 'latest' 使用最新稳定版[/]")
    flutter_version = Prompt.ask("Flutter 版本", default="3.35.7").strip().lower()
    
    # 询问是否构建增强版镜像
    console.print("\n[bold yellow]🛠️  Flutter 镜像增强选项：[/]")
    console.print("[cyan]原始镜像缺少 Python 和 Node.js 工具，建议构建增强版[/]")
    build_enhanced = Confirm.ask("是否构建增强版 Flutter 镜像？", default=True)
    
    if build_enhanced:
        console.print("\n[bold yellow]📦 增强版镜像配置：[/]")
        include_all = Confirm.ask("安装所有推荐的 Python 包和工具？", default=True)
        
        if not include_all:
            console.print("[cyan]选择 Python 包：[/]")
            include_requests = Confirm.ask("安装 requests 包？", default=True)
            include_semver = Confirm.ask("安装 semver 包？", default=True)
            include_yaml = Confirm.ask("安装 PyYAML 包？", default=True)
            include_jsonschema = Confirm.ask("安装 jsonschema 包？", default=True)
        else:
            include_requests = include_semver = include_yaml = include_jsonschema = True
            
        extra_packages = []
        if include_requests: extra_packages.append("requests")
        if include_semver: extra_packages.append("semver")
        if include_yaml: extra_packages.append("pyyaml")
        if include_jsonschema: extra_packages.append("jsonschema")
        
        enhanced_config = {
            "enabled": True,
            "extra_packages": extra_packages,
            "install_all": include_all
        }
    else:
        enhanced_config = {"enabled": False}
    
    return {
        "url": gitea_url,
        "token": token,
        "name": runner_name,
        "flutter_version": flutter_version,
        "enhanced_config": enhanced_config
    }

def pull_single_image(image_name, display_name=None):
    """拉取单个镜像"""
    name = display_name or image_name
    console.print(f"[yellow]拉取: {name} ({image_name})[/]")
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("拉取中...", total=None)
            run(f"docker pull {image_name}", capture=True)
            progress.update(task, completed=True)
        
        console.print(f"[green]✅ {name} 拉取成功[/]")
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ {name} 拉取失败[/]")
        console.print(f"[yellow]错误: {e.stderr[:200] if hasattr(e, 'stderr') and e.stderr else '未知错误'}[/]")
        return False

def build_enhanced_flutter_image(base_image: str, version_tag: str, config: dict) -> str:
    """构建增强版 Flutter 镜像"""
    console.print(f"\n[bold yellow]🔨 开始构建增强版 Flutter 镜像[/]")
    console.print(f"[cyan]基础镜像: {base_image}[/]")
    
    # 创建临时 Dockerfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.Dockerfile', delete=False) as f:
        dockerfile_content = f"""FROM {base_image}

# 设置非交互式安装环境
ENV DEBIAN_FRONTEND=noninteractive

# 更新包列表并安装基础工具
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    git \\
    unzip \\
    zip \\
    sudo \\
    ca-certificates \\
    software-properties-common \\
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 3 和 pip
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    && ln -sf /usr/bin/python3 /usr/bin/python \\
    && python3 -m pip install --upgrade pip setuptools wheel

# 安装 Node.js (最新 LTS 版本)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \\
    && apt-get install -y nodejs \\
    && npm install -g npm@latest

# 清理缓存
RUN apt-get autoremove -y && apt-get clean
"""
        
        # 添加 Python 包安装
        if config.get("install_all", True):
            dockerfile_content += """RUN pip3 install --no-cache-dir \\
    requests \\
    semver \\
    pyyaml \\
    jsonschema \\
    python-dateutil \\
    pytz \\
    colorama \\
    tqdm \\
    docker
"""
        elif config.get("extra_packages"):
            packages = " \\\n    ".join(config["extra_packages"])
            dockerfile_content += f"RUN pip3 install --no-cache-dir \\\n    {packages}\n"
        
        # 添加环境变量和验证
        dockerfile_content += """
# 设置环境变量
ENV PATH="/flutter/bin:/flutter/bin/cache/dart-sdk/bin:$PATH"
ENV FLUTTER_ROOT="/flutter"
ENV PUB_CACHE="/flutter/.pub-cache"

# 验证安装
RUN python3 --version && pip3 --version && node --version && npm --version
RUN flutter --version && dart --version

# 设置工作目录
WORKDIR /workspace
"""
        
        f.write(dockerfile_content)
        dockerfile_path = f.name
    
    enhanced_image = f"local/flutter-enhanced:{version_tag}"
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("构建镜像中...", total=None)
            
            # 构建镜像
            build_cmd = f"docker build -f {dockerfile_path} -t {enhanced_image} ."
            result = run(build_cmd, capture=True)
            
            progress.update(task, completed=True)
        
        console.print(f"[bold green]✅ 增强版镜像构建成功！[/]")
        return enhanced_image
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ 镜像构建失败！[/]")
        console.print(f"[red]错误信息：{e.stderr[:500] if hasattr(e, 'stderr') and e.stderr else '未知错误'}[/]")
        console.print("[yellow]将使用原始镜像[/]")
        return base_image
    finally:
        # 清理临时文件
        if os.path.exists(dockerfile_path):
            os.unlink(dockerfile_path)

def handle_flutter_image(gitea_info):
    """处理 Flutter 镜像（构建或使用原始镜像）"""
    flutter_input = gitea_info['flutter_version']
    if flutter_input in ['latest', 'stable']:
        flutter_tag = "stable"
    else:
        flutter_tag = flutter_input
    
    base_flutter_image = f"ghcr.io/cirruslabs/flutter:{flutter_tag}"
    
    if gitea_info['enhanced_config']['enabled']:
        # 构建增强版镜像
        enhanced_image = build_enhanced_flutter_image(
            base_flutter_image, 
            flutter_tag,
            gitea_info['enhanced_config']
        )
        return enhanced_image
    else:
        return base_flutter_image

def register_runner(gitea_info, flutter_image):
    """注册 Runner 到 Gitea"""
    runner_name = gitea_info['name']
    container_name = f"gitea-{runner_name}"
    volume_name = f"gitea-runner-data-{runner_name}"
    
    # 检查并清理同名容器
    result = run(f"docker ps -a --filter name=^{container_name}$ --format '{{{{.Names}}}}'", capture=True, check=False)
    if result.stdout.strip() == container_name:
        if Confirm.ask(f"已存在容器 '{container_name}'，是否删除并重新创建？", default=True):
            run(f"docker stop {container_name}", check=False)
            run(f"docker rm {container_name}", check=False)
        else:
            console.print("[yellow]跳过注册，使用现有容器[/]")
            return False, container_name, None, None
    
    # Flutter 标签处理
    flutter_input = gitea_info['flutter_version']
    if flutter_input in ['latest', 'stable']:
        flutter_label = "flutter-stable"
    else:
        flutter_label = f"flutter-{flutter_input}"
    
    flutter_label_entry = f"{flutter_label}:docker://{flutter_image}"
    
    # 所有标签
    labels = (
        "ubuntu-latest:docker://catthehacker/ubuntu:act-latest,"
        "java-8:docker://eclipse-temurin:8-jdk-jammy,"
        "java-11:docker://eclipse-temurin:11-jdk-jammy,"
        "java-17:docker://eclipse-temurin:17-jdk-jammy,"
        "java-21:docker://eclipse-temurin:21-jdk-jammy,"
        f"{flutter_label_entry}"
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
        return True, container_name, flutter_label, flutter_image
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Runner 注册失败！[/]")
        console.print(f"错误：{e.stderr[:500] if hasattr(e, 'stderr') and e.stderr else '未知错误'}")
        return False, container_name, flutter_label, flutter_image

def show_runner_summary(container_name, runner_name, flutter_label, failed_images):
    """显示 Runner 安装摘要"""
    console.print("\n" + "="*50)
    console.print(Panel.fit(
        f"[bold green]🎉 Runner 安装完成！[/]\n\n"
        f"容器名称: [cyan]{container_name}[/]\n"
        f"持久化卷: [cyan]gitea-runner-data-{runner_name}[/]\n"
        f"支持标签: [yellow]ubuntu-latest, java-8/11/17/21, {flutter_label}[/]",
        title="安装成功", border_style="green"
    ))
    
    if failed_images:
        console.print("\n[yellow]💡 以下镜像拉取失败（首次使用时自动拉取）：[/]")
        for name, image in failed_images:
            console.print(f"[yellow]• {name}: {image}[/]")
    
    show_runner_management_commands(container_name, runner_name)

def show_runner_management_commands(container_name, runner_name):
    """显示 Runner 管理命令"""
    console.print("\n[bold cyan]🔧 管理命令：[/]")
    console.print(f"查看日志: [green]docker logs -f {container_name}[/]")
    console.print(f"重启: [green]docker restart {container_name}[/]")
    console.print(f"停止: [green]docker stop {container_name}[/]")
    console.print(f"删除容器: [green]docker rm -f {container_name}[/]")
    console.print(f"删除卷: [green]docker volume rm gitea-runner-data-{runner_name}[/]")
    console.print(f"查看状态: [green]docker ps --filter name={container_name}[/]")

def show_flutter_image_usage(image_name, version_tag, packages):
    """显示 Flutter 镜像使用说明"""
    console.print("\n[bold cyan]📝 Flutter 增强版镜像使用说明：[/]")
    console.print(f"1. 镜像标签: [green]{image_name}[/]")
    console.print(f"2. Flutter 版本: [green]{version_tag}[/]")
    console.print(f"3. 预装工具: Python3, pip, Node.js, npm, npx")
    if packages:
        console.print(f"4. 预装 Python 包: {', '.join(packages)}")
    
    console.print("\n[bold yellow]在 Gitea workflow 中使用：[/]")
    console.print(f"""```yaml
jobs:
  build:
    runs-on: flutter-{version_tag}
    steps:
      - uses: actions/checkout@v4
      - name: Check tools
        run: |
          python3 --version
          pip3 --version  
          node --version
          flutter --version
      - name: Build project
        run: flutter build apk --release
```""")

# ==================== 主程序 ====================
def main():
    """主函数"""
    try:
        check_root()
        
        while True:
            choice = show_main_menu()
            
            if choice == 1:
                # 模块1: 重新完全安装注册Runner
                module_complete_installation()
                
            elif choice == 2:
                # 模块2: 仅编译安装Flutter镜像
                module_build_flutter_only()
                
            elif choice == 3:
                # 模块3: 仅下载JDK多个版本镜像
                module_download_jdk_only()
                
            elif choice == 4:
                # 模块4: 仅下载Ubuntu-Latest镜像
                module_download_ubuntu_only()
                
            elif choice == 5:
                # 模块5: 仅注册Runner（不下载镜像）
                module_register_runner_only()
                
            elif choice == 6:
                # 模块6: 管理现有Runner
                module_manage_runners()
                
            elif choice == 7:
                # 退出
                console.print("\n[bold green]👋 感谢使用，再见！[/]")
                break
            
            # 询问是否继续
            if choice != 7:
                console.print("\n" + "="*50)
                if not Confirm.ask("是否返回主菜单？", default=True):
                    console.print("\n[bold green]👋 感谢使用，再见！[/]")
                    break
    
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/]")
    except Exception as e:
        console.print(f"[bold red]错误：{e}[/]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
