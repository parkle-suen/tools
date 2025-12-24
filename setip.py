#!/usr/bin/env python3

import os
import subprocess
import shutil
import netifaces

def run_command(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"错误: 命令失败 ({cmd})")
        exit(1)

def get_interfaces():
    interfaces = netifaces.interfaces()
    return [iface for iface in interfaces if iface != 'lo']

def backup_netplan():
    netplan_dir = "/etc/netplan/"
    for file in os.listdir(netplan_dir):
        if file.endswith(".yaml") or file.endswith(".yml"):
            src = os.path.join(netplan_dir, file)
            backup = src + ".bak"
            if not os.path.exists(backup):
                shutil.copy(src, backup)
                print(f"备份: {src} -> {backup}")

def generate_netplan(interface, ip, gateway, dns):
    config = f"""network:
  version: 2
  renderer: networkd
  ethernets:
    {interface}:
      dhcp4: false
      addresses:
        - {ip}
      routes:
        - to: default
          via: {gateway}
      nameservers:
        addresses: [{dns}]
"""
    netplan_file = "/etc/netplan/00-custom-config.yaml"
    with open(netplan_file, "w") as f:
        f.write(config)
    print(f"生成 Netplan 配置: {netplan_file}")
    print(config)

def set_proxy(proxy_http, proxy_https=None):
    if not proxy_http:
        return
    proxy_https = proxy_https or proxy_http

    env_lines = [
        f'http_proxy="{proxy_http}"',
        f"https_proxy="{proxy_https}"',
        'no_proxy="localhost,127.0.0.1,::1"'
    ]
    with open("/etc/environment", "a") as f:
        for line in env_lines:
            f.write("\n" + line)
    print("已添加代理到 /etc/environment")

    apt_proxy = f"""Acquire::http::Proxy "{proxy_http}";
Acquire::https::Proxy "{proxy_https}";
"""
    apt_file = "/etc/apt/apt.conf.d/95proxies"
    with open(apt_file, "w") as f:
        f.write(apt_proxy)
    print(f"已设置 apt 代理: {apt_file}")

def main():
    print("=" * 70)
    print("          Ubuntu 网络初始化脚本 - 设置静态 IP 和代理")
    print("=" * 70)
    print("本脚本功能：")
    print("  - 查看当前网络接口并帮助你选择一个")
    print("  - 可选：将网络从 DHCP（自动获取 IP）改为静态 IP（固定 IP）")
    print("  - 自动备份原有 Netplan 配置（.bak 文件，可手动恢复）")
    print("  - 生成新的 Netplan YAML 配置并立即应用")
    print("  - 测试网络连通性（ping 8.8.8.8）")
    print("  - 可选：设置系统级 HTTP/HTTPS 代理（影响 apt 和环境变量）")
    print("")
    print("适用系统：")
    print("  - Ubuntu 18.04 及以上版本（包括 Ubuntu Server 和 Desktop）")
    print("  - 使用 Netplan 管理的系统（大多数现代 Ubuntu）")
    print("  - 不适用于 Ubuntu 16.04 或其他发行版")
    print("")
    print("当前日期：2025 年 12 月（脚本无时间依赖）")
    print("注意事项：")
    print("  - 必须用 sudo 运行（root 权限）")
    print("  - 设置静态 IP 错误可能导致网络断开！请在有物理访问或控制台的环境中使用")
    print("  - 如果出错，可手动恢复备份：cp /etc/netplan/*.bak /etc/netplan/ && netplan apply")
    print("  - 脚本会覆盖自定义 Netplan 文件，但会先备份")
    print("=" * 70)

    confirm = input("是否继续运行脚本？(y/n，默认 y): ").strip().lower()
    if confirm == 'n':
        print("已取消")
        return

    print("\n当前网络接口:", get_interfaces())

    interface = input("输入要设置的网络接口 (默认第一个): ").strip()
    if not interface:
        interface = get_interfaces()[0]
    print(f"选择接口: {interface}")

    use_static = input("是否设置静态 IP? (y/n, 默认 y): ").strip().lower()
    if use_static != 'n':
        print("\n静态 IP 设置说明：")
        print("  - IP 地址格式示例：192.168.1.100/24 （/24 是子网掩码）")
        print("  - 网关通常是路由器 IP，如 192.168.1.1")
        print("  - DNS 可多个用逗号分隔，默认 Google DNS")
        ip = input("输入静态 IP (例如 192.168.1.100/24): ").strip()
        gateway = input("输入网关 (例如 192.168.1.1): ").strip()
        dns = input("输入 DNS (默认 8.8.8.8,8.8.4.4): ").strip()
        if not dns:
            dns = "8.8.8.8,8.8.4.4"

        backup_netplan()
        generate_netplan(interface, ip, gateway, dns)

        print("应用 Netplan 配置...")
        run_command("netplan apply")

        print("测试网络连通性...")
        run_command("ping -c 3 8.8.8.8")

    use_proxy = input("\n是否设置 HTTP/HTTPS 代理? (y/n, 默认 n): ").strip().lower()
    if use_proxy == 'y':
        print("\n代理设置说明：")
        print("  - 只需输入 http 代理地址，https 会自动同用")
        print("  - 示例：http://proxy.example.com:8080")
        proxy = input("输入代理地址: ").strip()
        set_proxy(proxy)

    print("\n初始化完成！建议重启系统使所有设置生效: sudo reboot")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("错误: 请使用 sudo 运行此脚本！")
        exit(1)
    main()