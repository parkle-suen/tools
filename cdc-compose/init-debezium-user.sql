-- 创建 Debezium 专用的复制用户
CREATE USER debezium WITH REPLICATION LOGIN PASSWORD '11111111';




-- 授予必要权限
GRANT USAGE ON SCHEMA public TO debezium;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

-- 关键：允许读取系统表（Debezium 需要）
GRANT pg_read_all_data TO debezium;  -- PG14+ 推荐方式
-- 或手动授权（PG<14）：
-- GRANT SELECT ON pg_catalog.pg_publication TO debezium;
-- GRANT SELECT ON pg_catalog.pg_replication_slots TO debezium;


-- 授予对所有表的 SELECT 权限 (根据实际 schema 调整)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;