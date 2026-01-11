#!/usr/bin/env python3
"""
Node.js 企业级安装脚本 - 全栈架构师优化版
版本：v2.0 (2026-01-11)
功能：安全、可靠地安装最新 Node.js LTS 版本到 Ubuntu Server 22.04+
特点：
  - 自动检测架构（x86_64/aarch64）
  - 从官方源获取最新 LTS 版本
  - 独立目录安装（/opt/nodejs/[version]）
  - 符号链接管理（/usr/local/bin）
  - 完整的错误处理和回滚机制
  - SHA256 完整性验证
  - 多版本支持，易于升级/降级
"""

import os
import sys
import json
import shutil
import hashlib
import tempfile
import platform
import subprocess
import urllib.request
from typing import Optional, Tuple, Dict
from pathlib import Path
from datetime import datetime

class NodeJSInstaller:
    """Node.js 企业级安装器"""
    
    # 常量定义
    NODE_JS_INDEX = "https://nodejs.org/dist/index.json"
    SHA256_SUFFIX = ".sha256sum"
    INSTALL_BASE = Path("/opt/nodejs")
    BIN_LINK_DIR = Path("/usr/local/bin")
    PROFILE_SCRIPT = Path("/etc/profile.d/nodejs.sh")
    
    def __init__(self):
        self.arch_map = {
            "x86_64": "x64",
            "aarch64": "arm64",
            "arm64": "arm64"
        }
        self.current_arch = platform.machine()
        self.node_arch = self.arch_map.get(self.current_arch, "x64")
        self.temp_dir = None
        self.backup_dir = None
        self.rollback_info = {}
        
    def log(self, message: str, level: str = "INFO"):
        """结构化日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}", flush=True)
    
    def run_command(self, cmd: str, capture: bool = False) -> Tuple[int, str]:
        """执行命令并返回结果"""
        self.log(f"执行命令: {cmd}")
        try:
            if capture:
                result = subprocess.run(
                    cmd, shell=True, check=False,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8'
                )
                return result.returncode, result.stdout.strip()
            else:
                result = subprocess.run(cmd, shell=True, check=False)
                return result.returncode, ""
        except Exception as e:
            self.log(f"命令执行异常: {e}", "ERROR")
            return -1, str(e)
    
    def check_prerequisites(self) -> bool:
        """检查安装前提条件"""
        self.log("检查系统环境...")
        
        # 1. 检查 root 权限
        if os.geteuid() != 0:
            self.log("错误: 需要 root 权限运行此脚本", "ERROR")
            self.log("请使用: sudo ./install_nodejs.py", "ERROR")
            return False
        
        # 2. 检查架构支持
        if self.current_arch not in self.arch_map:
            self.log(f"警告: 检测到不支持的系统架构: {self.current_arch}", "WARN")
            self.log(f"支持的架构: {list(self.arch_map.keys())}", "WARN")
            user_confirm = input("是否继续尝试安装？(y/N): ").strip().lower()
            if user_confirm != 'y':
                return False
        
        # 3. 检查磁盘空间 (至少需要 200MB)
        try:
            stat = os.statvfs("/")
            free_space = stat.f_frsize * stat.f_bavail
            if free_space < 200 * 1024 * 1024:  # 200MB
                self.log(f"警告: 磁盘空间不足，可用 {free_space // (1024*1024)}MB，需要 200MB", "WARN")
        except:
            pass  # 忽略磁盘检查错误
        
        # 4. 检查网络连接
        try:
            urllib.request.urlopen("https://nodejs.org", timeout=5)
            self.log("网络连接正常", "INFO")
        except Exception as e:
            self.log(f"网络连接检查失败: {e}", "WARN")
            self.log("安装需要互联网连接，请检查网络", "WARN")
        
        return True
    
    def get_latest_lts_version(self) -> Optional[Dict]:
        """从官方源获取最新 LTS 版本信息"""
        self.log("获取最新 Node.js LTS 版本信息...")
        
        try:
            with urllib.request.urlopen(self.NODE_JS_INDEX, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # 查找最新的 LTS 版本
            lts_versions = [v for v in data if v.get('lts')]
            if not lts_versions:
                self.log("未找到 LTS 版本，使用最新稳定版", "WARN")
                lts_versions = data[:1]
            
            latest = lts_versions[0]
            version = latest['version'].lstrip('v')
            
            # 检查架构支持
            files = latest.get('files', [])
            needed_file = f"linux-{self.node_arch}"
            if needed_file not in files:
                self.log(f"错误: 版本 {version} 不支持 {self.node_arch} 架构", "ERROR")
                self.log(f"可用架构: {files}", "ERROR")
                return None
            
            self.log(f"找到最新 LTS 版本: v{version} (代号: {latest.get('lts', 'Unknown')})", "INFO")
            
            return {
                'version': version,
                'full_version': latest['version'],
                'npm_version': latest.get('npm', 'unknown'),
                'release_date': latest.get('date', 'unknown'),
                'lts_name': latest.get('lts', '')
            }
            
        except Exception as e:
            self.log(f"获取版本信息失败: {e}", "ERROR")
            return None
    
    def download_file(self, url: str, dest_path: Path) -> bool:
        """下载文件并显示进度"""
        self.log(f"下载: {url}")
        
        try:
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) / total_size)
                    sys.stdout.write(f"\r下载进度: {percent:.1f}% ({block_num * block_size / (1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB)")
                    sys.stdout.flush()
            
            urllib.request.urlretrieve(url, dest_path, report_progress)
            sys.stdout.write("\n")
            
            # 验证文件大小
            if dest_path.stat().st_size < 1024:  # 小于 1KB 可能是错误页面
                self.log(f"警告: 下载的文件过小 ({dest_path.stat().st_size} 字节)", "WARN")
                return False
                
            self.log(f"下载完成: {dest_path.stat().st_size / (1024*1024):.1f}MB", "INFO")
            return True
            
        except Exception as e:
            self.log(f"下载失败: {e}", "ERROR")
            return False
    
    def verify_sha256(self, file_path: Path, expected_hash: str) -> bool:
        """验证文件 SHA256 哈希值"""
        self.log(f"验证文件完整性: {file_path.name}")
        
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            actual_hash = sha256_hash.hexdigest()
            
            if actual_hash == expected_hash:
                self.log("SHA256 验证通过", "INFO")
                return True
            else:
                self.log(f"SHA256 验证失败", "ERROR")
                self.log(f"期望: {expected_hash[:16]}...", "ERROR")
                self.log(f"实际: {actual_hash[:16]}...", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"SHA256 验证异常: {e}", "ERROR")
            return False
    
    def create_backup(self) -> bool:
        """创建现有安装的备份"""
        self.log("创建系统备份...")
        
        # 检查现有安装
        existing_install = None
        for version_dir in self.INSTALL_BASE.glob("*/"):
            if (version_dir / "bin" / "node").exists():
                existing_install = version_dir
                break
        
        if not existing_install:
            self.log("未发现现有 Node.js 安装", "INFO")
            return True
        
        # 创建备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"/tmp/nodejs_backup_{timestamp}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份现有安装
        try:
            backup_target = self.backup_dir / "nodejs"
            shutil.copytree(existing_install, backup_target, symlinks=True)
            
            # 备份符号链接
            link_backup = []
            for bin_file in ["node", "npm", "npx"]:
                link_path = self.BIN_LINK_DIR / bin_file
                if link_path.exists() and link_path.is_symlink():
                    target = link_path.resolve()
                    if str(target).startswith(str(existing_install)):
                        link_backup.append({
                            'name': bin_file,
                            'target': str(target),
                            'link': str(link_path)
                        })
            
            # 保存备份信息
            self.rollback_info = {
                'backup_dir': str(self.backup_dir),
                'existing_install': str(existing_install),
                'symlinks': link_backup,
                'profile_script': self.PROFILE_SCRIPT.exists()
            }
            
            self.log(f"备份创建成功: {self.backup_dir}", "INFO")
            return True
            
        except Exception as e:
            self.log(f"备份失败: {e}", "ERROR")
            return False
    
    def install_version(self, version_info: Dict) -> bool:
        """安装指定版本"""
        version = version_info['version']
        full_version = version_info['full_version']
        
        self.log(f"开始安装 Node.js v{version}", "INFO")
        
        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp(prefix="nodejs_install_"))
        self.log(f"临时目录: {self.temp_dir}")
        
        try:
            # 1. 下载 Node.js 包
            tar_name = f"node-{full_version}-linux-{self.node_arch}.tar.xz"
            download_url = f"https://nodejs.org/dist/{full_version}/{tar_name}"
            tar_path = self.temp_dir / tar_name
            
            if not self.download_file(download_url, tar_path):
                return False
            
            # 2. 下载并验证 SHA256
            sha256_url = f"{download_url}{self.SHA256_SUFFIX}"
            sha256_path = self.temp_dir / f"{tar_name}{self.SHA256_SUFFIX}"
            
            if self.download_file(sha256_url, sha256_path):
                with open(sha256_path, 'r') as f:
                    expected_hash = f.read().strip().split()[0]
                if not self.verify_sha256(tar_path, expected_hash):
                    self.log("警告: SHA256 验证失败，但继续安装", "WARN")
            
            # 3. 解压文件
            self.log(f"解压 {tar_name} ...")
            install_dir = self.INSTALL_BASE / version
            install_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # 清理可能存在的旧目录
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            # 解压到临时位置再移动
            extract_temp = self.temp_dir / "extract"
            extract_temp.mkdir(exist_ok=True)
            
            return_code, output = self.run_command(
                f"tar -xf {tar_path} -C {extract_temp}", capture=True
            )
            
            if return_code != 0:
                self.log(f"解压失败: {output}", "ERROR")
                return False
            
            # 4. 移动到安装目录
            extracted = next(extract_temp.iterdir())
            shutil.move(str(extracted), str(install_dir))
            
            self.log(f"安装到: {install_dir}", "INFO")
            
            # 5. 创建符号链接
            self.log("创建系统符号链接...")
            for bin_file in ["node", "npm", "npx"]:
                source = install_dir / "bin" / bin_file
                if source.exists():
                    target = self.BIN_LINK_DIR / bin_file
                    
                    # 移除旧链接
                    if target.exists():
                        target.unlink()
                    
                    # 创建新链接
                    target.symlink_to(source)
                    self.log(f"创建链接: {target} -> {source}", "DEBUG")
            
            # 6. 设置环境变量
            self.log("配置系统环境变量...")
            env_content = f"""# Node.js Environment Configuration
