import os
import subprocess
import webbrowser

def run_command(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"警告: 命令执行失败 ({result.stderr.strip()})，但尝试继续...")
    print()

def install_astro():
    print("\n=== 正在安装 Astro (最新版) ===")
    print("Astro 是现代高性能静态站点生成器，支持 React/Vue/Svelte 等框架，内置优秀优化。")
    
    # 检查 Node.js
    node_check = subprocess.run("node -v", shell=True, capture_output=True)
    if node_check.returncode != 0:
        print("未检测到 Node.js！Astro 需要 Node.js LTS 版（推荐最新 LTS）。")
        print("当前推荐版本：从官网下载最新 LTS（长期支持至至少 2027 年）。")
        confirm = input("现在打开 Node.js 官网下载页面？(y/n，默认 y): ").strip().lower()
        if confirm != 'n':
            webbrowser.open("https://nodejs.org")
        print("请安装完成后重新运行本脚本。")
        return

    npm_check = subprocess.run("npm -v", shell=True, capture_output=True)
    if npm_check.returncode != 0:
        print("npm 未找到，请确认 Node.js 已正确安装。")
        return

    print("检测到 Node.js 和 npm，正在升级 npm 到最新版...")
    run_command("npm install -g npm@latest")

    print("\n=== 创建新 Astro 项目 ===")
    print("提示：在接下来的交互向导中，您将有机会：")
    print("  • 选择项目模板（推荐 Blog 或 Portfolio）")
    print("  • 强烈建议选择「Yes」安装 Tailwind CSS（现代实用类 CSS 框架）")
    print("  • 可选择使用 TypeScript（推荐 Strict 模式，提供更好类型安全）")
    print("  • 可直接从 Astro 官方/社区主题库选择主题作为起点")
    print("  • 建议选择「Yes」自动安装依赖")
    print()

    blog_name = input("输入新 Astro 项目文件夹名称 (默认 my-astro-site): ").strip() or "my-astro-site"
    
    if os.path.exists(blog_name):
        if os.listdir(blog_name):
            print(f"警告：文件夹 {blog_name} 已存在且不为空。")
            overwrite = input("是否继续使用此文件夹（会覆盖现有内容）？(y/n，默认 n): ").strip().lower()
            if overwrite != 'y':
                print("操作取消。请手动处理文件夹后重新运行脚本。")
                return
        else:
            print(f"使用现有空文件夹 {blog_name}")
    else:
        os.makedirs(blog_name)
        print(f"已创建文件夹 {blog_name}")

    original_dir = os.getcwd()
    os.chdir(blog_name)
    print(f"已进入项目目录: {os.getcwd()}")

    print("\n启动 Astro 官方创建向导（npm create astro@latest）...")
    print("请按照提示操作，重点关注上述推荐选项。")
    run_command("npm create astro@latest")

    # 如果用户在向导中选择了不安装依赖，手动补装
    if not os.path.exists("node_modules"):
        confirm_install = input("\n检测到依赖未安装，是否现在执行 npm install？(y/n，默认 y): ").strip().lower()
        if confirm_install != 'n':
            run_command("npm install")

    print(f"\nAstro 项目已创建在: {os.getcwd()}")
    print("\n快速启动开发服务器：")
    print("   npm run dev")
    print("   打开浏览器访问 http://localhost:4321 查看效果")
    print("\n构建生产版本：")
    print("   npm run build")
    print("   输出在 dist 文件夹，可直接部署到 Netlify、Vercel、GitHub Pages 等")

    # 主题教程
    print("\n=== Astro 主题选择教程 ===")
    print("Astro 官方主题库地址：https://astro.build/themes/")
    confirm = input("现在打开 Astro 官方主题库页面？(y/n，默认 y): ").strip().lower()
    if confirm != 'n':
        webbrowser.open("https://astro.build/themes/")
    
    print("\n推荐流行主题（直接使用以下命令重新创建项目即可使用主题）：")
    print("1. AstroPaper - 极简、快速、支持深色模式的博客主题（内置 Tailwind）")
    print("   npm create astro@latest -- --template satnaing/astro-paper")
    print()
    print("2. Astro Ink - 优雅现代的博客主题（内置 Tailwind）")
    print("   npm create astro@latest -- --template withastro/astro-ink")
    print()
    print("3. Nano Blog - 极简个人博客主题")
    print("   npm create astro@latest -- --template nanostores/nano-blog")
    print()
    print("更多主题请访问官方主题库选择并按照其说明安装。")

    # Tailwind CSS 组件推荐
    print("\n=== Tailwind CSS 组件库推荐 ===")
    print("如果您在创建时选择了安装 Tailwind CSS，可进一步添加预建组件库提升效率：")
    print()
    print("1. DaisyUI（最推荐）- 提供大量美观开箱即用组件")
    print("   在项目目录执行：")
    print("   npm install -D daisyui")
    print("   然后编辑 tailwind.config.mjs，添加：")
    print("   plugins: [require('daisyui')]")
    print()
    print("2. Flowbite - 另一套高质量组件")
    print("   npm install -D flowbite")
    print("   按照 Flowbite 官方文档配置")
    print()
    print("3. Headless UI + Tailwind UI（Tailwind 官方付费组件）")
    print("   适合追求极致一致性的项目")
    print()
    print("使用组件库后，只需引用类名即可快速构建界面，大幅提升开发速度。")

    os.chdir(original_dir)
    print("\n全部完成！推荐使用 VS Code + Astro 官方插件进行开发，支持实时预览和智能提示。")

def main():
    print("=" * 80)
    print("      Windows 一键安装 Astro 静态站点生成器（2026 版）")
    print("=" * 80)
    print("当前脚本更新日期: 2026 年 1 月 7 日")
    print("本脚本功能：")
    print("  - 检测并引导安装 Node.js（必需）")
    print("  - 创建全新的 Astro 项目（最新版）")
    print("  - 提供详细交互提示（Tailwind、TypeScript、主题选择）")
    print("  - 附带流行主题安装命令与 Tailwind 组件库推荐")
    print("")
    print("适用系统: Windows 10 / 11 (64 位)")
    print("开发推荐：VS Code + Astro 插件 + Front Matter CMS（Markdown 编辑增强）")
    print("部署推荐：Netlify / Vercel / GitHub Pages（一键绑定 Git 仓库自动构建）")
    print("=" * 80)

    confirm = input("\n是否开始安装 Astro？(y/n，默认 y): ").strip().lower()
    if confirm == 'n':
        print("操作已取消。")
        return

    install_astro()

    input("\n按 Enter 键退出脚本...")

if __name__ == "__main__":
    main()