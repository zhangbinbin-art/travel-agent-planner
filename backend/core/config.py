import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/travel_bishe?charset=utf8mb4")
    SECRET_KEY = os.getenv("SECRET_KEY", "travel-bishe-secret-key-change-me")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    AMAP_KEY = os.getenv("AMAP_KEY", "")
    # Web 服务（地理编码/距离等 REST 接口）专用 Key；未单独配置时回退到 AMAP_KEY
    AMAP_WEB_KEY = os.getenv("AMAP_WEB_KEY") or os.getenv("AMAP_KEY", "")
    # DeepSeek Function-Calling（AI 需求解析/行程解说）；留空则自动降级为关键词解析
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "20"))

settings = Settings()
