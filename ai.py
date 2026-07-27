import time
import openai
from cache import cache_get, cache_set, get_cache_key
from config import config

# 初始化 OpenAI 客户端（指向 DeepSeek）
client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=30.0,
    max_retries=2
)

# ---------------------- 单轮对话（原有，保留） ----------------------
def generate_response(prompt: str, temperature: float = 0.7, system_prompt: str = None) -> str:
    if system_prompt is None:
        system_prompt = "你是一个专业的运维顾问，擅长分析系统指标并提供优化建议。请给出具体、可操作的建议，并优先考虑安全性和稳定性。"

    cache_key = get_cache_key("ai", {
        "prompt": prompt,
        "temp": temperature,
        "system": system_prompt[:50]
    })

    try:
        cached = cache_get(cache_key)
        if cached:
            return cached
    except Exception:
        pass  # Redis 不可用时跳过缓存

    try:
        response = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"DeepSeek API 调用失败: {e}")

    try:
        ttl = 86400 if temperature < 0.3 else (300 if temperature > 0.7 else 3600)
        cache_set(cache_key, reply, ttl)
    except Exception:
        pass

    return reply

# ---------------------- 多轮对话（新增） ----------------------
def generate_chat(messages: list, temperature: float = 0.7) -> str:
    """
    支持多轮对话，messages 格式：[{"role": "user", "content": "..."}, ...]
    此函数不使用缓存，因为对话历史动态变化。
    """
    system_prompt = "你是一个专业的运维顾问，擅长系统优化和故障排查。请基于对话历史回答问题。"
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        raise RuntimeError(f"DeepSeek API 调用失败: {e}")