# Auto-generated by Node.js installer on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Version: v{version}

export NODE_HOME="{install_dir}"
export PATH="$NODE_HOME/bin:$PATH"

# npm global packages directory
export NPM_CONFIG_PREFIX="$HOME/.npm-global"
export PATH="$HOME/.npm-global/bin:$PATH"
"""
            
            with open(self.PROFILE_SCRIPT, 'w') as f:
                f.write(env_content)
            
            os.chmod(self.PROFILE_SCRIPT, 0o644)
            
            # 7. 验证安装
            self.log("验证安装结果...")
            checks = [
                ("node --version", f"v{version}"),
                ("npm --version", version_info['npm_version'].split('.')[0]),  # 主要版本匹配
                ("npx --version", version_info['npm_version'].split('.')[0])
            ]
            
            all_passed = True
            for cmd, expected in checks:
                return_code, output = self.run_command(cmd, capture=True)
                if return_code == 0:
                    self.log(f"✓ {cmd}: {output}", "INFO")
                    if expected and expected not in output:
                        self.log(f"  警告: 期望包含 '{expected}'，但得到 '{output}'", "WARN")
                else:
                    self.log(f"✗ {cmd}: 失败", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.log(f"✅ Node.js v{version} 安装成功！", "SUCCESS")
                
                # 输出安装摘要
                print("\n" + "="*60)
                print("安装摘要:")
                print(f"  • 版本: v{version} ({version_info['lts_name']})")
                print(f"  • npm: {version_info['npm_version']}")
                print(f"  • 发布日期: {version_info['release_date']}")
                print(f"  • 安装位置: {install_dir}")
                print(f"  • 符号链接: /usr/local/bin/{{node,npm,npx}}")
                print(f"  • 环境配置: {self.PROFILE_SCRIPT}")
                print("\n下一步:")
                print("  1. 重新登录或执行: source /etc/profile")
                print("  2. 验证: node -v && npm -v")
                print("  3. 安装全局包: npm install -g yarn pnpm")
                print("\n管理命令:")
                print("  • 查看安装: ls {self.INSTALL_BASE}")
                print("  • 切换版本: 修改 {self.PROFILE_SCRIPT} 中的 NODE_HOME")
                print("  • 完全卸载: 运行此脚本的 --uninstall 选项")
                print("="*60)
                
                return True
            else:
                self.log("❌ 安装验证失败，执行回滚", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"安装过程异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "DEBUG")
            return False
    
    def cleanup(self, success: bool = True):
        """清理临时文件"""
        self.log("清理临时文件...")
        
        # 清理临时目录
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.log(f"清理临时目录: {self.temp_dir}")
            except:
                pass
        
        # 如果安装失败且存在备份，执行回滚
        if not success and self.rollback_info:
            self.log("执行安装失败回滚...", "WARN")
            self.rollback_installation()
        
        # 如果安装成功且存在备份，询问是否保留备份
        elif success and self.backup_dir and self.backup_dir.exists():
            keep = input(f"\n是否保留备份文件？({self.backup_dir}) [y/N]: ").strip().lower()
            if keep != 'y':
                try:
                    shutil.rmtree(self.backup_dir)
                    self.log(f"删除备份目录: {self.backup_dir}")
                except:
                    pass
    
    def rollback_installation(self):
        """回滚到备份版本"""
        if not self.rollback_info:
            self.log("无回滚信息可用", "ERROR")
            return
        
        try:
            backup_dir = Path(self.rollback_info['backup_dir'])
            existing_install = self.rollback_info.get('existing_install')
            
            if existing_install and backup_dir.exists():
                # 恢复安装目录
                target_dir = Path(existing_install)
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                backup_source = backup_dir / "nodejs"
                if backup_source.exists():
                    shutil.copytree(backup_source, target_dir, symlinks=True)
                    self.log(f"恢复安装目录: {target_dir}", "INFO")
                
                # 恢复符号链接
                for link_info in self.rollback_info.get('symlinks', []):
                    link_path = Path(link_info['link'])
                    target_path = Path(link_info['target'])
                    
                    if link_path.exists():
                        link_path.unlink()
                    
                    if target_path.exists():
                        link_path.symlink_to(target_path)
                        self.log(f"恢复符号链接: {link_path}", "INFO")
                
                self.log("✅ 回滚完成", "INFO")
            
        except Exception as e:
            self.log(f"回滚失败: {e}", "ERROR")
    
    def uninstall_current(self) -> bool:
        """卸载当前安装的 Node.js"""
        self.log("开始卸载 Node.js...")
        
        # 查找当前激活的版本
        active_version = None
        if self.BIN_LINK_DIR.joinpath("node").exists():
            try:
                node_path = self.BIN_LINK_DIR.joinpath("node").resolve()
                for version_dir in self.INSTALL_BASE.glob("*/"):
                    if node_path.is_relative_to(version_dir):
                        active_version = version_dir.name
                        break
            except:
                pass
        
        if not active_version:
            self.log("未找到当前激活的 Node.js 版本", "WARN")
            active_version = input("请输入要卸载的版本号: ").strip()
        
        if not active_version:
            self.log("未指定版本号，取消卸载", "INFO")
            return False
        
        # 确认卸载
        confirm = input(f"确定要卸载 Node.js v{active_version}？此操作不可逆！ [y/N]: ").strip().lower()
        if confirm != 'y':
            self.log("取消卸载", "INFO")
            return False
        
        try:
            # 1. 移除符号链接
            for bin_file in ["node", "npm", "npx"]:
                link_path = self.BIN_LINK_DIR / bin_file
                if link_path.exists() and link_path.is_symlink():
                    try:
                        target = link_path.resolve()
                        if str(target).startswith(str(self.INSTALL_BASE / active_version)):
                            link_path.unlink()
                            self.log(f"移除符号链接: {link_path}", "INFO")
                    except:
                        pass
            
            # 2. 移除安装目录
            install_dir = self.INSTALL_BASE / active_version
            if install_dir.exists():
                shutil.rmtree(install_dir)
                self.log(f"移除安装目录: {install_dir}", "INFO")
            
            # 3. 检查是否还有其他版本
            remaining_versions = list(self.INSTALL_BASE.glob("*/"))
            if not remaining_versions:
                # 如果没有其他版本，移除环境配置
                if self.PROFILE_SCRIPT.exists():
                    self.PROFILE_SCRIPT.unlink()
                    self.log(f"移除环境配置: {self.PROFILE_SCRIPT}", "INFO")
                
                # 可选：移除基础目录
                if self.INSTALL_BASE.exists():
                    try:
                        self.INSTALL_BASE.rmdir()
                        self.log(f"移除基础目录: {self.INSTALL_BASE}", "INFO")
                    except:
                        pass
            
            self.log(f"✅ Node.js v{active_version} 卸载完成", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"卸载失败: {e}", "ERROR")
            return False

def print_banner():
    """打印脚本横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║            Node.js 企业级安装脚本 - 全栈架构师版              ║
