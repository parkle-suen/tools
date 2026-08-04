# ═══════════════════════════════════════════════════════════════
# CachyOS Plasma 虚拟化环境安装脚本 v3
# 已核实: 所有包存在 (CachyOS/extra 仓库 + AUR, 2026-08)
# ═══════════════════════════════════════════════════════════════

# ── 第 0 步：paru ──────────────────────────────────────────────
# CachyOS 官方仓库自带 paru (cachyos repo 2.1.0-3)，直接装即可
sudo pacman -S --needed paru

# ── 第 1 步：QEMU 核心 + UEFI 固件 + 软件 TPM ─────────────────
# qemu-full 11.0.3 (Provides qemu，满足 quickemu 依赖)
# edk2-ovmf 202605 / swtpm 0.10.1 (均已在 extra)
sudo pacman -S --needed qemu-full edk2-ovmf swtpm

# ── 第 2 步：libvirt + virt-manager 管理栈 ────────────────────
# virt-install 是 virt-manager 的硬依赖 (virt-install=5.1.0)，自动装上
# dnsmasq 是 libvirt 的 optdepends，默认 NAT 网络必需，必须显式装
# iptables-nft 包已不存在（已合并进 iptables，系统已装 1.8.13 nft 后端）
sudo pacman -S --needed libvirt virt-manager dnsmasq

# ── 第 3 步：Windows 客户机 virtio 驱动 ───────────────────────
# quickemu 路径：不用装，quickget 建 Windows VM 时自动下载 virtio-win.iso
# virt-manager 路径：装 AUR 包（ISO → /var/lib/libvirt/images/virtio-win.iso）
paru -S --needed virtio-win
# 或手动下载：https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/ （已验证 200 可达）

# ── 第 4 步：客户机增强（注意：装进【客户机】内部，不是主机）──
# 主机侧无需再装任何东西（spice-gtk 客户端由 virt-manager 依赖带上）
# 在 Linux 客户机【内部】执行：
#   sudo pacman -S --needed spice-vdagent          # 剪贴板/拖放
#   sudo pacman -S --needed qemu-guest-agent       # (可选) 优雅关机/文件系统冻结

# ── 第 5 步：quickemu + quickget（AUR）────────────────────────
paru -S --needed quickemu
# 可选：paru -S quickgui   （图形前端）

# ── 第 6 步：启用 libvirtd 服务 ───────────────────────────────
# 会自动连带启用 virtlogd.socket 和 virtlockd.socket
sudo systemctl enable --now libvirtd.service

# ── 第 7 步：验证 ─────────────────────────────────────────────
virsh list --all            # 应显示空列表无报错
systemctl status libvirtd   # active (running)
quickemu --version          # 4.9.9
ls /var/lib/libvirt/images/virtio-win.iso   # 若装了 AUR virtio-win

# ── 第 8 步（可选）：免密管理权限 ─────────────────────────────
# 默认【不需要】！你在 wheel 组 + polkit 已能完整管理，virt-manager 连
# qemu:///system 时弹一次密码即可（polkit-kde-agent 已装，提示框正常）。
# 只有你嫌每次输密码烦，才执行下面这条：
sudo usermod -aG libvirt $USER
# 注1: 必须放在第 2 步【之后】——libvirt 组由装包时的 sysusers 钩子创建，
#      提前执行会报 "group 'libvirt' does not exist"
# 注2: 执行后必须【重新登录】组权限才生效
# 注3: /dev/kvm 在本机是 0666，kvm 组无需加入，quickemu 用户态直接可用