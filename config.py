from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, validator
from typing import Optional, Literal

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "agent"
    DEBUG: bool = False
    
    # 数据库配置
    DB_TYPE: Literal["postgresql", "mysql"] = "postgresql"  # 数据库类型，支持 postgresql 或 mysql
    DB_HOST: str = "localhost"                     # 数据库主机地址
    DB_PORT: int = Field(5432, ge=1, le=65535)     # 数据库端口，默认 5432 (PostgreSQL)
    DB_USER: str = Field(..., min_length=1)        # 数据库用户名（必填）
    DB_PASSWORD: str = Field(..., min_length=1)    # 数据库密码（必填）
    DB_NAME: str = Field(..., min_length=1)        # 数据库名（必填）
    DATABASE_URL: Optional[str] = None             # 可选的完整连接字符串
    
    # 管理员配置
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password"
    
    # API密钥
    DASHSCOPE_API_KEY: str = "your_api_key_here"

    # 动态设置默认端口
    @validator("DB_PORT", pre=True, always=True)
    def set_default_port(cls, v, values):
        if v is not None:
            return v
        # 根据数据库类型设置默认端口
        if values.get("DB_TYPE") == "mysql":
            return 3306
        return 5432

    # 如果提供了 DB_* 单独字段，可以动态构造 DATABASE_URL
    @validator("DATABASE_URL", always=True)
    def assemble_db_url(cls, v, values):
        if v:
            return v
        # 从 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME 构造
        db_type = values.get('DB_TYPE', 'postgresql')
        # 根据数据库类型构造连接字符串
        if db_type == "mysql":
            url = f"mysql://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_NAME')}"
        else:  # postgresql
            url = f"postgresql://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_NAME')}"
            # 如果启用SSL，取消下面注释
            # url += "?sslmode=require"
        return url

    class Config:
        env_file = ".env"          # 从 .env 文件加载
        env_file_encoding = "utf-8"
        case_sensitive = False     # 环境变量大小写不敏感

settings = Settings() # type: ignore
