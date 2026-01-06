#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gitea Popular Runner 管理工具 - 优化增强版
支持多版本批量下载和灵活配置，包含 Amazon Corretto JDK
"""

import os
import sys
import subprocess
import tempfile
import re
from typing import List, Dict, Any, Tuple

# 尝试导入 rich 库，如果不存在则自动安装
try:
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.markdown import Markdown
except ImportError:
    print("\033[93m正在安装 rich...\033[0m")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.markdown import Markdown

console = Console()

# ==================== 全局配置 ====================
DEFAULT_JAVA_VERSIONS = ["8", "11", "17", "21", "25"]
DEFAULT_FLUTTER_VERSIONS = ["3.35.7", "latest"]
DEFAULT_UBUNTU_INSTALL = True

# ==================== 工具函数 ====================
def run(cmd: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """运行命令"""
    kwargs = {"shell": True, "check": check, "text": True}
    if capture:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs)

def check_root() -> None:
    """检查是否为 root 权限"""
    if os.geteuid() != 0:
        console.print("[bold red]请使用 sudo 运行此脚本[/]")
        sys.exit(1)

def parse_multi_version_input(input_str: str, default_versions: List[str]) -> List[str]:
    """
    解析多版本输入字符串
    支持空格、逗号、分号分隔
    """
    if not input_str.strip():
        return default_versions
    
    # 替换所有分隔符为逗号
    normalized = re.sub(r'[ ,;]+', ',', input_str.strip())
    
    # 分割版本
    versions = []
    for version in normalized.split(','):
        version = version.strip().lower()
        if version and version != 'skip':
            versions.append(version)
    
    return versions if versions else default_versions

def validate_flutter_version(version: str) -> str:
    """验证并标准化 Flutter 版本"""
    if version.lower() in ['latest', 'stable']:
        return 'stable'
    # 简单验证版本格式
    if re.match(r'^\d+(\.\d+)*$', version):
        return version
    return version  # 如果不是标准格式，也允许尝试

def validate_java_version(version: str) -> str:
    """验证 Java 版本"""
    try:
        v = int(version)
        if v >= 8 and v <= 25:  # 合理的 Java 版本范围
            return str(v)
    except ValueError:
        pass
    return version  # 如果不是数字，允许用户尝试

def pull_single_image(image_name: str, display_name: str = None) -> bool:
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

def get_gitea_info() -> Dict[str, Any]:
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
    
    return {
        "url": gitea_url,
        "token": token,
        "name": runner_name
    }

def show_main_menu() -> int:
    """显示主菜单"""
    console.clear()
    console.rule("[bold magenta]🚀 Gitea Runner 管理工具 - 优化增强版[/]")
    
    console.print(Panel.fit(
        "[bold cyan]📋 主要功能模块：[/]\n\n"
        "1. [green]重新完全安装注册 Runner[/] - 完整流程（[red]注意删除旧Runner容器的持久卷[/]）\n"
        "2. [green]仅下载多个 Flutter 版本镜像[/] - 拉取指定版本的 Flutter 镜像\n"
        "3. [green]仅下载多个 Temurin JDK 版本镜像[/] - 拉取指定版本的 Eclipse Temurin JDK 镜像\n"
        "4. [green]仅下载多个 Amazon Corretto JDK 版本镜像[/] - 拉取指定版本的 AWS Amazon Corretto JDK 镜像\n"
        "5. [green]仅下载 Ubuntu-Latest 工具镜像[/] - 拉取包含完整工具链的 Ubuntu 镜像\n"
        "6. [green]仅注册 Runner（不下载镜像）[/] - 快速注册 Runner 容器\n"
        "7. [green]管理现有 Runner[/] - 查看、重启、删除 Runner\n"
        "8. [green]退出[/]\n\n"
        "[yellow]💡 提示：支持批量下载，输入多个版本时用空格、逗号或分号分隔[/]",
        title="功能菜单", border_style="cyan"
    ))
    
    while True:
        try:
            choice = IntPrompt.ask("请选择功能编号", default=1, choices=["1", "2", "3", "4", "5", "6", "7", "8"])
            if 1 <= choice <= 8:
                return choice
        except:
            pass
        console.print("[red]无效的选择，请重新输入[/]")

# ==================== 模块 1: 完整安装注册 ====================
def module_complete_installation() -> bool:
    """模块1：重新完全安装注册Runner（包含下载镜像）"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🔧 模块1：重新完全安装注册 Runner[/]")
    
    # 获取 Gitea 信息
    gitea_info = get_gitea_info()
    
    console.print("\n[bold yellow]📦 配置要下载的 Java 版本 (Eclipse Temurin)[/]")
    console.print("[cyan]请输入要下载的 Java 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]输入 'skip' 跳过 Temurin JDK 安装[/]")
    console.print(f"[cyan]默认版本: {', '.join(DEFAULT_JAVA_VERSIONS)}[/]")
    java_input = Prompt.ask("Temurin JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    
    if java_input.strip().lower() == 'skip':
        temurin_versions = []
        console.print("[yellow]已跳过 Temurin JDK 安装[/]")
    else:
        temurin_versions = parse_multi_version_input(java_input, DEFAULT_JAVA_VERSIONS)
    
    console.print("\n[bold yellow]📦 配置要下载的 Java 版本 (Amazon Corretto)[/]")
    console.print("[cyan]请输入要下载的 AWS Amazon Corretto 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]💡 Amazon Corretto 是 AWS 优化的 OpenJDK 发行版，在 AWS 环境性能更佳[/]")
    console.print("[cyan]输入 'skip' 跳过 Amazon Corretto JDK 安装[/]")
    console.print(f"[cyan]默认版本: {', '.join(DEFAULT_JAVA_VERSIONS)}[/]")
    aws_java_input = Prompt.ask("Amazon Corretto JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    
    if aws_java_input.strip().lower() == 'skip':
        aws_java_versions = []
        console.print("[yellow]已跳过 Amazon Corretto JDK 安装[/]")
    else:
        aws_java_versions = parse_multi_version_input(aws_java_input, DEFAULT_JAVA_VERSIONS)
    
    console.print("\n[bold yellow]📦 配置要下载的 Flutter 版本[/]")
    console.print("[cyan]请输入要下载的 Flutter 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]可以输入具体的版本号如 3.35.7，或使用 'latest' 表示最新稳定版[/]")
    console.print(f"[cyan]默认版本: {', '.join(DEFAULT_FLUTTER_VERSIONS)}[/]")
    flutter_input = Prompt.ask("Flutter 版本", default=",".join(DEFAULT_FLUTTER_VERSIONS))
    flutter_versions = parse_multi_version_input(flutter_input, DEFAULT_FLUTTER_VERSIONS)
    
    console.print("\n[bold yellow]📦 配置 Ubuntu-Latest 工具镜像[/]")
    console.print("[cyan]这个镜像包含完整的 Ubuntu 基础环境和常用开发工具，兼容大多数 GitHub Actions[/]")
    install_ubuntu = Confirm.ask("是否下载 Ubuntu-Latest 工具镜像？", default=DEFAULT_UBUNTU_INSTALL)
    
    # 显示配置摘要
    console.print("\n[bold cyan]📋 配置摘要：[/]")
    if temurin_versions:
        console.print(f"Temurin JDK 版本: {', '.join(temurin_versions)}")
    else:
        console.print("Temurin JDK 版本: 跳过")
    
    if aws_java_versions:
        console.print(f"Amazon Corretto JDK 版本: {', '.join(aws_java_versions)}")
    else:
        console.print("Amazon Corretto JDK 版本: 跳过")
    
    console.print(f"Flutter 版本: {', '.join(flutter_versions)}")
    console.print(f"Ubuntu-Latest: {'是' if install_ubuntu else '否'}")
    console.print(f"Runner 名称: {gitea_info['name']}")
    
    if not Confirm.ask("\n确认以上配置并开始安装？", default=True):
        console.print("[yellow]取消安装[/]")
        return False
    
    # 预拉取所有基础镜像
    console.print("\n[bold cyan]📥 开始预拉取所有基础镜像...[/]")
    
    all_images = []
    
    # Ubuntu 镜像
    if install_ubuntu:
        all_images.append(("Ubuntu-Latest 工具镜像", "catthehacker/ubuntu:act-latest"))
    
    # Temurin JDK 镜像
    for version in temurin_versions:
        validated = validate_java_version(version)
        all_images.append((f"Temurin JDK {version}", f"eclipse-temurin:{validated}-jdk-jammy"))
    
    # Amazon Corretto JDK 镜像
    for version in aws_java_versions:
        validated = validate_java_version(version)
        all_images.append((f"Amazon Corretto JDK {version}", f"public.ecr.aws/amazoncorretto/amazoncorretto:{validated}"))
    
    # Flutter 镜像
    for version in flutter_versions:
        validated = validate_flutter_version(version)
        all_images.append((f"Flutter {version}", f"ghcr.io/cirruslabs/flutter:{validated}"))
    
    failed_images = []
    for name, image in all_images:
        if not pull_single_image(image, name):
            failed_images.append((name, image))
    
    # 注册 Runner
    success = register_runner_with_versions(gitea_info, temurin_versions, aws_java_versions, flutter_versions, install_ubuntu)
    
    if success:
        show_runner_summary(gitea_info['name'], temurin_versions, aws_java_versions, flutter_versions, failed_images)
    else:
        console.print("[bold red]❌ Runner 注册失败，请检查错误信息[/]")
    
    return success

def register_runner_with_versions(gitea_info: Dict[str, Any], temurin_versions: List[str], 
                                 aws_java_versions: List[str], flutter_versions: List[str], 
                                 install_ubuntu: bool) -> bool:
    """注册 Runner 并支持多版本"""
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
            return False
    
    # 构建标签列表
    labels = []
    
    # Ubuntu 标签
    if install_ubuntu:
        labels.append("ubuntu-latest:docker://catthehacker/ubuntu:act-latest")
    
    # Temurin Java 标签
    for version in temurin_versions:
        validated = validate_java_version(version)
        labels.append(f"java-{version}:docker://eclipse-temurin:{validated}-jdk-jammy")
    
    # Amazon Corretto Java 标签
    for version in aws_java_versions:
        validated = validate_java_version(version)
        labels.append(f"java-aws-{version}:docker://public.ecr.aws/amazoncorretto/amazoncorretto:{validated}")
    
    # Flutter 标签
    for version in flutter_versions:
        validated = validate_flutter_version(version)
        if validated == 'stable':
            labels.append("flutter-stable:docker://ghcr.io/cirruslabs/flutter:stable")
        else:
            labels.append(f"flutter-{validated}:docker://ghcr.io/cirruslabs/flutter:{validated}")
    
    labels_str = ','.join(labels)
    
    # 创建持久化卷
    run(f"docker volume create {volume_name}", check=False)
    
    # 启动容器
    console.print(f"[cyan]启动 Runner 容器：{container_name}[/]")
    
    docker_cmd = f"""docker run -d \
  --name {container_name} \
  --restart unless-stopped \
  --network host \
  -e GITEA_INSTANCE_URL="{gitea_info['url']}" \
  -e GITEA_RUNNER_REGISTRATION_TOKEN="{gitea_info['token']}" \
  -e GITEA_RUNNER_NAME="{gitea_info['name']}" \
  -e GITEA_RUNNER_LABELS="{labels_str}" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v {volume_name}:/data \
  gitea/act_runner:latest"""
    
    try:
        run(docker_cmd, capture=True)
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Runner 注册失败！[/]")
        console.print(f"错误：{e.stderr[:500] if hasattr(e, 'stderr') and e.stderr else '未知错误'}")
        return False

# ==================== 模块 2: 仅下载多个 Flutter 版本镜像 ====================
def module_download_flutter_only() -> None:
    """模块2：仅下载多个Flutter版本镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块2：仅下载多个 Flutter 版本镜像[/]")
    
    console.print("\n[bold yellow]📦 Flutter 版本配置：[/]")
    console.print("[cyan]请输入要下载的 Flutter 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]📝 支持格式示例: '3.35.7, 3.38.5, latest; 3.22.7'[/]")
    console.print("[cyan]💡 'latest' 会自动转换为 'stable' 标签（获取最新稳定版）[/]")
    console.print(f"[cyan]🔧 默认版本: {', '.join(DEFAULT_FLUTTER_VERSIONS)}[/]")
    
    flutter_input = Prompt.ask("Flutter 版本", default=",".join(DEFAULT_FLUTTER_VERSIONS))
    flutter_versions = parse_multi_version_input(flutter_input, DEFAULT_FLUTTER_VERSIONS)
    
    console.print(f"\n[bold cyan]📋 准备下载以下 Flutter 版本：[/]")
    for i, version in enumerate(flutter_versions, 1):
        validated = validate_flutter_version(version)
        console.print(f"{i}. Flutter {version} → ghcr.io/cirruslabs/flutter:{validated}")
    
    if not Confirm.ask("\n确认下载以上镜像？", default=True):
        console.print("[yellow]取消下载[/]")
        return
    
    # 下载镜像
    failed = []
    for version in flutter_versions:
        validated = validate_flutter_version(version)
        image_name = f"ghcr.io/cirruslabs/flutter:{validated}"
        display_name = f"Flutter {version} (ghcr.io/cirruslabs/flutter:{validated})"
        
        console.print(f"\n[yellow]正在下载: {display_name}[/]")
        if not pull_single_image(image_name, f"Flutter {version}"):
            failed.append((f"Flutter {version}", image_name))
    
    # 显示结果
    console.print("\n" + "="*50)
    if failed:
        console.print(f"[yellow]部分镜像下载失败 ({len(failed)}/{len(flutter_versions)})[/]")
        for name, image in failed:
            console.print(f"[red]❌ {name}: {image}[/]")
    else:
        console.print("[bold green]✅ 所有选中镜像下载完成！[/]")
    
    # 显示已下载的 Flutter 镜像
    console.print("\n[bold cyan]📋 已下载的 Flutter 镜像：[/]")
    result = run("docker images ghcr.io/cirruslabs/flutter* --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'", capture=True)
    if result.stdout:
        console.print(result.stdout)
    else:
        console.print("[yellow]未找到 Flutter 镜像[/]")

# ==================== 模块 3: 仅下载多个 Temurin JDK 版本镜像 ====================
def module_download_temurin_jdk_only() -> None:
    """模块3：仅下载多个Eclipse Temurin JDK版本镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块3：仅下载多个 Eclipse Temurin JDK 版本镜像[/]")
    
    console.print("\n[bold yellow]📦 Eclipse Temurin JDK 版本配置：[/]")
    console.print("[cyan]请输入要下载的 Eclipse Temurin JDK 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]📝 支持格式示例: '8, 11, 17, 21, 25'[/]")
    console.print("[cyan]💡 建议下载常用版本: 8, 11, 17, 21, 25[/]")
    console.print(f"[cyan]🔧 默认版本: {', '.join(DEFAULT_JAVA_VERSIONS)}[/]")
    
    jdk_input = Prompt.ask("Eclipse Temurin JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    jdk_versions = parse_multi_version_input(jdk_input, DEFAULT_JAVA_VERSIONS)
    
    console.print(f"\n[bold cyan]📋 准备下载以下 Eclipse Temurin JDK 版本：[/]")
    for i, version in enumerate(jdk_versions, 1):
        validated = validate_java_version(version)
        console.print(f"{i}. Eclipse Temurin JDK {version} → eclipse-temurin:{validated}-jdk-jammy")
    
    if not Confirm.ask("\n确认下载以上镜像？", default=True):
        console.print("[yellow]取消下载[/]")
        return
    
    # 下载镜像
    failed = []
    for version in jdk_versions:
        validated = validate_java_version(version)
        image_name = f"eclipse-temurin:{validated}-jdk-jammy"
        display_name = f"Eclipse Temurin JDK {version} (eclipse-temurin:{validated}-jdk-jammy)"
        
        console.print(f"\n[yellow]正在下载: {display_name}[/]")
        if not pull_single_image(image_name, f"Eclipse Temurin JDK {version}"):
            failed.append((f"Eclipse Temurin JDK {version}", image_name))
    
    # 显示结果
    console.print("\n" + "="*50)
    if failed:
        console.print(f"[yellow]部分镜像下载失败 ({len(failed)}/{len(jdk_versions)})[/]")
        for name, image in failed:
            console.print(f"[red]❌ {name}: {image}[/]")
    else:
        console.print("[bold green]✅ 所有选中镜像下载完成！[/]")
    
    # 显示已下载的 Eclipse Temurin JDK 镜像
    console.print("\n[bold cyan]📋 已下载的 Eclipse Temurin JDK 镜像：[/]")
    result = run("docker images eclipse-temurin* --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'", capture=True)
    if result.stdout:
        console.print(result.stdout)
    else:
        console.print("[yellow]未找到 eclipse-temurin 镜像[/]")

# ==================== 模块 4: 仅下载多个 Amazon Corretto JDK 版本镜像 ====================
def module_download_aws_jdk_only() -> None:
    """模块4：仅下载多个AWS Amazon Corretto JDK版本镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块4：仅下载多个 AWS Amazon Corretto JDK 版本镜像[/]")
    
    console.print("\n[bold yellow]📦 AWS Amazon Corretto JDK 版本配置：[/]")
    console.print("[cyan]请输入要下载的 AWS Amazon Corretto JDK 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]📝 支持格式示例: '8, 11, 17, 21, 25'[/]")
    console.print("[cyan]💡 AWS Amazon Corretto 是 AWS 优化的 OpenJDK 发行版，在 AWS 环境性能更佳[/]")
    console.print(f"[cyan]🔧 默认版本: {', '.join(DEFAULT_JAVA_VERSIONS)}[/]")
    
    aws_jdk_input = Prompt.ask("AWS Amazon Corretto JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    aws_jdk_versions = parse_multi_version_input(aws_jdk_input, DEFAULT_JAVA_VERSIONS)
    
    console.print(f"\n[bold cyan]📋 准备下载以下 AWS Amazon Corretto JDK 版本：[/]")
    for i, version in enumerate(aws_jdk_versions, 1):
        validated = validate_java_version(version)
        console.print(f"{i}. AWS Amazon Corretto JDK {version} → public.ecr.aws/amazoncorretto/amazoncorretto:{validated}")
    
    if not Confirm.ask("\n确认下载以上镜像？", default=True):
        console.print("[yellow]取消下载[/]")
        return
    
    # 下载镜像
    failed = []
    for version in aws_jdk_versions:
        validated = validate_java_version(version)
        image_name = f"public.ecr.aws/amazoncorretto/amazoncorretto:{validated}"
        display_name = f"AWS Amazon Corretto JDK {version} (public.ecr.aws/amazoncorretto/amazoncorretto:{validated})"
        
        console.print(f"\n[yellow]正在下载: {display_name}[/]")
        if not pull_single_image(image_name, f"AWS Amazon Corretto JDK {version}"):
            failed.append((f"AWS Amazon Corretto JDK {version}", image_name))
    
    # 显示结果
    console.print("\n" + "="*50)
    if failed:
        console.print(f"[yellow]部分镜像下载失败 ({len(failed)}/{len(aws_jdk_versions)})[/]")
        for name, image in failed:
            console.print(f"[red]❌ {name}: {image}[/]")
    else:
        console.print("[bold green]✅ 所有选中镜像下载完成！[/]")
    
    # 显示已下载的 AWS Amazon Corretto JDK 镜像
    console.print("\n[bold cyan]📋 已下载的 AWS Amazon Corretto JDK 镜像：[/]")
    result = run("docker images public.ecr.aws/amazoncorretto/amazoncorretto* --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}'", capture=True)
    if result.stdout:
        console.print(result.stdout)
    else:
        console.print("[yellow]未找到 AWS Amazon Corretto JDK 镜像[/]")
    
    # 显示性能优势说明
    console.print("\n[bold yellow]🚀 AWS Amazon Corretto JDK 优势：[/]")
    console.print("• 专为 AWS 环境优化的 OpenJDK 发行版")
    console.print("• 在 AWS EC2 实例上性能提升 10%-20%")
    console.print("• 与 AWS 服务深度集成，兼容性更好")
    console.print("• 提供长期支持 (LTS) 版本")
    console.print("• 适用于部署在 AWS 环境的 Java 应用程序")

# ==================== 模块 5: 仅下载 Ubuntu-Latest 工具镜像 ====================
def module_download_ubuntu_only() -> None:
    """模块5：仅下载Ubuntu-Latest工具镜像"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]📥 模块5：仅下载 Ubuntu-Latest 工具镜像[/]")
    
    ubuntu_image = "catthehacker/ubuntu:act-latest"
    
    console.print(f"\n[bold cyan]📦 镜像详情：[/]")
    console.print(f"镜像名称: {ubuntu_image}")
    console.print("\n[bold yellow]🔧 包含的完整工具链：[/]")
    console.print("• 📦 Ubuntu 22.04 LTS (Jammy Jellyfish) 基础环境")
    console.print("• 🐍 Python 3.10+ 和 pip")
    console.print("• 📦 Node.js 和 npm")
    console.print("• 🐙 Git 和 GitHub CLI")
    console.print("• 🔨 GNU 开发工具链 (gcc, g++, make, cmake)")
    console.print("• 🐳 Docker CLI 和容器工具")
    console.print("• 📦 常用开发库和依赖")
    console.print("• 🔄 兼容大多数 GitHub Actions 工作流")
    console.print("\n[cyan]💡 这个镜像是专门为 GitHub Actions 兼容性优化的完整开发环境[/]")
    
    if not Confirm.ask("\n确认下载此镜像？", default=True):
        console.print("[yellow]取消下载[/]")
        return
    
    success = pull_single_image(ubuntu_image, "Ubuntu-Latest 工具镜像")
    
    if success:
        console.print("\n[bold green]✅ 镜像下载完成！[/]")
        console.print("[cyan]镜像信息：[/]")
        result = run(f"docker images {ubuntu_image} --format 'table {{.Repository}}:{{.Tag}}\\t{{.Size}}\\t{{.CreatedAt}}'", capture=True)
        if result.stdout:
            console.print(result.stdout)
        
        console.print("\n[bold yellow]📝 使用说明：[/]")
        console.print("在 workflow 中配置: [green]runs-on: ubuntu-latest[/]")
        console.print("Runner 会自动使用此镜像执行任务")

# ==================== 模块 6: 仅注册 Runner ====================
def module_register_runner_only() -> None:
    """模块6：仅注册Runner（不下载镜像）"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🚀 模块6：仅注册 Runner（快速模式）[/]")
    
    console.print("[yellow]⚠️  注意：此模式假设所需镜像已存在本地[/]")
    console.print("[yellow]如果镜像不存在，job 执行时会自动拉取，但首次运行会较慢[/]")
    
    # 获取 Gitea 信息
    gitea_info = get_gitea_info()
    
    console.print("\n[bold yellow]📦 配置 Runner 支持的标签[/]")
    console.print("[cyan]请输入支持的 Eclipse Temurin Java 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]输入 'skip' 跳过 Temurin JDK[/]")
    temurin_input = Prompt.ask("Eclipse Temurin JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    
    if temurin_input.strip().lower() == 'skip':
        temurin_versions = []
        console.print("[yellow]已跳过 Eclipse Temurin JDK[/]")
    else:
        temurin_versions = parse_multi_version_input(temurin_input, DEFAULT_JAVA_VERSIONS)
    
    console.print("\n[cyan]请输入支持的 AWS Amazon Corretto Java 版本（多个版本用空格、逗号或分号分隔）[/]")
    console.print("[cyan]输入 'skip' 跳过 Amazon Corretto JDK[/]")
    aws_java_input = Prompt.ask("AWS Amazon Corretto JDK 版本", default=",".join(DEFAULT_JAVA_VERSIONS))
    
    if aws_java_input.strip().lower() == 'skip':
        aws_java_versions = []
        console.print("[yellow]已跳过 AWS Amazon Corretto JDK[/]")
    else:
        aws_java_versions = parse_multi_version_input(aws_java_input, DEFAULT_JAVA_VERSIONS)
    
    console.print("\n[cyan]请输入支持的 Flutter 版本（多个版本用空格、逗号或分号分隔）[/]")
    flutter_input = Prompt.ask("Flutter 版本", default=",".join(DEFAULT_FLUTTER_VERSIONS))
    flutter_versions = parse_multi_version_input(flutter_input, DEFAULT_FLUTTER_VERSIONS)
    
    console.print("\n[cyan]是否支持 Ubuntu-Latest？[/]")
    support_ubuntu = Confirm.ask("支持 Ubuntu-Latest", default=True)
    
    # 直接注册 Runner
    success = register_runner_with_versions(gitea_info, temurin_versions, aws_java_versions, flutter_versions, support_ubuntu)
    
    if success:
        console.print("\n[bold green]✅ Runner 注册成功！[/]")
        
        # 构建支持的标签列表
        tags = []
        if support_ubuntu:
            tags.append("ubuntu-latest")
        for version in temurin_versions:
            tags.append(f"java-{version}")
        for version in aws_java_versions:
            tags.append(f"java-aws-{version}")
        for version in flutter_versions:
            validated = validate_flutter_version(version)
            tags.append(f"flutter-{validated}" if validated != 'stable' else "flutter-stable")
        
        console.print(f"[cyan]支持的标签: {', '.join(tags)}[/]")
        
        # 显示管理命令
        show_runner_management_commands(gitea_info['name'])
    else:
        console.print("[bold red]❌ Runner 注册失败[/]")

# ==================== 模块 7: 管理现有 Runner ====================
def module_manage_runners() -> None:
    """模块7：管理现有Runner"""
    console.print("\n" + "="*50)
    console.print("[bold magenta]🔧 模块7：管理现有 Runner[/]")
    
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
    try:
        choice = IntPrompt.ask("选择", default=0)
    except:
        choice = 0
    
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
    
    try:
        action = IntPrompt.ask("选择操作", default=1, choices=["1", "2", "3", "4", "5", "6", "7"])
    except:
        action = 1
    
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

# ==================== 辅助函数 ====================
def show_runner_summary(runner_name: str, temurin_versions: List[str], 
                       aws_java_versions: List[str], flutter_versions: List[str], 
                       failed_images: List[Tuple[str, str]]) -> None:
    """显示 Runner 安装摘要"""
    container_name = f"gitea-{runner_name}"
    
    console.print("\n" + "="*50)
    
    # 构建支持的标签列表
    tags = ["ubuntu-latest"]
    for version in temurin_versions:
        tags.append(f"java-{version}")
    for version in aws_java_versions:
        tags.append(f"java-aws-{version}")
    for version in flutter_versions:
        validated = validate_flutter_version(version)
        tags.append(f"flutter-{validated}" if validated != 'stable' else "flutter-stable")
    
    summary_panel = Panel.fit(
        f"[bold green]🎉 Runner 安装完成！[/]\n\n"
        f"容器名称: [cyan]{container_name}[/]\n"
        f"持久化卷: [cyan]gitea-runner-data-{runner_name}[/]\n"
        f"支持的标签: [yellow]{', '.join(tags)}[/]",
        title="安装成功", border_style="green"
    )
    
    console.print(summary_panel)
    
    if failed_images:
        console.print("\n[yellow]💡 以下镜像拉取失败（首次使用时自动拉取）：[/]")
        for name, image in failed_images:
            console.print(f"[yellow]• {name}: {image}[/]")
    
    show_runner_management_commands(runner_name)

def show_runner_management_commands(runner_name: str) -> None:
    """显示 Runner 管理命令"""
    container_name = f"gitea-{runner_name}"
    
    console.print("\n[bold cyan]🔧 管理命令：[/]")
    console.print(f"查看日志: [green]docker logs -f {container_name}[/]")
    console.print(f"重启: [green]docker restart {container_name}[/]")
    console.print(f"停止: [green]docker stop {container_name}[/]")
    console.print(f"删除容器: [green]docker rm -f {container_name}[/]")
    console.print(f"删除卷: [green]docker volume rm gitea-runner-data-{runner_name}[/]")
    console.print(f"查看状态: [green]docker ps --filter name={container_name}[/]")

# ==================== 主程序 ====================
def main() -> None:
    """主函数"""
    try:
        check_root()
        
        while True:
            choice = show_main_menu()
            
            if choice == 1:
                # 模块1: 重新完全安装注册Runner
                module_complete_installation()
                
            elif choice == 2:
                # 模块2: 仅下载多个Flutter版本镜像
                module_download_flutter_only()
                
            elif choice == 3:
                # 模块3: 仅下载多个Temurin JDK版本镜像
                module_download_temurin_jdk_only()
                
            elif choice == 4:
                # 模块4: 仅下载多个Amazon Corretto JDK版本镜像
                module_download_aws_jdk_only()
                
            elif choice == 5:
                # 模块5: 仅下载Ubuntu-Latest工具镜像
                module_download_ubuntu_only()
                
            elif choice == 6:
                # 模块6: 仅注册Runner（不下载镜像）
                module_register_runner_only()
                
            elif choice == 7:
                # 模块7: 管理现有Runner
                module_manage_runners()
                
            elif choice == 8:
                # 退出
                console.print("\n[bold green]👋 感谢使用，再见！[/]")
                break
            
            # 询问是否继续
            if choice != 8:
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
