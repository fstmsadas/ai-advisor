import redis
import hashlib
import json
from config import config
import logging

logger = logging.getLogger(__name__)

# 全局变量
pool = None
r = None

def init_redis():
    """惰性初始化 Redis 连接池（避免启动时阻塞）"""
    global pool, r
    if r is not None:
        return
    try:
        pool = redis.ConnectionPool(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=0,
            max_connections=10,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        r = redis.Redis(connection_pool=pool)
        r.ping()  # 测试连接
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.error(f"Redis 初始化失败: {e}")
        r = None
        pool = None

def get_cache_key(prefix, params):
    """生成缓存键，基于前缀和参数字典"""
    key_str = prefix + ":" + hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return key_str

def cache_get(key):
    """从缓存获取值，若 Redis 不可用则返回 None"""
    if r is None:
        init_redis()
        if r is None:
            logger.debug("Redis 不可用，跳过读取缓存")
            return None
    try:
        return r.get(key)
    except Exception as e:
        logger.warning(f"Redis 读取失败: {e}")
        return None

def cache_set(key, value, ttl=3600):
    """写入缓存，若 Redis 不可用则静默跳过"""
    if r is None:
        init_redis()
        if r is None:
            logger.debug("Redis 不可用，跳过写入缓存")
            return
    try:
        r.setex(key, ttl, json.dumps(value) if not isinstance(value, str) else value)
    except Exception as e:
        logger.warning(f"Redis 写入失败: {e}")

# 会话历史管理
def save_chat_history(session_id: str, messages: list, ttl: int = 3600):
    cache_set(f"chat:{session_id}", json.dumps(messages, ensure_ascii=False), ttl)

def get_chat_history(session_id: str):
    data = cache_get(f"chat:{session_id}")
    return json.loads(data) if data else []

def clear_chat_history(session_id: str):
    cache_set(f"chat:{session_id}", None, ttl=0)  # 用空值并立即过期，或直接删除
    # 更准确的做法是使用 redis.delete，但为了统一降级，此处用 set 空值
    # 实际可改为： if r: r.delete(f"chat:{session_id}")
