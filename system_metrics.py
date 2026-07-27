import psutil
import logging

logger = logging.getLogger(__name__)

def get_system_metrics():
    """获取系统指标（使用 interval=0 避免阻塞）"""
    logger.info("开始采集系统指标...")
    cpu = psutil.cpu_percent(interval=0)          # 立即返回上次采样值
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load = psutil.getloadavg()
    logger.info("采集完成")
    return {
        'cpu_percent': cpu,
        'memory_percent': mem.percent,
        'disk_usage': disk.percent,
        'load_avg': load[0]
    }

def get_top_processes(n=5):
    """使用 psutil 获取 CPU 最高的 n 个进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            cpu = proc.cpu_percent(interval=0)
            mem = proc.memory_percent()
            processes.append({
                'pid': proc.pid,
                'user': proc.username(),
                'cpu': round(cpu, 1),
                'mem': round(mem, 1),
                'command': proc.name()
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    processes.sort(key=lambda x: x['cpu'], reverse=True)
    return processes[:n]

def is_cpu_high(threshold=80):
    return psutil.cpu_percent(interval=0) > threshold
