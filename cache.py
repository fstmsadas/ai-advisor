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
        r.ping()
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.error(f"Redis 初始化失败: {e}")
        r = None
        pool = None

def get_cache_key(prefix, params):
    key_str = prefix + ":" + hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return key_str

def cache_get(key):
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
    if r is None:
        init_redis()
        if r is None:
            logger.debug("Redis 不可用，跳过写入缓存")
            return
    try:
        r.setex(key, ttl, json.dumps(value) if not isinstance(value, str) else value)
    except Exception as e:
        logger.warning(f"Redis 写入失败: {e}")

def cache_delete(key):
    """删除单个缓存键"""
    if r is None:
        return
    try:
        r.delete(key)
    except Exception as e:
        logger.warning(f"Redis 删除失败: {e}")

def cache_delete_pattern(pattern):
    """删除匹配模式的所有键（用于批量清理）"""
    if r is None:
        return
    try:
        for key in r.scan_iter(pattern):
            r.delete(key)
    except Exception as e:
        logger.warning(f"Redis 模式删除失败: {e}")

# 会话历史管理
def save_chat_history(session_id: str, messages: list, ttl: int = 3600):
    try:
        import json
        cache_set(f"chat:{session_id}", json.dumps(messages, ensure_ascii=False), ttl)
    except Exception as e:
        logger.error(f"保存聊天历史失败: {e}")

def get_chat_history(session_id: str):
    import json
    data = cache_get(f"chat:{session_id}")
    return json.loads(data) if data else []

def clear_chat_history(session_id: str):
    cache_delete(f"chat:{session_id}")
