#!/usr/bin/env python3
import os
import subprocess
import getpass
import sys
import time

# 检测当前用户身份
IS_ROOT = os.geteuid() == 0
SUDO_PREFIX = "" if IS_ROOT else "sudo "


def run(cmd, check=True, retries=1, needs_sudo=False):
    """执行命令，支持重试和智能sudo处理"""
    # 智能添加sudo前缀
    if needs_sudo and not cmd.startswith("sudo "):
        cmd = f"{SUDO_PREFIX}{cmd}"

    for i in range(retries):
        print(f"执行 → {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result
        elif i < retries - 1:
            print(f"重试中... ({i + 1}/{retries})")
            time.sleep(2)

    if check and result.returncode != 0:
        print(f"错误：命令执行失败 → {cmd}")
        print(f"错误输出: {result.stderr}")
        sys.exit(1)
    return result


def ask_yes_no(question):
    while True:
        ans = input(f"\n{question} (y/n): ").strip().lower()
        if ans in ["y", "yes"]:
            return True
        if ans in ["n", "no"]:
            return False
        print("请回答 y 或 n")


def check_network():
    """检查网络连接"""
    print("检查网络连接...")
    # 检查是否能访问Docker仓库
    test_urls = [
        "https://download.docker.com",
        "https://raw.githubusercontent.com",
        "https://get.docker.com",
    ]

    accessible = False
    for url in test_urls:
        try:
            result = subprocess.run(
                f"curl -s --head --connect-timeout 5 {url}",
                shell=True,
                capture_output=True,
            )
            if result.returncode == 0:
                print(f"✓ 可访问: {url}")
                accessible = True
            else:
                print(f"✗ 无法访问: {url}")
        except:
            print(f"✗ 连接失败: {url}")

    if not accessible:
        print("\n⚠️  网络连接可能有问题，请检查网络设置")
        if not ask_yes_no("是否继续安装？"):
            sys.exit(1)

    return accessible


# ==================== 开始 ====================
print("=" * 65)
print(" Ubuntu Server Docker + Portainer 安装脚本（修复版）".center(65))
print("=" * 65)

# 显示当前用户身份
if IS_ROOT:
    print(f"当前用户: root (超级用户)")
else:
    print(f"当前用户: {getpass.getuser()} (普通用户)")

# 检查网络
if not check_network():
    print("网络连接检查失败，但用户选择继续安装")

# 1. Docker 安装方式选择
print("\nDocker 安装方式选择：")
print("1. 生产环境安装（使用APT仓库，推荐）")
print("2. 快速安装（使用官方脚本）")
print("3. 跳过Docker安装")

while True:
    choice = input("\n请选择 1 / 2 / 3 : ").strip()
    if choice == "1":
        install_production = True
        break
    elif choice == "2":
        install_production = False
        break
    elif choice == "3":
        install_production = None
        break
    else:
        print("请输入 1、2 或 3")

# 执行选择的 Docker 安装
if install_production is True:
    print("\n使用 生产环境安装方式...")

    # 检查是否已存在Docker仓库
    docker_repo_files = [
        "/etc/apt/sources.list.d/docker.list",
        "/etc/apt/sources.list.d/docker.sources",
        "/etc/apt/sources.list.d/docker.list.save",
    ]

    repo_exists = any(os.path.exists(f) for f in docker_repo_files)

    if repo_exists:
        print("检测到已存在Docker仓库配置")
        run("apt update -y", needs_sudo=True)
    else:
        print("配置 Docker 官方仓库...")

        # 获取系统信息
        result = run("lsb_release -cs", check=False)
        if result.returncode == 0:
            codename = result.stdout.strip()
        else:
            # 备用方法获取codename
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if "VERSION_CODENAME" in line:
                            codename = line.split("=")[1].strip().strip('"')
                            break
                    else:
                        codename = "focal"  # 默认
            except:
                codename = "focal"

        print(f"检测到系统版本: {codename}")

        # 使用传统.list文件格式，兼容性更好
        commands = [
            "apt update -y",
            "apt install -y apt-transport-https ca-certificates curl software-properties-common",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
            "chmod a+r /etc/apt/keyrings/docker.asc",
            f'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu {codename} stable" | tee /etc/apt/sources.list.d/docker.list',
            "apt update -y",
        ]

        for cmd in commands:
            if not run(cmd, check=True, retries=2, needs_sudo=True):
                print(f"命令失败: {cmd}")
                print("是否切换到快速安装方式？")
                if ask_yes_no("使用快速安装脚本继续？"):
                    install_production = False
                    break
                else:
                    sys.exit(1)

    if install_production is True:  # 如果还在使用生产环境安装
        # 安装Docker
        print("安装Docker组件...")
        run(
            "apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            retries=2,
            needs_sudo=True,
        )
        run("systemctl enable --now docker", needs_sudo=True)

elif install_production is False:
    print("\n使用 快速安装脚本...")
    commands = [
        "curl -fsSL https://get.docker.com -o get-docker.sh",
        "sh get-docker.sh",
        "rm -f get-docker.sh",
        "systemctl enable --now docker",
    ]

    for cmd in commands:
        # 只有安装脚本需要sudo权限
        needs_sudo = "sh get-docker.sh" in cmd or "systemctl" in cmd
        run(cmd, check=True, retries=2, needs_sudo=needs_sudo)

else:
    print("\n跳过 Docker 安装")

# 检查 Docker
print("\n检查 Docker 是否正常...")
result = subprocess.run("docker version >/dev/null 2>&1", shell=True)
if result.returncode != 0:
    print("警告：Docker 未运行！")
    print("尝试启动Docker服务...")
    run("systemctl start docker", needs_sudo=True)
    run("systemctl status docker --no-pager", check=False, needs_sudo=True)
else:
    print("✓ Docker 正常！")
    os.system("docker --version")

# 2. Portainer 安装
if ask_yes_no("是否安装 Portainer CE？"):
    # 获取要使用的用户
    if IS_ROOT:
        print("\n⚠️  当前为root用户，需要指定一个普通用户来管理Portainer数据")
        print("建议使用一个已存在的普通用户，或创建新用户")
        while True:
            portainer_user = input(
                "请输入用于Portainer数据管理的用户名 (留空使用当前用户): "
            ).strip()
            if not portainer_user:
                portainer_user = getpass.getuser()
                break
            # 检查用户是否存在
            result = run(f"id {portainer_user}", check=False)
            if result.returncode == 0:
                break
            else:
                print(f"用户 '{portainer_user}' 不存在，请重新输入")
    else:
        portainer_user = getpass.getuser()

    print(f"使用用户: {portainer_user} 管理Portainer数据")

    # 创建数据目录 - 使用标准位置
    data_dir = "/var/lib/portainer"
    print(f"\n创建数据目录：{data_dir}")

    commands = [
        f"mkdir -p {data_dir}",
        f"chown -R {portainer_user}:{portainer_user} {data_dir}",
        # 停止并移除现有容器
        "docker stop portainer 2>/dev/null || true",
        "docker rm portainer 2>/dev/null || true",
        # 创建Volume
        "docker volume create portainer_data 2>/dev/null || true",
    ]

    for cmd in commands:
        # 前两个命令需要sudo权限
        needs_sudo = cmd.startswith("mkdir") or cmd.startswith("chown")
        run(cmd, check=False, needs_sudo=needs_sudo)

    # 创建符号链接（可选）
    if ask_yes_no("是否创建符号链接到用户主目录？"):
        user_home = f"/home/{portainer_user}" if portainer_user != "root" else "/root"
        symlink_path = f"{user_home}/portainer_data"
        symlink_cmd = (
            f"ln -sf /var/lib/docker/volumes/portainer_data/_data {symlink_path}"
        )
        run(symlink_cmd, check=False, needs_sudo=True)
        print(f"符号链接创建在: {symlink_path}")

    print("部署 Portainer 容器...")

    # 运行Portainer
    portainer_cmd = """docker run -d \
--name portainer \
--restart=always \
-p 8000:8000 \
-p 9443:9443 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v portainer_data:/data \
portainer/portainer-ce:latest"""

    run(portainer_cmd)

    print("\n" + "=" * 50)
    print("✓ Portainer 部署完成！")
    print("访问地址:")
    print("  HTTP管理: http://你的IP:9000")
    print("  HTTPS管理: https://你的IP:9443 (推荐)")
    print("  Edge代理: http://你的IP:8000")
    print(f"数据目录: {data_dir}")
    print(f"数据所有者: {portainer_user}")
    print("首次访问需要设置管理员密码")
    print("=" * 50)

# 3. 添加用户到docker组
if IS_ROOT:
    print("\n当前为root用户，无需添加到docker组")
    if ask_yes_no("是否要将一个普通用户添加到docker组？"):
        while True:
            docker_user = input("请输入要添加到docker组的用户名: ").strip()
            if docker_user:
                result = run(f"id {docker_user}", check=False)
                if result.returncode == 0:
                    run(f"usermod -aG docker {docker_user}", needs_sudo=True)
                    print(f"✓ 已将用户 '{docker_user}' 添加到docker组")
                    print("注意：用户需要重新登录或运行 'newgrp docker' 使权限生效")
                    break
                else:
                    print(f"用户 '{docker_user}' 不存在，请重新输入")
else:
    current_user = getpass.getuser()
    if ask_yes_no(f"将用户 '{current_user}' 添加到 docker 组（无需sudo运行docker）？"):
        run(f"usermod -aG docker {current_user}", needs_sudo=True)
        print("✓ 已添加用户到docker组")
        print("注意：需要重新登录或运行 'newgrp docker' 使权限生效")

print("\n" + "=" * 50)
print("安装完成！")
print("=" * 50)

# 显示Docker状态
print("\n📊 Docker 状态:")
os.system(f"{SUDO_PREFIX}systemctl status docker --no-pager | head -10")

# 显示Portainer状态
print("\n🐳 Portainer 状态:")
os.system(
    "docker ps --filter name=portainer --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
)

print("\n💡 提示:")
print("- 如果无法访问Portainer，请检查防火墙设置")
print("- 使用: sudo ufw allow 9443/tcp 开放端口")
print("- 测试: docker run hello-world")
