"""
配置加载模块

负责从 databases.json 加载多服务器配置
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """单个MySQL服务器配置"""
    id: str
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset
        }


class ConfigLoader:
    """配置加载器"""

    _instance: Optional["ConfigLoader"] = None

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        from .path_manager import path_manager

        self.project_root = path_manager.project_root
        self.default_server_id: Optional[str] = None
        self.servers: Dict[str, ServerConfig] = {}

        self._load_env()
        self._load_databases()

        self._initialized = True

    def _load_env(self):
        """加载 .env 文件中的环境变量"""
        from dotenv import load_dotenv

        env_file = self.project_root / "config" / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        self.default_server_id = os.getenv("DEFAULT_SERVER")

    def _load_databases(self):
        """从 databases.json 加载服务器配置"""
        db_config_file = self.project_root / "config" / "databases.json"

        if not db_config_file.exists():
            raise FileNotFoundError(f"配置文件未找到: {db_config_file}")

        with open(db_config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        servers_data = data.get("servers", {})
        for server_id, config in servers_data.items():
            self.servers[server_id] = ServerConfig(
                id=server_id,
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                user=config.get("user", ""),
                password=config.get("password", ""),
                database=config.get("database", ""),
                charset=config.get("charset", "utf8mb4")
            )

        if not self.default_server_id and self.servers:
            self.default_server_id = list(self.servers.keys())[0]

    def get_server(self, server_id: Optional[str] = None) -> ServerConfig:
        """获取服务器配置"""
        sid = server_id or self.default_server_id
        if not sid:
            raise ValueError("没有配置任何MySQL服务器")

        if sid not in self.servers:
            available = ", ".join(self.servers.keys())
            raise ValueError(f"服务器 '{sid}' 未配置。可用服务器: {available}")

        return self.servers[sid]

    def list_servers(self) -> List[dict]:
        """列出所有服务器（不包含密码）"""
        return [
            {
                "id": s.id,
                "host": s.host,
                "port": s.port,
                "database": s.database
            }
            for s in self.servers.values()
        ]

    def get_default_server_id(self) -> Optional[str]:
        """获取默认服务器ID"""
        return self.default_server_id


def get_config() -> ConfigLoader:
    """获取配置加载器单例"""
    return ConfigLoader()
