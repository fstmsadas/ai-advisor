import json
import os
import time
import redis
from config import config
import logging

logger = logging.getLogger(__name__)

# ---- Redis 连接 ----
try:
    r = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    r.ping()
    redis_available = True
    logger.info("Redis 可用，将使用 Redis 作为主缓冲")
except Exception as e:
    redis_available = False
    logger.warning(f"Redis 不可用: {e}，将使用文件缓冲")

# ---- 文件缓冲路径（相对路径，兼容容器和宿主机） ----
FILE_BUFFER_PATH = os.path.join(os.getcwd(), "data", "buffer.jsonl")
os.makedirs(os.path.dirname(FILE_BUFFER_PATH), exist_ok=True)

def write_to_buffer(data_type, data):
    if redis_available:
        try:
            r.rpush(f"buffer:{data_type}", json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Redis 写入失败: {e}，降级到文件")
    try:
        with open(FILE_BUFFER_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"type": data_type, "data": data, "ts": time.time()}) + "\n")
        return True
    except Exception as e:
        logger.error(f"文件缓冲写入失败: {e}")
        return False

def read_from_buffer(data_type, batch_size=100):
    if redis_available:
        try:
            items = []
            for _ in range(batch_size):
                item = r.lpop(f"buffer:{data_type}")
                if item is None:
                    break
                items.append(json.loads(item))
            return items
        except Exception as e:
            logger.error(f"Redis 读取失败: {e}，降级到文件")
    try:
        with open(FILE_BUFFER_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        items = []
        remaining = []
        for line in lines:
            data = json.loads(line.strip())
            if data.get("type") == data_type and len(items) < batch_size:
                items.append(data["data"])
            else:
                remaining.append(line)
        if remaining:
            with open(FILE_BUFFER_PATH, 'w', encoding='utf-8') as f:
                f.writelines(remaining)
        else:
            os.remove(FILE_BUFFER_PATH)
        return items
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"文件缓冲读取失败: {e}")
        return []

def get_buffer_length(data_type):
    if redis_available:
        try:
            return r.llen(f"buffer:{data_type}")
        except:
            pass
    try:
        with open(FILE_BUFFER_PATH, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if json.loads(line.strip()).get("type") == data_type)
    except:
        return 0
