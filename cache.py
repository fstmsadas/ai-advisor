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
    """根据前缀和参数字典生成唯一缓存键"""
    key_str = prefix + ":" + hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return key_str

def cache_get(key):
    return r.get(key)

def cache_set(key, value, ttl=3600):
    """设置缓存，value 自动转为 JSON 字符串"""
    r.setex(key, ttl, json.dumps(value) if not isinstance(value, str) else value)
