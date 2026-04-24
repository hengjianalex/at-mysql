# 数据库配置说明

## 快速开始

1. 复制配置模板：
   ```bash
   cp config/databases.example.json config/databases.json
   ```

2. 编辑 `config/databases.json`，填入你的数据库连接信息：
   ```json
   {
     "servers": {
       "YIFEI": {
         "host": "你的数据库主机地址",
         "port": 3306,
         "user": "你的用户名",
         "password": "你的密码",
         "database": "你的数据库名",
         "charset": "utf8mb4"
       }
     }
   }
   ```

3. 修改 `.env` 文件（如果需要）：
   ```bash
   DEFAULT_SERVER=YIFEI
   ```

## 安全警告

⚠️ **重要**：`config/databases.json` 文件包含敏感的数据库凭证信息，已被添加到 `.gitignore`，**不应该提交到 Git 仓库**。

如果你不小心提交了包含真实密码的配置文件，请：

1. 立即修改数据库密码
2. 从 Git 历史中移除敏感文件：
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config/databases.json" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. 强制推送到远程仓库（谨慎操作）

## 配置项说明

### servers 对象

包含所有可用的数据库服务器配置。

#### 每个服务器的配置项：

- `host` (必需): 数据库主机地址
- `port` (必需): 数据库端口，默认 3306
- `user` (必需): 数据库用户名
- `password` (必需): 数据库密码
- `database` (必需): 数据库名称
- `charset` (可选): 字符集，默认 `utf8mb4`

### 示例配置

```json
{
  "servers": {
    "YIFEI": {
      "host": "sh-cynosdbmysql-grp-ho336kds.sql.tencentcdb.com",
      "port": 27271,
      "user": "root",
      "password": "your-secure-password",
      "database": "hro",
      "charset": "utf8mb4"
    },
    "YUNYAN_OB": {
      "host": "sh-cynosdbmysql-grp-2uw0q4ik.sql.tencentcdb.com",
      "port": 25603,
      "user": "root",
      "password": "your-secure-password",
      "database": "hrssc",
      "charset": "utf8mb4"
    }
  }
}
```

## 使用多服务器

你可以在配置中定义多个数据库服务器，然后在查询时通过 `server_id` 参数选择：

```python
# 使用 YIFEI 服务器
result = MySQL_Yifei(query="SELECT * FROM table")

# 使用 YUNYAN_OB 服务器
result = MySQL_OB(query="SELECT * FROM table")
```

## 环境变量

可以在 `config/.env` 文件中配置默认服务器：

```bash
DEFAULT_SERVER=YIFEI
```

## 故障排除

### 连接失败

1. 检查数据库主机和端口是否正确
2. 确认数据库服务正在运行
3. 检查防火墙设置
4. 验证用户名和密码

### 字符集问题

如果遇到中文乱码，确保：
- `charset` 设置为 `utf8mb4`
- 数据库和表也使用 `utf8mb4` 字符集

## 最佳实践

1. ✅ 使用环境变量管理敏感信息
2. ✅ 定期更新数据库密码
3. ✅ 使用最小权限原则创建专用数据库用户
4. ✅ 不要将配置文件提交到版本控制
5. ✅ 使用配置模板 (`databases.example.json`) 作为参考
