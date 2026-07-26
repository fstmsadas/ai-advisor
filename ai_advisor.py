import time
from ai import generate_response
from system_metrics import get_system_metrics, get_top_processes, is_cpu_high
from utils import setup_logger

logger = setup_logger('ai_advisor')

def get_optimization_advice(metrics, top_procs, retries=3):
    """
    根据系统指标和进程信息，调用 AI 生成优化建议
    :param metrics: 系统指标字典
    :param top_procs: top 进程列表
    :param retries: 重试次数
    :return: AI 建议字符串
    """
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
            return advice
        except Exception as e:
            logger.error(f"AI 调用失败 (尝试 {attempt+1}/{retries}): {e}")
            time.sleep(2 ** attempt)  # 指数退避
    return "AI 服务暂时不可用，请稍后重试。"

def check_and_advise(threshold=80):
    """检查 CPU 是否超阈值，若超出则生成建议并返回，否则返回 None"""
    metrics = get_system_metrics()
    if metrics['cpu_percent'] > threshold:
        top_procs = get_top_processes(5)
        advice = get_optimization_advice(metrics, top_procs)
        logger.info(f"CPU 超阈值建议: {advice}")
        return advice
    else:
        logger.info("CPU 正常，无需建议")
        return None
