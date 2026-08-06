"""
通维AI项目管理系统 - 合规模块

向后兼容导出 router，保持 routers.py 中 `compliance.router` 可用。
"""

from .routes import router

__all__ = ["router"]
