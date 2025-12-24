import os
import subprocess
import sys
import webbrowser

def run_command(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"警告: 命令执行失败 ({result.stderr.strip()})，但尝试继续...")
    print()

def install_hugo():
    print("\n=== 正在安装 Hugo (最新 extended 版) ===")
    print("使用 Microsoft 官方 winget 包管理器安装（最简单、无需额外工具）")
    
    # 检查 winget 是否可用
    winget_check = subprocess.run("winget --version", shell=True, capture_output=True)
    if winget_check.returncode != 0:
        print("未检测到 winget！winget 是 Windows 10/11 内置包管理器。")
        print("解决方案：")
        print("1. 打开 Microsoft Store，搜索 'App Installer' 并更新（winget 随它附带）。")
        print("2. 或手动从 GitHub 下载最新版：https://github.com/microsoft/winget-cli/releases")
        confirm = input("现在打开 Microsoft Store？(y/n，默认 y): ").strip().lower()
        if confirm != 'n':
            webbrowser.open("ms-windows-store://pdp/?productid=9NBLGGH4NNS1")
        print("更新完成后重新运行本脚本。")
        return
    
    # 安装 Hugo extended
    run_command("winget install --id Hugo.Hugo.Extended -e")
    print("Hugo 安装完成！")
    run_command("hugo version")

def install_hexo():
    print("\n=== 正在安装 Hexo (最新 v8.1.0) ===")
    # 检查 Node.js
    node_check = subprocess.run("node -v", shell=True, capture_output=True)
    if node_check.returncode != 0:
        print("未检测到 Node.js！Hexo 需要 Node.js LTS 版。")
        print("推荐下载最新 LTS (v24.x)：支持到 2028 年。")
        confirm = input("现在打开 Node.js 官网下载页面？(y/n，默认 y): ").strip().lower()
        if confirm != 'n':
            webbrowser.open("https://nodejs.org")
        print("请安装完成后重新运行本脚本。")
        return

    npm_check = subprocess.run("npm -v", shell=True, capture_output=True)
    if npm_check.returncode != 0:
        print("npm 未找到，请先安装 Node.js。")
        return

    print("检测到 Node.js 和 npm，正在升级 npm 并安装 Hexo...")
    run_command("npm install -g npm@latest")
    run_command("npm install -g hexo-cli@latest")
    print("Hexo 安装完成！")
    run_command("hexo version")

    print("\nHexo 快速开始建议：")
    blog_name = input("输入新博客文件夹名称 (默认 myblog): ").strip() or "myblog"
    if os.path.exists(blog_name):
        print(f"文件夹 {blog_name} 已存在，跳过创建。")
    else:
        run_command(f"hexo init {blog_name}")
        os.chdir(blog_name)
        run_command("npm install")
        print(f"博客已创建在: {os.getcwd()}")
    print("使用: hexo new '文章标题' → hexo server (预览) → hexo generate")

def main():
    print("=" * 70)
    print("      Windows 一键安装 Hugo / Hexo 静态站点生成器（winget 版）")
    print("=" * 70)
    print("当前日期: 2025 年 12 月 16 日")
    print("本脚本功能：")
    print("  - 选择安装 Hugo（最快 SSG）或 Hexo（Node.js 博客框架）或两者")
    print("  - Hugo: 最新 extended 版 (用 Microsoft winget 安装，最简单)")
    print("  - Hexo: 最新 v8.1.0 (需先安装 Node.js LTS v24.x)")
    print("")
    print("适用系统: Windows 10 / 11 (64 位)")
    print("为什么在 Windows 开发：")
    print("  - VS Code + 插件实时预览超爽（推荐 Front Matter CMS）")
    print("  - 部署时用 GitHub Actions / Gitea Actions 自动构建")
    print("")
    print("注意事项：")
    print("  - winget 在大多数 Windows 10/11 已内置")
    print("  - 如果 winget 未找到，脚本会引导更新 App Installer")
    print("  - Node.js 请手动从官网下载安装")
    print("=" * 70)

    choice = input("\n选择安装：1=Hugo, 2=Hexo, 3=两者 (默认 3): ").strip() or "3"

    if choice in ["1", "3"]:
        install_hugo()
    if choice in ["2", "3"]:
        install_hexo()

    print("\n全部完成！建议安装 VS Code + Front Matter 插件，实时预览更爽~")
    input("按 Enter 退出...")

if __name__ == "__main__":
    main()