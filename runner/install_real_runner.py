#!/usr/bin/env python3
"""
Gitea Runner 物理机专用安装脚本 - 2026年1月修复版
精准安装：OpenJDK 17 → Flutter → Gitea Runner
"""

import subprocess
import sys
import os
import shlex
import time
import socket
from pathlib import Path

# 尝试使用 rich 美化输出（可选，如果没装就优雅降级）
try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None




def rprint(text="", style=None, emoji=""):
    styles = {
        "title":    "bold magenta",
        "success":  "bold green",
        "info":     "bold cyan",
        "warning":  "bold yellow",
        "error":    "bold red",
        "dim":      "dim white",
    }
    
    if HAS_RICH:
        # 1. 自动选择样式名
        emoji_map = {"✅": "success", "❌": "error", "⚠️": "warning", "📦": "info"}
        style_name = style or emoji_map.get(emoji, "white")
        
        # 2. 获取实际的 Rich 渲染字符串 (例如 "bold green")
        full_style = styles.get(style_name, style_name) 
        
        # 3. 提取基础颜色用于 Emoji 前缀 (取最后一个词，如 "green")
        base_color = full_style.split()[-1]
        
        prefix = f"[bold bright_{base_color}]{emoji}[/] " if emoji else ""
        console.print(f"{prefix}{text}", style=full_style)
    else:
        # 简化版 ANSI 处理
        color_code_map = {"green": "92", "red": "91", "yellow": "93", "cyan": "96"}
        # 匹配 style 字符串中是否含有颜色关键词
        c_code = next((code for word, code in color_code_map.items() if word in (style or "")), "0")
        print(f"\033[{c_code}m{emoji} {text}\033[0m")

def run(cmd, desc="", check=True, shell=False, cwd=None, capture=True):
    if desc:
        rprint(desc, emoji="📦")

    try:
        kwargs = {
            "shell": shell,
            "capture_output": capture,
            "text": True,
            "check": check,
        }
        if cwd:
            kwargs["cwd"] = cwd

        result = subprocess.run(cmd if shell else shlex.split(cmd), **kwargs)

        if capture and result.stdout and desc:
            lines = result.stdout.strip().splitlines()
            if lines:
                rprint(f"输出: {lines[0][:100]}", style="dim")
                if len(lines) > 1:
                    rprint(f"      ... ({len(lines)-1} 更多行)", style="dim")

        return result
    except subprocess.CalledProcessError as e:
        if check:
            err = e.stderr.strip()[:400] if e.stderr else str(e)
            rprint(f"❌ 失败: {err}", style="bold red", emoji="💥")
            sys.exit(1)
        return None


def check_requirements():
    rprint("检查系统基本要求...", emoji="🔍")
    if os.geteuid() != 0:
        rprint("需要 root 权限运行此脚本！", style="bold red")
        sys.exit(1)

    distro = run("lsb_release -is 2>/dev/null || echo Unknown", check=False, shell=True)
    if distro and not any(x in distro.stdout for x in ["Ubuntu", "Debian"]):
        rprint("⚠️  脚本主要针对 Ubuntu/Debian，其他系统可能需要手动调整", style="yellow")

    rprint("系统要求检查通过", emoji="✅")


def create_runner_user():
    rprint("="*60, emoji="═")
    rprint("步骤 1 : 创建专用用户 act_runner", style="bold blue")
    rprint("="*60, emoji="═")

    if run("id act_runner", check=False, shell=True).returncode == 0:
        rprint("用户 act_runner 已存在", emoji="✅")
        if not os.path.isdir("/home/act_runner"):
            run("mkhomedir_helper act_runner", check=False, shell=True)
        return True

    run("groupadd act_runner 2>/dev/null || true", "创建组", shell=True)
    run("useradd -m -s /bin/bash -g act_runner -G sudo act_runner", "创建用户", shell=True)

    sudoers = "/etc/sudoers.d/99-act-runner"
    with open(sudoers, "w") as f:
        f.write("act_runner ALL=(ALL) NOPASSWD:ALL\n")
    run(f"chmod 440 {sudoers}", "设置sudo免密")

    rprint("act_runner 用户创建完成 + sudo免密", emoji="✅")
    return True


