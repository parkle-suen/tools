#!/usr/bin/env python3
# ssh_tutorial.py
# 一个交互式的 SSH 配置教程脚本（Rich 美化版）
# 作者: Grok 定制
# 依赖: pip install rich

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
import platform
import os

console = Console()

def print_header(text):
    console.rule(f"[bold cyan]{text}[/bold cyan]", style="cyan")

def main_menu():
    table = Table(title="SSH 配置完整交互教程", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("选项", style="bold white", width=5)
    table.add_column("描述", style="bold white")

    table.add_row("1", "创建 SSH Key 并保存到 .ssh 目录（Windows / Linux / macOS）")
    table.add_row("2", "将公钥添加到 authorized_keys（实现免密码登录服务器）")
    table.add_row("3", "私钥管理：修改权限、添加到 ssh-agent 等高级操作")
    table.add_row("0", "[bold red]退出教程[/bold red]")

    console.print(Panel(table, style="cyan"))

def section_1():
    print_header("1. 创建 SSH Key 并保存到 .ssh 目录")
    
    system = platform.system()
    if system == "Windows":
        console.print("[bold yellow]⚠ Windows 系统推荐使用 OpenSSH（Win10/11 自带）或 Git Bash[/bold yellow]")
        console.print("推荐使用 ed25519 类型（更安全、更快）\n")
    else:
        console.print("[bold green]✓ Linux / macOS 操作完全一致[/bold green]\n")

    cmd = """ssh-keygen -t ed25519 -C "你的邮箱@example.com\""""
    console.print(Panel(f"[bold magenta]$ {cmd}[/bold magenta]", title="推荐命令", style="magenta"))

    console.print(Markdown("""
- 直接回车使用默认路径：`~/.ssh/id_ed25519`
- passphrase（密码）**建议留空**（直接回车两次）→ 实现完全免密码
    """))

    console.print("[bold green]✓ 生成后会得到两个文件：[/bold green]")
    console.print("  • [bold red]id_ed25519[/bold red]      → 私钥（绝对保密！）")
    console.print("  • [bold green]id_ed25519.pub[/bold green]  → 公钥（可以分享）\n")

    console.print(Panel("[magenta]$ ls -la ~/.ssh/[/magenta]", title="检查文件", style="magenta"))
    console.print("[bold yellow]⚠ 私钥权限必须是 600！（后面会教怎么改）[/bold yellow]")

def section_2():
    print_header("2. 将公钥添加到服务器的 authorized_keys（实现免密码登录）")

    console.print(Markdown("""
### 详细步骤（最后一次用密码登录服务器）：

1. 本地复制公钥内容  
   `[magenta]$ cat ~/.ssh/id_ed25519.pub[/magenta]`  
   （Windows 可使用 `clip < ~/.ssh/id_ed25519.pub` 直接复制到剪贴板）

2. 登录服务器（最后一次输入密码）  
   `[magenta]$ ssh user@server-ip[/magenta]`

3. 在服务器上创建目录并设置权限
"""))
    console.print(Panel("$ mkdir -p ~/.ssh\n$ chmod 700 ~/.ssh", style="magenta", title="创建 .ssh 目录"))

    console.print(Markdown("""
4. 添加公钥到 authorized_keys  
   使用编辑器粘贴（推荐）：
"""))
    console.print(Panel("$ nano ~/.ssh/authorized_keys", title="编辑文件并粘贴公钥", style="magenta"))

    console.print(Panel("$ chmod 600 ~/.ssh/authorized_keys", title="设置文件权限（关键！）", style="red"))

    console.print("\n[bold green]✓ 大功告成！退出后重新连接应直接登录，无需密码！[/bold green]")

def section_3():
    print_header("3. 私钥管理：权限、ssh-agent 等高级操作")

    console.print("[bold red]✗ 私钥权限不对是 SSH 最常见的报错！必须严格 600[/bold red]")

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("操作", style="bold cyan")
    table.add_column("命令", style="bold magenta")
    table.add_column("说明", style="bold yellow")

    table.add_row("修改私钥权限", "chmod 600 ~/.ssh/id_ed25519", "必须！否则拒绝加载")
    table.add_row("修改目录权限", "chmod 700 ~/.ssh", "目录也要严格权限")
    table.add_row("检查权限", "ls -la ~/.ssh/", "私钥应显示 -rw-------")

    console.print(table)

    console.print(Markdown("\n### 添加到 ssh-agent（避免重复输入 passphrase）\n"))
    console.print(Panel("$ eval \"$(ssh-agent -s)\"\n$ ssh-add ~/.ssh/id_ed25519", 
                        title="添加私钥到 agent（只需输入一次 passphrase）", style="magenta"))
    
    console.print("[bold green]✓ 添加成功后，该终端会话内所有 ssh/scp/git 操作都免输密码[/bold green]")

# === 主程序 ===
console.print(Panel("[bold yellow]欢迎使用 SSH 配置交互教程！[/bold yellow]\n这个脚本将带你一步步掌握 SSH 免密码登录，界面更美观、内容更清晰 🚀", 
                    style="bold yellow"))

while True:
    main_menu()
    choice = console.input("[bold green]\n请输入选项编号 (0-3): [/bold green]").strip()

    if choice == "1":
        section_1()
    elif choice == "2":
        section_2()
    elif choice == "3":
        section_3()
    elif choice == "0":
        console.print(Panel("[bold green]教程结束，祝你 SSH 配置顺利！再见！🚀[/bold green]", style="green"))
        break
    else:
        console.print("[bold red]✗ 无效选项，请重新输入！[/bold red]")

    console.input("[cyan]\n按回车键继续...[/cyan]")