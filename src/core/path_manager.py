"""
路径管理模块

统一管理项目中的所有文件路径，基于 PROJECT_ROOT 进行拼接
"""

import os
from pathlib import Path
from typing import Optional


class PathManager:
    """路径管理器（单例模式）"""

    _instance: Optional["PathManager"] = None

    def __new__(cls) -> "PathManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        project_root_env = os.getenv("PROJECT_ROOT")

        if project_root_env:
            self._project_root = Path(project_root_env).resolve()
        else:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "config").exists() or (parent / ".env").exists():
                    self._project_root = parent
                    break
            else:
                self._project_root = Path.cwd()

        self._initialized = True

    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return self._project_root

    @property
    def config_dir(self) -> Path:
        """获取配置目录"""
        return self._project_root / "config"

    @property
    def output_dir(self) -> Path:
        """获取输出目录"""
        return self._project_root / "output"

    @property
    def reference_dir(self) -> Path:
        """获取Reference目录（位于项目根目录的父目录）"""
        parent_root = self._project_root.parent
        ref_dir = parent_root / "Reference"
        if not ref_dir.exists():
            ref_dir = self._project_root / "Reference"
        return ref_dir

    def get_output_path(self, filename: str) -> str:
        """获取输出文件路径，自动创建目录"""
        out_dir = self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / filename)

    def get_config_path(self, config_name: str) -> str:
        """获取配置文件路径"""
        return str(self.config_dir / config_name)

    def resolve_path(self, relative_path: str) -> str:
        """解析相对路径为绝对路径"""
        return str(self._project_root / relative_path)

    def set_output_dir(self, output_dir: str) -> None:
        """动态设置输出目录"""
        self._output_dir = Path(output_dir).resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_output_dir(self) -> Path:
        """获取当前输出目录"""
        return getattr(self, "_output_dir", self.output_dir)


path_manager = PathManager()