def install_openjdk17():
    rprint("="*60, emoji="═")
    rprint("步骤 2 : 安装 OpenJDK 17", style="bold blue")
    rprint("="*60, emoji="═")

    if run("java -version 2>&1 | grep -q 'openjdk.*17'", check=False, shell=True).returncode == 0:
        rprint("OpenJDK 17 已经安装", emoji="✅")
        return True

    run("apt-get update -y", "更新软件源")
    run("apt-get install -y openjdk-17-jdk", "安装 OpenJDK 17")

    java_home = run("readlink -f $(which java) | sed 's:/bin/java::'", shell=True, check=False)
    if java_home and java_home.stdout.strip():
        jh = java_home.stdout.strip()
        with open("/etc/profile.d/java.sh", "w") as f:
            f.write(f'export JAVA_HOME="{jh}"\nexport PATH="$JAVA_HOME/bin:$PATH"\n')
        run("chmod 644 /etc/profile.d/java.sh")
        rprint(f"JAVA_HOME 已设置为: {jh}", emoji="✅")

    return True


def install_flutter():
    rprint("="*60, emoji="═")
    rprint("步骤 3 : 安装 Flutter", style="bold blue")
    rprint("="*60, emoji="═")

    flutter_dir = "/opt/flutter"
    flutter_bin = f"{flutter_dir}/bin/flutter"

    if os.path.exists(flutter_dir):
        rprint(f"检测到已有目录 {flutter_dir}", style="yellow", emoji="⚠️")
        if input("是否删除现有 Flutter 并重新安装？(y/N): ").strip().lower() != 'y':
            rprint("用户取消，跳过 Flutter 安装")
            return True

    default_ver = "3.35.7"
    ver = input(f"Flutter 版本 (默认 {default_ver}): ").strip() or default_ver

    use_cn = input("是否使用中国镜像加速？(y/N): ").strip().lower() == 'y'

    run(f"rm -rf {flutter_dir}", "清理旧目录")
    run(f"mkdir -p {flutter_dir}", "创建目录")
    run(f"chown -R act_runner:act_runner {flutter_dir}")

    tar_file = f"/opt/flutter_linux_{ver}-stable.tar.xz"

    if not os.path.exists(tar_file):
        url = f"https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_{ver}-stable.tar.xz"
        run(f"curl -L -# -o {tar_file} {url}", f"下载 Flutter {ver}")
    else:
        rprint(f"使用已存在的安装包：{tar_file}", emoji="♻️")

    run(f"tar xf {tar_file} -C {flutter_dir} --strip-components=1", "解压")
    run(f"chown -R act_runner:act_runner {flutter_dir}", "修复权限")

    # 环境变量
    lines = [
        f'export PATH="{flutter_dir}/bin:$PATH"',
        f'export FLUTTER_ROOT="{flutter_dir}"',
    ]
    if use_cn:
        lines += [
            'export PUB_HOSTED_URL=https://pub.flutter-io.cn',
            'export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn',
        ]

    env_block = "\n".join(lines) + "\n"

    for profile in ["/etc/profile.d/flutter.sh", "/home/act_runner/.profile"]:
        try:
            with open(profile, "a") as f:
                f.write(f"\n# Flutter {ver} - {time.strftime('%Y-%m-%d')}\n{env_block}")
            if profile.startswith("/etc"):
                run(f"chmod 644 {profile}")
            else:
                run(f"chown act_runner:act_runner {profile}")
        except Exception as e:
            rprint(f"写入 {profile} 失败: {e}", style="yellow")

    # 立即在当前进程生效
    os.environ["PATH"] = f"{flutter_dir}/bin:" + os.environ.get("PATH", "")
    os.environ["FLUTTER_ROOT"] = flutter_dir
    if use_cn:
        os.environ.update({
            "PUB_HOSTED_URL": "https://pub.flutter-io.cn",
            "FLUTTER_STORAGE_BASE_URL": "https://storage.flutter-io.cn"
        })

    # 尝试 source（部分生效）
    run("source /etc/profile.d/flutter.sh 2>/dev/null || true", shell=True, check=False)

    # doctor
    rprint("执行 flutter doctor 检查...", emoji="🔍")
    doctor = run(f"sudo -u act_runner {flutter_bin} doctor", capture=True, check=False, shell=True)

    if doctor and doctor.returncode == 0:
        rprint("flutter doctor 输出：", emoji="📋")
        for line in doctor.stdout.splitlines():
            if line.strip():
                rprint(f"  {line}", style="dim white")
        rprint("Flutter 环境看起来正常（警告可以先忽略）", emoji="✅")
    else:
        rprint("doctor 执行有非零退出码，但不影响使用", style="yellow")

    # 修复root下不允许运行flutter.        
    fix_git_safe_directory()

    return True

