import os
import subprocess
import secrets
import string
import shutil
from datetime import datetime

def generate_random_string(length=32):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# 项目目录
project_dir = os.path.expanduser("~/supabase-dev-project")
repo_dir = os.path.expanduser("~/supabase")

print("开始部署 Supabase 开发/测试环境...")

# 1. 克隆仓库
if not os.path.exists(repo_dir):
    print("正在克隆 Supabase 仓库...")
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/supabase/supabase", repo_dir], check=True)
else:
    print("Supabase 仓库已存在，跳过克隆")

# 2. 创建/清理项目目录
if os.path.exists(project_dir):
    print(f"项目目录 {project_dir} 已存在，正在删除并重新创建...")
    shutil.rmtree(project_dir)
os.makedirs(project_dir)
print(f"创建项目目录: {project_dir}")

# 复制文件
shutil.copytree(os.path.join(repo_dir, "docker"), project_dir, dirs_exist_ok=True)
shutil.copy(os.path.join(repo_dir, "docker", ".env.example"), os.path.join(project_dir, ".env"))

# 3. 生成随机密钥
postgres_password = generate_random_string(48)
jwt_secret = generate_random_string(64)
secret_key_base = generate_random_string(64)
studio_username = "admin"  # 你可以改成自己喜欢的
studio_password = generate_random_string(32)

# 修改 .env
env_path = os.path.join(project_dir, ".env")
with open(env_path, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("POSTGRES_PASSWORD="):
        new_lines.append(f"POSTGRES_PASSWORD={postgres_password}\n")
    elif line.startswith("JWT_SECRET="):
        new_lines.append(f"JWT_SECRET={jwt_secret}\n")
    elif line.startswith("SECRET_KEY_BASE="):
        new_lines.append(f"SECRET_KEY_BASE={secret_key_base}\n")
    elif line.startswith("DASHBOARD_USERNAME="):
        new_lines.append(f"DASHBOARD_USERNAME={studio_username}\n")
    elif line.startswith("DASHBOARD_PASSWORD="):
        new_lines.append(f"DASHBOARD_PASSWORD={studio_password}\n")
    else:
        new_lines.append(line)

with open(env_path, "w") as f:
    f.writelines(new_lines)

print(". 密钥已生成并写入 .env 文件")

# 4. 启动 Docker
os.chdir(project_dir)
print("正在拉取 Docker 镜像（第一次会比较慢，请耐心等待）...")
subprocess.run(["docker", "compose", "pull"], check=True)

print("正在启动 Supabase 所有容器...")
subprocess.run(["docker", "compose", "up", "-d"], check=True)

# 5. 保存重要信息到文件
credentials_file = os.path.join(project_dir, "supabase-credentials.txt")
with open(credentials_file, "w") as f:
    f.write(f"Supabase 开发环境部署信息 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
    f.write("="*60 + "\n\n")
    f.write(f"项目目录: {project_dir}\n\n")
    f.write("Studio 管理面板地址:\n")
    f.write("    http://你的服务器IP:8000\n")
    f.write("    或本地访问: http://localhost:8000\n\n")
    f.write("Studio 登录信息:\n")
    f.write(f"    用户名: {studio_username}\n")
    f.write(f"    密码:   {studio_password}\n\n")
    f.write("重要密钥（已写入 .env，已备份在此）:\n")
    f.write(f"    POSTGRES_PASSWORD: {postgres_password}\n")
    f.write(f"    JWT_SECRET:        {jwt_secret}\n")
    f.write(f"    SECRET_KEY_BASE:   {secret_key_base}\n\n")
    f.write("注意：\n")
    f.write("    - ANON_KEY 和 SERVICE_ROLE_KEY 当前使用默认值，仅适合本地玩玩！\n")
    f.write("    - 正式使用请务必更换所有密钥并加反向代理 + SSL\n")
    f.write("    - 查看状态: cd {project_dir} && docker compose ps\n".format(project_dir=project_dir))
    f.write("    - 查看日志: docker compose logs -f\n")
    f.write("    - 停止服务: docker compose down\n")
    f.write("    - 完全重置: docker compose down -v && rm -rf volumes/\n\n")
    f.write("官方文档: https://supabase.com/docs/guides/self-hosting/docker\n")

# 6. 最终输出
print("\n" + "="*60)
print("部署完成！重要信息如下（已保存到 supabase-credentials.txt）")
print("="*60)
print(f"项目目录: {project_dir}")
print("\nStudio 管理面板:")
print("    http://你的服务器IP:8000   (或 http://localhost:8000)")
print("\nStudio 登录:")
print(f"    用户名: {studio_username}")
print(f"    密码:   {studio_password}")
print("\n重要密钥（已保存）:")
print(f"    POSTGRES_PASSWORD: {postgres_password}")
print(f"    JWT_SECRET:        {jwt_secret}")
print(f"    SECRET_KEY_BASE:   {secret_key_base}")
print("\n提示:")
print("    - 所有信息已保存到: {credentials_file}")
print("    - 第一次启动需要几分钟初始化数据库，请稍等")
print("    - 查看容器状态: cd {project_dir} && docker compose ps")
print("="*60)

print("\n玩得开心！有问题随时问我~")