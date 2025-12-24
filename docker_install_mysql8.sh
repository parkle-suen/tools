# 先删除旧容器与数据卷（防止冲突，非常重要！）
docker rm -f mysql8 2>/dev/null
sudo rm -rf /docker/mysql8-data   # ← 自己改路径，注意清空！

# 正式启动（注意参数位置必须在镜像名后面）
docker run -d \
  --name mysql8 \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -v /docker/mysql8-data:/var/lib/mysql \
  --restart unless-stopped \
  mysql:8.0 \
  --lower_case_table_names=1 \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci