import redis
import hashlib
import json
from config import config

pool = redis.ConnectionPool(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=0,
    max_connections=10,
    decode_responses=True
)
r = redis.Redis(connection_pool=pool)

def get_cache_key(prefix, params):
    key_str = prefix + ":" + hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return key_str

def cache_get(key):
    return r.get(key)

def cache_set(key, value, ttl=3600):
    r.setex(key, ttl, json.dumps(value) if not isinstance(value, str) else value)

# ==================== 新增会话历史管理 ====================

def save_chat_history(session_id: str, messages: list, ttl: int = 3600):
    """保存会话消息列表到 Redis"""
    key = f"chat:{session_id}"
    r.setex(key, ttl, json.dumps(messages, ensure_ascii=False))

def get_chat_history(session_id: str):
    """获取会话消息列表（返回列表，若无则返回空列表）"""
    key = f"chat:{session_id}"
    data = r.get(key)
    if data:
        return json.loads(data)
    return []

def clear_chat_history(session_id: str):
    """清除会话历史"""
    key = f"chat:{session_id}"
    r.delete(key)
