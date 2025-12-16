#!/usr/bin/env python3
# gpg_tutorial.py
# 一个交互式的 GPG 配置与使用教程脚本（Rich 美化版）
# 作者: Grok 定制
# 依赖: pip install rich
# 运行: python3 gpg_tutorial.py

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
import platform

console = Console()

def print_header(text):
    console.rule(f"[bold cyan]{text}[/bold cyan]", style="cyan")

def main_menu():
    table = Table(title="GPG 完整交互教程", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("选项", style="bold white", width=5)
    table.add_column("描述", style="bold white")

    table.add_row("1", "生成你的 GPG 密钥对（推荐 ed25519）")
    table.add_row("2", "备份与安全管理私钥/子密钥")
    table.add_row("3", "上传公钥到密钥服务器（让别人能找到你）")
    table.add_row("4", "导入他人公钥并签名（建立信任）")
    table.add_row("5", "加密、解密、签名、验证文件或文本")
    table.add_row("6", "在 Git 中使用 GPG 签名 commit/tag")
    table.add_row("0", "[bold red]退出教程[/bold red]")

    console.print(Panel(table, style="cyan"))

def section_1():
    print_header("1. 生成你的 GPG 密钥对（推荐 ed25519）")

    console.print(Markdown("""
现代 GPG 推荐使用 **ed25519** 主密钥（签名） + **cv25519** 子密钥（加密），更安全、更快。

### 生成命令（一步到位）：
"""))
    console.print(Panel("""
gpg --full-generate-key
""".strip(), title="运行生成向导", style="magenta"))

    console.print(Markdown("""
向导中建议选择：
- 种类：`(1) RSA and RSA` → 改为 `(4) ECC and ECC`（如果支持）
- 曲线：`ed25519`（主密钥，用于签名）
- 子密钥曲线：`cv25519`（加密） + `ed25519`（签名）
- 密钥有效期：建议 **2y**（2年），到期前可续期
- Real name / Email / Comment：填写真实信息（尤其是 GitHub 用的邮箱）
- Passphrase：**强烈建议设置强密码短语**（私钥唯一保护）
"""))

    console.print("[bold green]✓ 生成完成后，你会有：[/bold green]")
    console.print("  • 主密钥（Master Key）：用于认证")
    console.print("  • 子密钥：签名（S）、加密（E）、认证（A）\n")

    console.print(Panel("[magenta]$ gpg --list-keys --keyid-format LONG[/magenta]", 
                        title="查看你的密钥", style="magenta"))

def section_2():
    print_header("2. 备份与安全管理私钥/子密钥")

    console.print("[bold red]✗ 私钥丢失 = 永久无法解密/证明身份！备份是重中之重[/bold red]")

    console.print(Markdown("""
### 导出完整私钥（含主密钥，用于灾难恢复）：
"""))
    console.print(Panel("""
gpg --export-secret-keys --armor YOUR_KEY_ID > my-master-key.asc
gpg --export-secret-subkeys --armor YOUR_KEY_ID > my-subkeys.asc
""".strip(), title="导出命令", style="magenta"))

    console.print(Markdown("""
- 打印到纸质备份（推荐）
- 存到加密 U 盘或离线存储
- **绝不要上传到云盘或邮箱**

### 安全转移到新电脑（推荐只转移子密钥，主密钥离线）：
1. 在旧电脑导出子密钥
2. 在新电脑导入子密钥
3. 删除旧电脑子密钥（可选）
"""))

    console.print("[bold yellow]⚠ 主密钥建议离线保存，只保留子密钥日常使用[/bold yellow]")

def section_3():
    print_header("3. 上传公钥到密钥服务器")

    console.print(Markdown("""
让别人能通过你的邮箱或 Key ID 找到你的公钥（GitHub 验证也需要）
"""))

    console.print(Panel("""
gpg --keyserver hkps://keys.openpgp.org --send-keys YOUR_KEY_ID
""".strip(), title="上传公钥", style="magenta"))

    console.print(Markdown("""
常用密钥服务器：
- hkps://keys.openpgp.org（推荐，验证邮箱）
- hkps://keyserver.ubuntu.com
- hkps://pgp.mit.edu

上传后，别人可以用：
"""))
    console.print(Panel("""
gpg --keyserver hkps://keys.openpgp.org --recv-keys YOUR_KEY_ID
# 或直接用邮箱搜索（keys.openpgp.org 支持）
""".strip(), title="他人获取你的公钥", style="magenta"))

def section_4():
    print_header("4. 导入他人公钥并签名（建立信任）")

    console.print(Markdown("""
### 导入他人公钥：
"""))
    console.print(Panel("""
gpg --recv-keys THEIR_KEY_ID
# 或从文件导入
gpg --import their-public-key.asc
""".strip(), style="magenta"))

    console.print(Markdown("""
### 签名他人公钥（表示你信任他）：
"""))
    console.print(Panel("""
gpg --sign-key THEIR_KEY_ID
# 或者本地信任（不上传）
gpg --edit-key THEIR_KEY_ID
> trust
> 5 (ultimate trust)
> quit
""".strip(), title="签名与信任", style="magenta"))

    console.print("[bold green]✓ 签名后可上传，让信任链传播[/bold green]")

def section_5():
    print_header("5. 加密、解密、签名、验证")

    table = Table(box=box.SIMPLE_HEAVY, title="常用操作一览")
    table.add_column("操作", style="bold cyan")
    table.add_column("命令", style="bold magenta")
    table.add_column("说明", style="bold yellow")

    table.add_row("加密文件（给某人）", "gpg -e -r THEIR_EMAIL file.txt", "生成 file.txt.gpg")
    table.add_row("解密文件", "gpg -d file.txt.gpg > file.txt", "会提示 passphrase")
    table.add_row("签名文件（分离签名）", "gpg --detach-sign --armor file.txt", "生成 file.txt.asc")
    table.add_row("签名并加密", "gpg -se -r THEIR_EMAIL file.txt", "同时签名+加密")
    table.add_row("验证分离签名", "gpg --verify file.txt.asc file.txt", "检查是否篡改")
    table.add_row("清签文本（可读）", "gpg --clearsign file.txt", "生成 file.txt.asc（带文本）")

    console.print(table)

def section_6():
    print_header("6. 在 Git 中使用 GPG 签名 commit 和 tag")

    console.print(Markdown("""
GitHub/GitLab 会显示 Verified 标志，证明是你提交的
"""))

    console.print(Panel("""
# 1. 查看你的签名密钥 ID
gpg --list-secret-keys --keyid-format LONG

# 2. 配置 Git（替换 YOUR_KEY_ID）
git config --global user.signingkey YOUR_KEY_ID
git config --global gpg.program gpg

# 3. 开启自动签名所有 commit
git config --global commit.gpgsign true

# 4. 签名 tag（推荐）
git tag -s v1.0 -m "Release 1.0"
""".strip(), title="Git 配置步骤", style="magenta"))

    console.print("[bold green]✓ 之后 push 到 GitHub，commit/tag 会显示 Verified 徽章[/bold green]")

# === 主程序 ===
console.print(Panel("[bold yellow]欢迎使用 GPG 完整交互教程！[/bold yellow]\n从生成密钥到 Git 签名，一步步带你掌握现代 GPG 使用 🚀\n安全第一：请为私钥设置强 passphrase！", 
                    style="bold yellow"))

while True:
    main_menu()
    choice = console.input("[bold green]\n请输入选项编号 (0-6): [/bold green]").strip()

    if choice == "1":
        section_1()
    elif choice == "2":
        section_2()
    elif choice == "3":
        section_3()
    elif choice == "4":
        section_4()
    elif choice == "5":
        section_5()
    elif choice == "6":
        section_6()
    elif choice == "0":
        console.print(Panel("[bold green]教程结束，祝你玩转 GPG！保持密钥安全 🔒[/bold green]", style="green"))
        break
    else:
        console.print("[bold red]✗ 无效选项，请重新输入！[/bold red]")

    console.input("[cyan]\n按回车键继续...[/cyan]")