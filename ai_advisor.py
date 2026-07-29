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
    for attempt in range(retries):
        try:
            advice = generate_response(prompt, temperature=0.2)
            logger.info(f"AI 返回内容长度: {len(advice) if advice else 0}, 内容: {advice[:50] if advice else '空'}")
            if advice and advice.strip():
                return advice.strip()
            else:
                logger.warning(f"AI 返回空字符串，重试 {attempt+1}/{retries}")
        except Exception as e:
            logger.error(f"AI 调用失败 (尝试 {attempt+1}/{retries}): {e}")
            time.sleep(2 ** attempt)
    # 降级：返回默认建议
    default_advice = f"⚠️ 当前 CPU 使用率 {metrics['cpu_percent']}%，建议检查高 CPU 进程：{top_procs}，考虑优化代码或扩容。"
    logger.info(f"返回降级建议: {default_advice}")
    return default_advice

def check_and_advise(threshold=80):
    metrics = get_system_metrics()
    if metrics['cpu_percent'] > threshold:
        top_procs = get_top_processes(5)
        advice = get_optimization_advice(metrics, top_procs)
        if advice:
            try:
                advice_id = insert_ai_advice(advice, metrics, top_procs)
                logger.info(f"AI 建议已入库 (ID={advice_id})")
            except Exception as e:
                logger.error(f"入库失败: {e}")
        return advice
    else:
        logger.info("CPU 正常，无需建议")
        return None
