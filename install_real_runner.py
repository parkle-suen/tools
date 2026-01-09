#!/usr/bin/env python3
"""
Gitea act_runner + Flutter + Amazon Corretto 17 一键配置脚本（增强版）
适用于 Ubuntu 22.04 / 24.04 LTS 物理机（非容器）
最后更新参考：2026年1月

使用方式：
sudo python3 this_script.py --gitea_url https://your-gitea.com --token YOUR_TOKEN [--no_mirror]

敏感信息已包含示例值，请根据实际情况修改或通过命令行传入
"""

import os
import subprocess
import argparse
import getpass
import sys
import shutil
from pathlib import Path

# ====================== 配置区（可修改） ======================
DEFAULT_GITEA_URL = "http://192.168.0.169:3000"           # 示例默认值（本地测试用）
DEFAULT_RUNNER_TOKEN = "oRyijO9he0A7cNWU6YT4YiDGemOljPn64ynMkMTq"  # 示例 token，请替换为真实值
DEFAULT_RUNNER_LABELS = "ubuntu-latest,flutter,android,jdk-17"     # 已添加 jdk-17

FLUTTER_INSTALL_DIR = "/opt/flutter"
ACT_RUNNER_BIN_DIR = "/usr/local/bin"
ACT_RUNNER_VERSION = "latest"
RUNNER_USER = "act_runner"
RUNNER_HOME = f"/home/{RUNNER_USER}"

# 中国镜像
USE_CHINA_MIRROR = True
PUB_HOSTED = "https://pub.flutter-io.cn"
FLUTTER_STORAGE = "https://storage.flutter-io.cn"

# ====================== 全局清理函数 ======================
def cleanup_on_failure():
    print("\n发生错误，正在尝试清理...")
    try:
        # 删除 runner 用户（谨慎操作）
        if user_exists(RUNNER_USER):
            run(f"sudo userdel -r {RUNNER_USER}", check=False)
        # 删除 Flutter 目录
        if dir_exists(FLUTTER_INSTALL_DIR):
            shutil.rmtree(FLUTTER_INSTALL_DIR, ignore_errors=True)
        # 删除 act_runner 二进制
        bin_path = Path(ACT_RUNNER_BIN_DIR) / "act_runner"
        if bin_path.exists():
            bin_path.unlink()
        # 删除 systemd 服务
        service_file = Path("/etc/systemd/system/gitea-act-runner.service")
        if service_file.exists():
            run("sudo systemctl stop gitea-act-runner || true", check=False)
            run("sudo systemctl disable gitea-act-runner || true", check=False)
            service_file.unlink()
            run("sudo systemctl daemon-reload", check=False)
        print("清理完成（部分可能已无法恢复，请手动检查）")
    except Exception as e:
        print(f"清理失败: {e}")

# ====================== 工具函数 ======================
def run(cmd, check=True, capture_output=False, shell=False, cwd=None):
    print(f"+ {cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, check=check, text=True,
                               capture_output=capture_output, cwd=cwd)
        if capture_output:
            output = result.stdout.strip()
            print(output)
            return output
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if check:
            cleanup_on_failure()
            sys.exit(1)

def user_exists(username):
    try:
        run(f"id {username}", check=True)
        return True
    except:
        return False

def dir_exists(path):
    return Path(path).is_dir()

def append_to_bashrc(line):
    bashrc = Path.home() / ".bashrc"
    content = bashrc.read_text() if bashrc.exists() else ""
    if line not in content:
        with open(bashrc, "a") as f:
            f.write(line + "\n")
        print(f"已添加至 ~/.bashrc: {line}")

# ====================== 主步骤 ======================
def create_runner_user():
    if user_exists(RUNNER_USER):
        print(f"用户 {RUNNER_USER} 已存在，跳过创建")
        return

    print(f"创建专用 runner 用户: {RUNNER_USER}")
    run(f"""
    useradd -m -s /bin/bash -d {RUNNER_HOME} {RUNNER_USER}
    mkdir -p {RUNNER_HOME}/.config
    chown -R {RUNNER_USER}:{RUNNER_USER} {RUNNER_HOME}
    """, shell=True)

def install_amazon_corretto_17():
    print("安装 Amazon Corretto 17 (JDK) ...")

    keyring = "/usr/share/keyrings/corretto-keyring.asc"
    if not Path(keyring).exists():
        run("wget -O- https://apt.corretto.aws/corretto.key | gpg --dearmor -o /usr/share/keyrings/corretto-keyring.asc")

    sources_list = "/etc/apt/sources.list.d/corretto.sources"
    if not Path(sources_list).exists():
        run(f"""
        echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.asc] https://apt.corretto.aws stable main" | tee {sources_list}
        """, shell=True)

    run("apt update")
    run("apt install -y java-17-amazon-corretto-jdk")

    # 尝试设置默认（多版本共存时）
    run("update-java-alternatives --set java-17-amazon-corretto-amd64 || true", check=False)

    java_ver = run("java -version", capture_output=True)
    print(f"Java 版本：\n{java_ver}")

