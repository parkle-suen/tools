import getpass
from core import perform_deploy


# --- 配置区（测试阶段默认值） ---
# 注意：Token 为敏感信息，仅在本地测试脚本中使用硬编码默认值。
#      生产环境或脚本提交到仓库时，请删除或注释掉默认 Token，避免泄露！
DEFAULT_GITEA_API_URL = "http://192.168.0.169:3000"
DEFAULT_TOKEN = "db52a5c2ee46e460a62a5244c9fd6cab8abe7f61"  # root/admin 最高权限 token
DEFAULT_REPO = "root/soccer-app-2"


def input_with_default(prompt: str, default: str) -> str:
    """带默认值的输入提示（用户直接回车即使用默认值）"""
    user_input = input(f"{prompt} [默认: {default}]: ").strip()
    return user_input if user_input else default


def main():
    print("=== Gitea Flutter APK 发布脚本 - 本地调试模式 ===")
    print("请使用一个测试仓库的副本进行调试（推荐先 fork 或新建空仓库）。")
    print("测试完成后，请手动删除创建的 Release 和 tag。\n")

    # 1. 输入参数（支持直接回车使用默认值）
    gitea_api_url = input_with_default(
        "请输入 Gitea API 基础 URL（例如 http://192.168.0.169:3000）",
        DEFAULT_GITEA_API_URL
    )

    print("\n⚠️  即将输入 Token。若直接回车，将使用脚本中硬编码的默认 Token（仅限本地测试！）")
    token_input = getpass.getpass("请输入 Gitea Token（具有 repo 权限）: ").strip()
    gitea_token = token_input if token_input else DEFAULT_TOKEN

    gitea_repo = input_with_default(
        "请输入仓库（owner/repo 格式，例如 root/soccer-app-2）",
        DEFAULT_REPO
    )

    if not all([gitea_token, gitea_api_url, gitea_repo]):
        print("❌ 参数不完整，退出。")
        return

    # 2. 参数确认
    print("\n=== 参数确认 ===")
    print(f"API URL: {gitea_api_url}")
    print(f"仓库: {gitea_repo}")
    print(f"Token: {'*' * len(gitea_token)}")
    confirm = input("\n确认使用以上参数执行完整发布流程？（将创建真实 Release 和 tag）[y/N]: ")

    if confirm.lower() != "y":
        print("操作已取消。")
        return

    print("\n提示：若需要 ntfy 通知，请提前设置环境变量 NTFY_BASE_URL 和 NTFY_TOPIC。")
    print("开始执行部署流程...\n")

    perform_deploy(gitea_token, gitea_api_url, gitea_repo)


if __name__ == "__main__":
    main()