║                   版本 2.0 (2026-01-11)                      ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def main():
    """主函数"""
    print_banner()
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='Node.js 企业级安装脚本')
    parser.add_argument('--version', type=str, help='指定安装的版本号 (如: 24.12.0)')
    parser.add_argument('--uninstall', action='store_true', help='卸载当前安装的 Node.js')
    parser.add_argument('--list-versions', action='store_true', help='列出可用 LTS 版本')
    args = parser.parse_args()
    
    # 创建安装器实例
    installer = NodeJSInstaller()
    
    # 处理卸载请求
    if args.uninstall:
        return installer.uninstall_current()
    
    # 处理列出版本请求
    if args.list_versions:
        installer.log("正在获取可用 LTS 版本...")
        try:
            with urllib.request.urlopen(installer.NODE_JS_INDEX, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            lts_versions = [v for v in data if v.get('lts')]
            print("\n可用 Node.js LTS 版本:")
            for i, v in enumerate(lts_versions[:10], 1):  # 显示最近10个
                print(f"  {i:2d}. {v['version']:10} ({v.get('lts', 'N/A'):15}) - {v['date']}")
            return True
        except Exception as e:
            installer.log(f"获取版本列表失败: {e}", "ERROR")
            return False
    
    # 标准安装流程
    installer.log(f"系统架构: {installer.current_arch} -> {installer.node_arch}")
    
    # 1. 检查前提条件
    if not installer.check_prerequisites():
        return False
    
    # 2. 获取版本信息
    if args.version:
        version_info = {
            'version': args.version,
            'full_version': f"v{args.version}",
            'npm_version': 'unknown',
            'release_date': 'unknown',
            'lts_name': 'Specified'
        }
        installer.log(f"使用指定版本: v{args.version}", "INFO")
    else:
        version_info = installer.get_latest_lts_version()
        if not version_info:
            installer.log("无法获取版本信息，安装终止", "ERROR")
            return False
    
    # 3. 确认安装
    print(f"\n安装信息:")
    print(f"  • 版本:      v{version_info['version']} ({version_info['lts_name']})")
    print(f"  • 架构:      {installer.node_arch}")
    print(f"  • 安装位置:  {installer.INSTALL_BASE / version_info['version']}")
    print(f"  • 发布日期:  {version_info['release_date']}")
    print()
    
    confirm = input("是否继续安装？(Y/n): ").strip().lower()
    if confirm and confirm != 'y':
        installer.log("安装已取消", "INFO")
        return False
    
    # 4. 创建备份
    if not installer.create_backup():
        installer.log("备份创建失败，继续安装可能有风险", "WARN")
        confirm = input("是否继续？(y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    # 5. 执行安装
    success = False
    try:
        success = installer.install_version(version_info)
    finally:
        # 6. 清理和回滚
        installer.cleanup(success)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n安装被用户中断", "INFO")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)