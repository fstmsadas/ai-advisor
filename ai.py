import time
import openai
from cache import cache_get, cache_set, get_cache_key
from config import config
import logging

logger = logging.getLogger(__name__)

# 初始化 OpenAI 客户端，设置超时
client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=30.0,
    max_retries=2  # openai 内置重试
)

def generate_response(prompt: str, temperature: float = 0.7, system_prompt: str = None) -> str:
    if system_prompt is None:
        system_prompt = "你是一个专业的运维顾问，擅长分析系统指标并提供优化建议。"

    cache_key = get_cache_key("ai", {
        "prompt": prompt,
        "temp": temperature,
        "system": system_prompt[:50]
    })

    # 尝试读缓存（即使 Redis 失败也不影响后续）
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 调用 API（带重试和降级）
    max_retries = 3
    for attempt in range(max_retries):
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
            # 成功，则缓存
            ttl = 86400 if temperature < 0.3 else (300 if temperature > 0.7 else 3600)
            cache_set(cache_key, reply, ttl)
            return reply
        except Exception as e:
            logger.error(f"AI 调用失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # 最后一次失败，返回降级消息
                return f"⚠️ AI 服务暂时不可用，请稍后重试。错误信息: {str(e)[:200]}"
            time.sleep(2 ** attempt)  # 指数退避

    return "AI 服务暂时不可用，请稍后重试。"
