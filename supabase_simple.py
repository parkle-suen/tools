import os
import subprocess
import shutil
from datetime import datetime

# 项目目录
project_dir = os.path.expanduser("~/supabase-dev-project")
repo_dir = os.path.expanduser("~/supabase")

print("开始部署 Supabase 开发/测试环境（固定简单密码版）...")

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

# 3. 固定密码写入 .env
fixed_postgres_password = "11111111"
fixed_jwt_secret = "my_very_long_fixed_jwt_secret_for_dev_1234567890"  # 超过32位
fixed_secret_key_base = "my_fixed_secret_key_base_for_local_dev_only_9876543210"
fixed_studio_username = "root"
fixed_studio_password = "11111111"

env_path = os.path.join(project_dir, ".env")
with open(env_path, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("POSTGRES_PASSWORD="):
        new_lines.append(f"POSTGRES_PASSWORD={fixed_postgres_password}\n")
    elif line.startswith("JWT_SECRET="):
        new_lines.append(f"JWT_SECRET={fixed_jwt_secret}\n")
    elif line.startswith("SECRET_KEY_BASE="):
        new_lines.append(f"SECRET_KEY_BASE={fixed_secret_key_base}\n")
    elif line.startswith("DASHBOARD_USERNAME="):
        new_lines.append(f"DASHBOARD_USERNAME={fixed_studio_username}\n")
    elif line.startswith("DASHBOARD_PASSWORD="):
        new_lines.append(f"DASHBOARD_PASSWORD={fixed_studio_password}\n")
    else:
        new_lines.append(line)

with open(env_path, "w") as f:
    f.writelines(new_lines)

print("已使用固定密码配置 .env 文件")

# 4. 启动 Docker
os.chdir(project_dir)
print("正在拉取 Docker 镜像（第一次会比较慢，请耐心等待）...")
subprocess.run(["docker", "compose", "pull"], check=True)

print("正在启动 Supabase 所有容器...")
subprocess.run(["docker", "compose", "up", "-d"], check=True)

# 5. 保存信息到文件
credentials_file = os.path.join(project_dir, "supabase-credentials.txt")
with open(credentials_file, "w") as f:
    f.write(f"Supabase 开发环境部署信息 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
    f.write("="*60 + "\n\n")
    f.write(f"项目目录: {project_dir}\n\n")
    f.write("Studio 管理面板地址:\n")
    f.write("    http://你的服务器IP:8000\n")
    f.write("    或本地访问: http://localhost:8000\n\n")
    f.write("Studio 登录信息（固定密码）:\n")
    f.write(f"    用户名: {fixed_studio_username}\n")
    f.write(f"    密码:   {fixed_studio_password}\n\n")
    f.write("其他固定密钥:\n")
    f.write(f"    POSTGRES_PASSWORD: {fixed_postgres_password}\n")
    f.write(f"    JWT_SECRET:        {fixed_jwt_secret}\n")
    f.write(f"    SECRET_KEY_BASE:   {fixed_secret_key_base}\n\n")
    f.write("注意：这是本地开发/测试专用配置，密码极简单，千万不要暴露到公网！\n")
    f.write("操作命令（进入项目目录后）:\n")
    f.write("    查看状态: docker compose ps\n")
    f.write("    查看日志: docker compose logs -f\n")
    f.write("    停止: docker compose down\n")
    f.write("    完全重置: docker compose down -v && rm -rf volumes/\n\n")
    f.write("官方文档: https://supabase.com/docs/guides/self-hosting/docker\n")

# 6. 最终输出
print("\n" + "="*60)
print("部署完成！所有密码已固定，超级简单")
print("="*60)
print(f"项目目录: {project_dir}")
print("\nStudio 管理面板:")
print("    http://你的服务器IP:8000   (或 http://localhost:8000)")
print("\nStudio 登录（固定）:")
print(f"    用户名: {fixed_studio_username}")
print(f"    密码:   {fixed_studio_password}   <--- 直接用这个！")
print("\n所有信息已保存到:")
print(f"    {credentials_file}")
print("\n第一次启动需要几分钟初始化数据库，稍等一下再打开浏览器")
print("="*60)
print("\n玩得开心！有问题随时问~")