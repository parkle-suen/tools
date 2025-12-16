#!/usr/bin/env python3

import os
import subprocess
import sys
import shutil
import platform
import urllib.request
import tarfile
import json

def run_command(cmd):
    print(f"执行命令: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"错误: 命令执行失败 ({cmd})")
        sys.exit(1)

def get_latest_lts_version():
    print("正在从 Node.js 官网获取最新的 LTS 版本信息...")
    try:
        with urllib.request.urlopen("https://nodejs.org/dist/index.json") as response:
            data = json.loads(response.read().decode())
        for release in data:
            if release['lts'] != False:  # 找到最新的 LTS
                version = release['version']  # 如 v24.12.0
                print(f"检测到最新的 LTS 版本: {version}")
                return version.lstrip('v')
        print("警告: 未找到 LTS 版本，将使用最新 Current 版本")
        return data[0]['version'].lstrip('v')
    except Exception as e:
        print(f"错误: 获取版本失败 ({e})，请检查网络")
        sys.exit(1)

def main():
    print("=" * 60)
    print("        Ubuntu 安装最新 Node.js LTS 版本脚本")
    print("=" * 60)
    print("本脚本功能：")
    print("  - 从 Node.js 官方网站直接下载并安装最新的 LTS（长期支持）版本")
    print("  - 不使用 apt，避免安装 Ubuntu 仓库中过时的旧版本（通常只有 12.x~18.x）")
    print("  - 当前日期: 2025 年 12 月（最新 LTS 为 v24.x 系列，支持到 2028 年）")
    print("  - 安装内容: Node.js + npm + corepack")
    print("  - 安装位置: /usr/local/ (全局可用)")
    print("  - 适用系统: Ubuntu 18.04+ (64 位 x64 架构)，也支持其他 Debian 系统")
    print("  - 注意: 需要 root 权限运行，且必须有网络连接")
    print("  - 如果你是 ARM64 架构（如某些云服务器），脚本会提示")
    print("=" * 60)

    confirm = input("是否继续安装？(y/n，默认 y): ").strip().lower()
    if confirm == 'n':
        print("已取消安装")
        sys.exit(0)

    # 检查架构
    arch = platform.machine()
    if arch != 'x86_64':
        print(f"警告: 检测到架构 {arch}，本脚本默认支持 x86_64")
        print("如果您是 aarch64 (ARM64)，请手动修改脚本中的 'linux-x64' 为 'linux-arm64'")
        confirm_arch = input("是否继续？(y/n): ").strip().lower()
        if confirm_arch == 'n':
            sys.exit(0)

    # 获取最新 LTS 版本
    version = get_latest_lts_version()
    full_version = f"v{version}"

    # 下载地址
    tar_name = f"node-{full_version}-linux-x64.tar.xz"
    download_url = f"https://nodejs.org/dist/{full_version}/{tar_name}"
    tmp_dir = "/tmp/nodejs_install"

    print(f"准备下载: {download_url}")

    # 创建临时目录
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    # 下载
    tar_path = os.path.join(tmp_dir, tar_name)
    print("正在下载 Node.js 二进制包（约 50MB，请耐心等待...）")
    try:
        urllib.request.urlretrieve(download_url, tar_path)
    except Exception as e:
        print(f"下载失败: {e}")
        sys.exit(1)

    # 解压到 /usr/local
    print("正在解压并安装到 /usr/local ...")
    try:
        with tarfile.open(tar_path, "r:xz") as tar:
            tar.extractall(path="/usr/local", members=[m for m in tar.getmembers() if m.name.startswith(f"node-{full_version}-linux-x64/")])
        # 移动内容并重命名目录
        extracted_dir = f"/usr/local/node-{full_version}-linux-x64"
        for item in os.listdir(extracted_dir):
            shutil.move(os.path.join(extracted_dir, item), "/usr/local/")
        os.rmdir(extracted_dir)
    except Exception as e:
        print(f"安装失败: {e}")
        sys.exit(1)

    # 清理临时文件
    shutil.rmtree(tmp_dir)

    print("安装完成！")
    print(f"Node.js 版本: {full_version}")
    print("验证安装:")
    run_command("node -v")
    run_command("npm -v")

    print("\n建议：")
    print("  - 重启终端或运行 'source /etc/profile' 使环境变量生效")
    print("  - 测试: node -e \"console.log('Hello Node.js!')\"")
    print("  - 卸载方法: sudo rm -rf /usr/local/bin/node /usr/local/bin/npm /usr/local/bin/npx /usr/local/include/node /usr/local/lib/node_modules /usr/local/share/man/man1/node*")
    print("安装完毕！享受最新 Node.js 吧~")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("错误: 请使用 sudo 运行此脚本！")
        sys.exit(1)
    main()