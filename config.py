import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 数据库
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "container_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "YourPass123!")
    DB_NAME = os.getenv("DB_NAME", "myapp")
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", 10))

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    # AI
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    # 应用
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")   # 生产环境务必设置
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    CPU_THRESHOLD = int(os.getenv("CPU_THRESHOLD", 80))
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/var/log/syslog")

config = Config()