def fix_git_safe_directory():
    """
    粗暴解决 git dubious ownership 问题：
    - root 用户信任所有 git 仓库
    - act_runner 用户也信任所有 git 仓库
    
    在物理机/个人/可信内部 CI 环境下基本无害，
    反正都是自己人玩，自己信得过就行。
    """
    rprint("正在永久关闭 git 的 'dubious ownership' 烦人检查...", style="bold yellow", emoji="💣")

    commands = [
        # root 信任所有目录
        ("git config --global --add safe.directory '*'", "root 用户"),
        
        # act_runner 信任所有目录
        ("sudo -u act_runner git config --global --add safe.directory '*'", "act_runner 用户"),
    ]

    for cmd, who in commands:
        try:
            result = run(cmd, shell=True, check=False, capture=True)
            if result.returncode == 0:
                rprint(f"→ {who} 已信任所有 git 目录", style="green", emoji="✅")
            else:
                rprint(f"→ {who} 配置失败: {result.stderr.strip()[:200]}", style="red", emoji="❌")
        except Exception as e:
            rprint(f"执行时出错 ({who}): {e}", style="red")

    # 给个小提示
    rprint("以后 flutter、git 相关的 ownership 警告应该都不会再出现了", style="dim cyan")
    rprint("（物理机个人 CI 这么干很常见，别被安全党吓到）", style="dim")

