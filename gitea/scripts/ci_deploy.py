import os
import subprocess
import requests
from semver import VersionInfo  # 已安装 semver 库
from ci_messenger import send_ntfy  # 假设模块存在

# --- 配置区（从环境变量获取，避免硬编码） ---
GITEA_TOKEN = os.getenv("GITEA_TOKEN")
GITEA_API_URL = os.getenv("GITEA_API_URL", "").rstrip("/")  # 去除尾缀 /
if "/api/v1" not in GITEA_API_URL:
    GITEA_API_URL += "/api/v1"  # 确保包含 /api/v1
REPO = os.getenv("GITEA_REPO")  # 格式: owner/repo

def run_command(command):
    """封装命令执行，带详细日志"""
    print(f"执行命令: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"输出: {result.stdout}")
    if result.returncode != 0:
        error_msg = f"❌ 命令失败: {command}\n错误: {result.stderr}"
        send_ntfy(error_msg, title="部署失败", priority="high")
        raise Exception(error_msg)
    return result.stdout.strip()

def get_next_version():
    """计算下一个 semantic 版本号"""
    print("获取最新 tag...")
    run_command("git fetch --tags --quiet")
    tags_output = run_command("git tag --sort=-version:refname")
    tags = [t.lstrip('v') for t in tags_output.splitlines() if t.startswith('v')]
    
    if not tags:
        print("无现有 tag，默认 v1.0.0")
        return "v1.0.0"
    
    latest = tags[0]
    print(f"最新版本: {latest}")
    
    try:
        ver = VersionInfo.parse(latest)
        bumped = ver.bump_patch()  # 默认 patch +1
        next_ver = f"v{bumped}"
        print(f"下一个版本: {next_ver}")
        return next_ver
    except ValueError:
        print("版本解析失败，回退到 v1.0.0")
        return "v1.0.0"

def main():
    try:
        print("开始 CI/CD 部署流程...")
        
        # 1. 计算版本
        version = get_next_version()
        print(f"📦 目标发布版本: {version}")
        
        # 2. Flutter 编译
        print("🚀 开始 Flutter 构建 APK...")
        run_command("flutter pub get")
        run_command("flutter build apk --release")
        
        apk_path = "build/app/outputs/flutter-apk/app-release.apk"
        if not os.path.exists(apk_path):
            raise Exception(f"APK 未生成: {apk_path}")
        print(f"✅ APK 生成成功: {apk_path}")
        
        # 3. 创建 Release
        print("🌐 创建 Gitea Release...")
        headers = {"Authorization": f"token {GITEA_TOKEN}", "Content-Type": "application/json"}
        release_data = {
            "tag_name": version,
            "target_commitish": "main",
            "name": f"Release {version}",
            "body": f"自动发布版本 {version}",
            "draft": False,
            "prerelease": False
        }
        
        resp = requests.post(f"{GITEA_API_URL}/repos/{REPO}/releases", json=release_data, headers=headers)
        resp.raise_for_status()
        release = resp.json()
        release_id = release['id']
        print(f"✅ Release 创建成功，ID: {release_id}")
        
        # 4. 上传 APK
        print("📤 上传 APK...")
        upload_url = f"{GITEA_API_URL}/repos/{REPO}/releases/{release_id}/assets"
        filename = f"app-release-{version.lstrip('v')}.apk"
        with open(apk_path, "rb") as f:
            files = {"attachment": (filename, f, "application/vnd.android.package-archive")}
            up_resp = requests.post(upload_url, headers=headers, files=files)
            up_resp.raise_for_status()
        print(f"✅ APK 上传成功: {filename}")
        
        # 5. 成功通知
        send_ntfy(f"版本 {version} 发布成功！\nAPK 已上传。", title="✅ 发布成功", tags="package,tada")
        
    except Exception as e:
        error_detail = f"流程异常: {str(e)}"
        print(error_detail)
        send_ntfy(error_detail, title="部署失败", priority="high")
        raise  # 确保 job 失败

if __name__ == "__main__":
    main()