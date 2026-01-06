import os
import subprocess
import requests
from semver import VersionInfo
from messenger import send_ntfy


def run_command(command, capture=True):
    """封装命令执行，失败时发送通知并抛异常"""
    print(f"执行命令: {command}")
    result = subprocess.run(
        command, shell=True, capture_output=capture, text=True
    )
    if result.stdout:
        print(f"输出: {result.stdout.strip()}")
    if result.stderr:
        print(f"错误输出: {result.stderr.strip()}")
    if result.returncode != 0:
        error_msg = f"❌ 命令执行失败: {command}\n错误详情: {result.stderr.strip()}"
        send_ntfy(error_msg, title="命令执行失败", priority="high")
        raise RuntimeError(error_msg)
    return result.stdout.strip()


def get_next_version():
    """计算下一个 semantic 版本号（默认 bump patch）"""
    print("正在获取最新 tag...")
    run_command("git fetch --tags --quiet")
    tags_output = run_command("git tag --sort=-version:refname")
    tags = [t.lstrip("v") for t in tags_output.splitlines() if t.startswith("v")]

    if not tags:
        print("未找到现有 tag，默认从 v1.0.0 开始")
        return "v1.0.0"

    latest = tags[0]
    print(f"当前最新版本: v{latest}")

    try:
        ver = VersionInfo.parse(latest)
        bumped = ver.bump_patch()
        next_ver = f"v{bumped}"
        print(f"计算下一个版本: {next_ver}")
        return next_ver
    except ValueError:
        print("最新 tag 格式无法解析，回退到 v1.0.0")
        return "v1.0.0"


def build_flutter_apk():
    """执行 Flutter 构建并返回 APK 路径"""
    print("🚀 开始 Flutter 构建 APK...")
    run_command("flutter pub get")
    run_command("flutter build apk --release")

    apk_path = "build/app/outputs/flutter-apk/app-release.apk"
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK 文件未生成: {apk_path}")
    print(f"✅ APK 构建成功: {apk_path}")
    return apk_path


def create_gitea_release(api_url: str, repo: str, token: str, version: str):
    """创建 Gitea Release，返回 release_id"""
    print("🌐 正在创建 Gitea Release...")
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }

    # 获取当前分支作为 target_commitish
    current_branch = run_command("git rev-parse --abbrev-ref HEAD")

    release_data = {
        "tag_name": version,
        "target_commitish": current_branch,
        "name": f"Release {version}",
        "body": f"自动发布版本 {version}",
        "draft": False,
        "prerelease": False,
    }

    url = f"{api_url}/repos/{repo}/releases"
    resp = requests.post(url, json=release_data, headers=headers)
    resp.raise_for_status()
    release_id = resp.json()["id"]
    print(f"✅ Release 创建成功，ID: {release_id}")
    return release_id


def upload_apk_to_release(api_url: str, repo: str, token: str, release_id: int, apk_path: str, version: str):
    """上传 APK 到指定 Release"""
    print("📤 正在上传 APK...")
    filename = f"app-release-{version.lstrip('v')}.apk"
    url = f"{api_url}/repos/{repo}/releases/{release_id}/assets"

    headers = {"Authorization": f"token {token}"}

    with open(apk_path, "rb") as f:
        files = {
            "attachment": (
                filename,
                f,
                "application/vnd.android.package-archive",
            )
        }
        resp = requests.post(url, headers=headers, files=files)
        resp.raise_for_status()

    print(f"✅ APK 上传成功: {filename}")


def perform_deploy(gitea_token: str, gitea_api_url: str, gitea_repo: str):
    """核心部署流程（本地与 CI 共用）"""
    try:
        print("=== 开始 CI/CD 部署流程 ===")

        # 处理 API URL
        api_url = gitea_api_url.rstrip("/")
        if "/api/v1" not in api_url:
            api_url += "/api/v1"

        # 1. 计算版本
        version = get_next_version()
        print(f"📦 目标发布版本: {version}")

        # 2. 构建 APK
        apk_path = build_flutter_apk()

        # 3. 创建 Release
        release_id = create_gitea_release(api_url, gitea_repo, gitea_token, version)

        # 4. 上传 APK
        upload_apk_to_release(api_url, gitea_repo, gitea_token, release_id, apk_path, version)

        # 5. 成功通知
        send_ntfy(
            f"版本 {version} 发布成功！\nAPK 已上传至 Release。",
            title="✅ 发布成功",
            tags="package,tada",
        )
        print("=== 部署流程完成 ===")

    except Exception as e:
        error_detail = f"部署流程异常: {str(e)}"
        print(error_detail)
        send_ntfy(error_detail, title="部署失败", priority="high")
        raise