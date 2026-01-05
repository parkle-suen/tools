import os
from core import perform_deploy


def main():
    print("=== Gitea CI/CD 部署脚本启动 ===")

    gitea_token = os.getenv("GITEA_TOKEN")
    gitea_api_url = os.getenv("GITEA_API_URL", "")
    gitea_repo = os.getenv("GITEA_REPO")

    if not all([gitea_token, gitea_api_url, gitea_repo]):
        raise ValueError("缺少必要的环境变量：GITEA_TOKEN、GITEA_API_URL、GITEA_REPO")

    perform_deploy(gitea_token, gitea_api_url, gitea_repo)


if __name__ == "__main__":
    main()