def install_flutter(args):
    print("安装/更新 Flutter SDK ...")

    mirror_args = ""
    if USE_CHINA_MIRROR:
        append_to_bashrc(f'export PUB_HOSTED_URL="{PUB_HOSTED}"')
        append_to_bashrc(f'export FLUTTER_STORAGE_BASE_URL="{FLUTTER_STORAGE}"')
        mirror_args = f"PUB_HOSTED_URL={PUB_HOSTED} FLUTTER_STORAGE_BASE_URL={FLUTTER_STORAGE}"

    if dir_exists(FLUTTER_INSTALL_DIR):
        print(f"目录已存在，尝试更新...")
        os.chdir(FLUTTER_INSTALL_DIR)
        run("git pull", check=False)
    else:
        run(f"mkdir -p {FLUTTER_INSTALL_DIR}")
        run(f"git clone --depth 1 https://github.com/flutter/flutter.git -b stable {FLUTTER_INSTALL_DIR}")

    # 添加 PATH
    append_to_bashrc(f'export PATH="$PATH:{FLUTTER_INSTALL_DIR}/bin"')

    # 刷新环境（当前会话）
    os.environ["PATH"] = f"{FLUTTER_INSTALL_DIR}/bin:{os.environ.get('PATH', '')}"

    print("运行 flutter doctor...")
    run(f"{mirror_args} flutter doctor", shell=True, check=False)

    print("自动接受 Android licenses...")
    try:
        run(f"yes | {mirror_args} flutter doctor --android-licenses", shell=True)
    except:
        print("Android licenses 接受失败，请稍后手动运行 flutter doctor --android-licenses")

def install_gitea_act_runner(args):
    print("安装 Gitea act_runner ...")

    bin_path = Path(ACT_RUNNER_BIN_DIR) / "act_runner"
    if not bin_path.exists():
        version_part = "" if ACT_RUNNER_VERSION == "latest" else ACT_RUNNER_VERSION
        url = f"https://dl.gitea.com/act_runner/{version_part}/act_runner-{version_part or 'latest'}-linux-amd64"
        run(f"curl -L -o {bin_path} {url}")
        run(f"chmod +x {bin_path}")

    # 注册（在 RUNNER_HOME 下）
    runner_file = Path(RUNNER_HOME) / ".runner"
    if not runner_file.exists():
        register_cmd = f"{bin_path} register --no-interactive --instance {args.gitea_url} --token {args.token}"
        if args.labels:
            register_cmd += f" --labels {args.labels}"
        run(f"sudo -u {RUNNER_USER} {register_cmd}", cwd=RUNNER_HOME, shell=True)

    # systemd 服务
    service_content = f"""[Unit]
Description=Gitea Actions Runner ({args.gitea_url})
After=network.target

[Service]
User={RUNNER_USER}
Group={RUNNER_USER}
WorkingDirectory={RUNNER_HOME}
ExecStart={ACT_RUNNER_BIN_DIR}/act_runner daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    service_path = Path("/etc/systemd/system/gitea-act-runner.service")
    with open("/tmp/gitea-runner.service", "w") as f:
        f.write(service_content)
    run(f"mv /tmp/gitea-runner.service {service_path}")
    run("systemctl daemon-reload")
    run("systemctl enable --now gitea-act-runner.service")

    print("Runner 服务已启动！")
    run("systemctl status gitea-act-runner --no-pager", check=False)

# ====================== 主程序 ======================
def main():
    parser = argparse.ArgumentParser(description="Gitea Runner + Flutter + Corretto 一键配置（增强版）")
    parser.add_argument("--gitea_url", default=DEFAULT_GITEA_URL, help="Gitea 实例 URL")
    parser.add_argument("--token", default=DEFAULT_RUNNER_TOKEN, help="Runner registration token")
    parser.add_argument("--labels", default=DEFAULT_RUNNER_LABELS, help="Runner labels")
    parser.add_argument("--no_mirror", action="store_true", help="禁用中国镜像")
    parser.add_argument("--install_flutter", action="store_true", default=True, help="安装 Flutter")
    parser.add_argument("--install_corretto", action="store_true", default=True, help="安装 Amazon Corretto 17")

    args = parser.parse_args()

    if not args.token:
        args.token = input("请输入 Gitea Runner Token: ").strip()
        if not args.token:
            print("Token 不能为空！")
            sys.exit(1)

    if not args.gitea_url or "example.com" in args.gitea_url:
        args.gitea_url = input(f"请输入 Gitea URL (当前默认 {DEFAULT_GITEA_URL}): ").strip() or DEFAULT_GITEA_URL

    global USE_CHINA_MIRROR
    USE_CHINA_MIRROR = not args.no_mirror

    print(f"开始配置... Gitea: {args.gitea_url} | 使用镜像: {USE_CHINA_MIRROR}")

    try:
        create_runner_user()

        if args.install_corretto:
            install_amazon_corretto_17()

        if args.install_flutter:
            install_flutter(args)

        install_gitea_act_runner(args)

        print("\n=== 配置完成！===")
        print("1. 建议执行: source ~/.bashrc")
        print("2. Flutter 环境已自动检查（见上方输出）")
        print("3. Runner 服务状态: sudo systemctl status gitea-act-runner")
        print("4. 在 Gitea 后台 -> Actions -> Runners 查看是否在线")
    except Exception as e:
        print(f"\n配置过程中发生严重错误: {e}")
        cleanup_on_failure()
        sys.exit(1)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("请使用 sudo 执行此脚本！")
        sys.exit(1)
    main()