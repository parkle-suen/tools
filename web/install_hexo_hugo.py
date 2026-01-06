#!/usr/bin/env python3

import os
import subprocess
import sys
import shutil
import platform
import urllib.request
import tarfile

def run_command(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"错误: 命令失败 ({cmd})")
        sys.exit(1)

def install_hugo():
    print("\n正在安装 Hugo（最新 extended 版）...")
    arch = platform.machine()
    if arch == 'x86_64':
        deb = "hugo_extended_0.152.2_linux-amd64.deb"
    elif arch == 'aarch64':
        deb = "hugo_extended_0.152.2_linux-arm64.deb"
    else:
        print(f"不支持的架构: {arch}")
        return

    url = f"https://github.com/gohugoio/hugo/releases/download/v0.152.2/{deb}"
    deb_path = "/tmp/" + deb

    print(f"下载: {url}")
    urllib.request.urlretrieve(url, deb_path)

    run_command(f"dpkg -i {deb_path}")
    os.remove(deb_path)

    print("Hugo 安装完成！")
    run_command("hugo version")

def install_hexo():
    print("\n正在安装 Hexo（最新 v8.1.1）...")
    print("前提：必须已安装最新 Node.js 和 npm（用之前的 Node.js 脚本安装）")
    run_command("node -v")  # 检查 Node.js
    run_command("npm -v")

    run_command("npm install -g hexo-cli@latest")

    print("Hexo 安装完成！")
    run_command("hexo version")

    print("\nHexo 使用建议：")
    print("  - 创建新博客: hexo init myblog && cd myblog && npm install")
    print("  - 本地预览: hexo server")
    print("  - 生成静态文件: hexo generate")

def main():
    print("=" * 70)
    print("          Ubuntu 安装 Hugo / Hexo 静态站点生成器脚本")
    print("=" * 70)
    print("本脚本功能：")
    print("  - 选择安装 Hugo（Go 语言，最快 SSG）或 Hexo（Node.js 博客框架）或两者")
    print("  - Hugo: 最新 v0.152.2 extended（支持 Sass、WebP 等）")
    print("  - Hexo: 最新 v8.1.1（需要先安装 Node.js）")
    print("  - 全局安装，命令行直接可用")
    print("")
    print("适用系统：Ubuntu 18.04+（64 位 amd64 或 arm64）")
    print("为什么在 Linux 上安装：")
    print("  - 本地/服务器预览、自动化 CI/CD 构建、性能更好")
    print("  - 即使你在 Windows 开发，服务器端也常需安装")
    print("")
    print("注意：")
    print("  - 需要 sudo 权限和网络")
    print("  - Hexo 需要先安装最新 Node.js（用之前的脚本）")
    print("=" * 70)

    choice = input("选择安装：1=Hugo, 2=Hexo, 3=两者 (默认 3): ").strip() or "3"

    if choice in ["1", "3"]:
        install_hugo()
    if choice in ["2", "3"]:
        install_hexo()

    print("\n安装完毕！享受静态博客开发吧~")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("错误: 请使用 sudo 运行此脚本！")
        sys.exit(1)
    main()