def install_act_runner():
    rprint("="*60, emoji="═")
    rprint("步骤 4 : 安装与注册 Gitea Actions Runner", style="bold blue")
    rprint("="*60, emoji="═")

    bin_path = "/usr/local/bin/act_runner"
    version = "0.2.13"

    if os.path.exists(bin_path):
        ver_out = run(f"{bin_path} --version", check=False, shell=True)
        if ver_out and ver_out.returncode == 0:
            rprint(f"act_runner 已存在 → {ver_out.stdout.strip()}", emoji="✅")
        else:
            rprint("现有 act_runner 可执行文件损坏，将重新下载", style="yellow")

    else:
        url = f"https://dl.gitea.com/act_runner/{version}/act_runner-{version}-linux-amd64"
        run(f"curl -L -f -o /tmp/act_runner {url}", "下载 act_runner")
        run("mv /tmp/act_runner /usr/local/bin/act_runner")
        run("chmod 755 /usr/local/bin/act_runner")
        run("chown act_runner:act_runner /usr/local/bin/act_runner")

    # =============================================
    # 注册部分 - 关键修复：必须在 /home/act_runner 下执行
    # =============================================
    rprint("准备注册 Runner（必须在用户家目录执行）", emoji="🔐")

    default_url = "http://192.168.0.169:3000"
    default_token = "oRyijO9he0A7cNWU6YT4YiDGemOljPn64ynMkMTq"   # 记得生产环境改掉这个！

    rprint("Gitea 实例地址", emoji="🌐")
    gitea_url = input(f"请输入 Gitea 地址（默认 {default_url}）： ").strip() or default_url

    rprint("Runner Registration Token", emoji="🔑")
    rprint(f"当前默认 token： {default_token}", style="yellow dim")
    token = input("请输入 registration token（直接回车用默认值）： ").strip()

    if not token:
        token = default_token
        rprint("→ 使用默认 token", style="italic green")
    else:
        rprint(f"→ 使用你输入的 token（前8位：{token[:8]}...）", style="italic cyan")

    runner_name = input("Runner 名称 (默认 my-runner): ").strip() or "my-runner"
    labels = input("标签 (默认 ubuntu-latest,flutter,jdk17,docker): ").strip() or "ubuntu-latest,flutter,jdk17,docker"

    register_cmd = (
        f"/usr/local/bin/act_runner register --no-interactive "
        f"--instance {gitea_url} --token {token} "
        f"--name {runner_name} --labels {labels}"
    )

    rprint("清理旧注册文件...", emoji="🧹")
    run("sudo -u act_runner rm -f /home/act_runner/.runner*", cwd="/home/act_runner", shell=True)

    rprint("开始注册（重要：在 act_runner 家目录执行）...", emoji="📝")

    # 核心修复：cd 到家目录再执行
    reg_result = run(
        f"sudo -u act_runner bash -c 'cd /home/act_runner && {register_cmd}'",
        shell=True, check=False
    )

    if reg_result.returncode == 0:
        rprint("Runner 注册成功！", style="bold green", emoji="🎉")
    else:
        rprint("首次注册失败（常见权限或网络问题）", style="bold yellow")
        if reg_result:
            print(reg_result.stderr[:600])
        rprint("等待 3 秒后自动重试一次...", emoji="⏳")
        time.sleep(3)
        reg_result = run(
            f"sudo -u act_runner bash -c 'cd /home/act_runner && {register_cmd}'",
            shell=True, check=False
        )
        if reg_result.returncode == 0:
            rprint("重试注册成功！", style="bold green", emoji="🎉")
        else:
            rprint("仍然失败，请手动执行以下命令：", style="bold red")
            rprint(f"  sudo -u act_runner bash -c 'cd /home/act_runner && {register_cmd}'")

    # systemd 服务
    rprint("生成 systemd 服务文件...", emoji="⚙️")

    java_home = ""
    jh_cmd = run("readlink -f $(which java) | sed 's:/bin/java::'", shell=True, check=False)
    if jh_cmd:
        java_home = jh_cmd.stdout.strip()

    service = f"""[Unit]
Description=Gitea Actions Runner
After=network.target

[Service]
Type=simple
User=act_runner
Group=act_runner
WorkingDirectory=/home/act_runner
ExecStart=/usr/local/bin/act_runner daemon
Restart=always
RestartSec=5s
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/flutter/bin"
Environment="JAVA_HOME={java_home}"
Environment="FLUTTER_ROOT=/opt/flutter"

NoNewPrivileges=yes
ProtectSystem=full
ReadWritePaths=/home/act_runner /opt/flutter

[Install]
WantedBy=multi-user.target
"""

    svc_file = "/etc/systemd/system/gitea-runner.service"
    with open(svc_file, "w") as f:
        f.write(service)

    run("systemctl daemon-reload")
    run("systemctl enable --now gitea-runner.service")

    time.sleep(2)  # 给服务一点启动时间
    status = run("systemctl is-active gitea-runner.service", check=False, shell=True)
    if status and "active" in status.stdout:
        rprint("Gitea Runner 服务已启动", emoji="✅")
    else:
        rprint("服务启动可能有延迟或异常，请稍后检查 journalctl", style="yellow")


def main():
    rprint("Gitea Runner 物理机专用安装脚本".center(60), style="bold magenta")
    rprint("OpenJDK 17  +  Flutter  +  act_runner".center(60), style="dim")
    print()

    if input("确认开始安装？(Y/n): ").strip().lower() not in ('', 'y'):
        return

    try:
        check_requirements()
        create_runner_user()
        install_openjdk17()
        install_flutter()
        install_act_runner()
        rprint("安装流程执行完毕，建议重启 shell 或新开终端验证环境变量", style="bold cyan")
    except Exception as e:
        rprint(f"安装过程中发生严重错误: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()