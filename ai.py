import time
import openai
from cache import cache_get, cache_set, get_cache_key
from config import config

# 初始化 OpenAI 客户端（指向 DeepSeek）
client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=30.0,          # 请求超时
    max_retries=2          # 内置重试
)

def generate_response(prompt: str, temperature: float = 0.7, system_prompt: str = None) -> str:
    """
    调用 DeepSeek API，支持缓存和 system prompt
    :param prompt: 用户输入
    :param temperature: 0~1，控制随机性
    :param system_prompt: 系统提示词，默认为通用运维顾问
    :return: AI 回复内容
    """
    # 默认系统提示（可覆盖）
    if system_prompt is None:
        system_prompt = (
            "你是一个专业的运维顾问，擅长分析系统指标并提供优化建议。"
            "请给出具体、可操作的建议，并优先考虑安全性和稳定性。"
        )

    # 生成缓存键（包含 prompt, temp 和 system_prompt 摘要）
    cache_key = get_cache_key("ai", {
        "prompt": prompt,
        "temp": temperature,
        "system": system_prompt[:50]  # 摘要避免过长
    })

    # 尝试读取缓存
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 调用 DeepSeek API
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
        # 记录异常，返回错误信息（外部重试机制会捕获）
        raise RuntimeError(f"DeepSeek API 调用失败: {e}")

    # 根据 temperature 设置缓存 TTL
    if temperature < 0.3:
        ttl = 86400   # 24h
    elif temperature > 0.7:
        ttl = 300     # 5min
    else:
        ttl = 3600    # 1h

    cache_set(cache_key, reply, ttl)
    return reply
