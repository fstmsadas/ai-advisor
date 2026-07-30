import time
from ai import generate_response
from system_metrics import get_system_metrics, get_top_processes
from db import insert_ai_advice
from utils import setup_logger

logger = setup_logger('ai_advisor')

def get_optimization_advice(metrics, top_procs, retries=3):
    prompt = f"""
    系统当前状态：
    - CPU 使用率: {metrics['cpu_percent']}%
    - 内存使用率: {metrics['memory_percent']}%
    - 磁盘使用率: {metrics['disk_usage']}%
    - 负载: {metrics['load_avg']}
    - 高 CPU 进程: {top_procs}
    请给出优化建议，包括可能的瓶颈和调优方向。
    """
    try:
        advice = generate_response(prompt, temperature=0.2)
        if advice and advice.strip():
            return advice.strip()
        else:
            logger.warning("AI 返回空内容，使用降级建议")
    except Exception as e:
        logger.error(f"AI 建议生成失败: {e}")

    # 降级建议（静态）
    return f"⚠️ 当前 CPU 使用率 {metrics['cpu_percent']}%，建议检查以下高 CPU 进程：{top_procs}，考虑优化代码或扩容。"
